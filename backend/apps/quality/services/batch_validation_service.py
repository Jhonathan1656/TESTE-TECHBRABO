from collections import Counter
from datetime import date, datetime

from django.conf import settings
from django.db.models import Count, Q
from django.utils import timezone

from apps.ans_reference.services.lookup_service import AnsPlanReference, find_plan_references
from apps.core.domain.age_bands import AgeBand
from apps.core.domain.severity import Severity
from apps.ingestion.models import ExtractedPlan, ExtractedPrice, ExtractionMethod, ImportBatch
from apps.pricing.models import PriceTable
from apps.pricing.services.price_lookup_service import (
    find_latest_effective_starts,
    find_operator_tables_valid_on,
    find_tables_valid_on,
)
from apps.quality.models import IssueStatus, ValidationIssue
from apps.quality.rules.registry import run_rules
from apps.quality.rules.snapshot import (
    BatchSnapshot,
    Finding,
    MissingPlan,
    PlanSnapshot,
    QualityThresholds,
    RegisteredBand,
)

BLOCKING_SEVERITIES = (Severity.ERROR, Severity.WARNING)


def validate_batch(batch: ImportBatch, now: datetime | None = None) -> list[Finding]:
    now = now or timezone.now()
    extracted_plans = list(
        batch.extracted_plans.select_related("plan__operator").prefetch_related("prices")
    )
    previous_tables = find_previous_tables(batch, find_matched_plans(extracted_plans))
    store_previous_values(extracted_plans, previous_tables)
    snapshot = build_batch_snapshot(batch, extracted_plans, previous_tables, now)
    findings = run_rules(snapshot)
    reconcile_issues(batch, findings, extracted_plans, now)
    return findings


def find_matched_plans(extracted_plans: list[ExtractedPlan]) -> list:
    return [
        extracted.plan
        for extracted in extracted_plans
        if not extracted.is_excluded and extracted.plan is not None
    ]


def find_previous_tables(batch: ImportBatch, matched_plans: list) -> dict[int, PriceTable]:
    """The tables a new version is compared against: those valid when it would start."""
    if batch.effective_from is None:
        return {}
    return find_tables_valid_on(matched_plans, batch.region, batch.effective_from)


def build_batch_snapshot(
    batch: ImportBatch,
    extracted_plans: list[ExtractedPlan],
    previous_tables: dict[int, PriceTable],
    now: datetime,
) -> BatchSnapshot:
    included = [extracted for extracted in extracted_plans if not extracted.is_excluded]
    matched_plans = find_matched_plans(extracted_plans)
    latest_starts = find_latest_effective_starts(matched_plans, batch.region)
    references = find_plan_references(matched_plans)
    return BatchSnapshot(
        today=timezone.localdate(now),
        effective_from=batch.effective_from,
        extraction_method=batch.extraction_method,
        extraction_model=batch.extraction_details.get("model", ""),
        document_text=_read_anchoring_text(batch),
        plans=tuple(
            build_plan_snapshot(extracted, previous_tables, latest_starts, references)
            for extracted in included
        ),
        missing_plans=find_missing_plans(batch, extracted_plans),
        conflicting_duplicates=batch.extraction_details.get("conflicting_duplicates", 0),
        thresholds=load_quality_thresholds(),
    )


def build_plan_snapshot(
    extracted: ExtractedPlan,
    previous_tables: dict[int, PriceTable],
    latest_starts: dict[int, date],
    references: dict[int, AnsPlanReference],
) -> PlanSnapshot:
    plan = extracted.plan
    prices = list(extracted.prices.all())
    previous_table = previous_tables.get(plan.id) if plan else None
    reference = references.get(plan.id) if plan else None
    return PlanSnapshot(
        label=extracted.label,
        plan_id=plan.id if plan else None,
        plan_name=plan.name if plan else None,
        product_line=plan.product_line if plan else None,
        contract_type=plan.contract_type if plan else None,
        accommodation=plan.accommodation if plan else None,
        has_coparticipation=plan.has_coparticipation if plan else None,
        match_method=extracted.match_method,
        match_score=extracted.match_score,
        suggestions=tuple(extracted.suggestions),
        values={AgeBand(price.age_band): price.final_value for price in prices},
        raw_texts={AgeBand(price.age_band): price.raw_text for price in prices},
        previous_values=(
            {AgeBand(entry.age_band): entry.value for entry in previous_table.entries.all()}
            if previous_table
            else {}
        ),
        current_effective_from=latest_starts.get(plan.id) if plan else None,
        ans_status=reference.status.value if reference else None,
        ans_status_label=reference.status_label if reference else None,
        ans_status_date=reference.status_date if reference else None,
        registered_bands=(
            {
                band: RegisteredBand(registered.min_value, registered.max_value)
                for band, registered in reference.price_bands.items()
            }
            if reference
            else {}
        ),
    )


def find_missing_plans(
    batch: ImportBatch, extracted_plans: list[ExtractedPlan]
) -> tuple[MissingPlan, ...]:
    if batch.effective_from is None:
        return ()
    present = {extracted.plan_id for extracted in extracted_plans if extracted.plan_id}
    tables = find_operator_tables_valid_on(batch.operator, batch.region, batch.effective_from)
    return tuple(
        MissingPlan(
            plan_id=table.plan_id, plan_name=table.plan.name, effective_from=table.validity.lower
        )
        for table in sorted(tables, key=lambda table: table.plan.name)
        if table.plan_id not in present
    )


def store_previous_values(
    extracted_plans: list[ExtractedPlan], previous_tables: dict[int, PriceTable]
) -> None:
    changed: list[ExtractedPrice] = []
    for extracted in extracted_plans:
        table = previous_tables.get(extracted.plan_id) if extracted.plan_id else None
        previous_by_band = (
            {entry.age_band: entry.value for entry in table.entries.all()} if table else {}
        )
        for price in extracted.prices.all():
            previous = previous_by_band.get(price.age_band)
            if price.previous_value != previous:
                price.previous_value = previous
                changed.append(price)
    ExtractedPrice.objects.bulk_update(changed, ["previous_value"])


def reconcile_issues(
    batch: ImportBatch,
    findings: list[Finding],
    extracted_plans: list[ExtractedPlan],
    now: datetime,
) -> None:
    existing = {issue.fingerprint: issue for issue in batch.issues.all()}
    plans_by_label = {extracted.label: extracted for extracted in extracted_plans}
    seen: set[str] = set()
    to_create: list[ValidationIssue] = []
    to_update: list[ValidationIssue] = []
    for finding in findings:
        if finding.fingerprint in seen:
            continue
        seen.add(finding.fingerprint)
        issue = existing.get(finding.fingerprint)
        if issue is None:
            to_create.append(build_issue(batch, finding, plans_by_label))
        else:
            refresh_issue(issue, finding)
            to_update.append(issue)
    for fingerprint, issue in existing.items():
        if fingerprint not in seen and issue.status != IssueStatus.RESOLVED:
            issue.status = IssueStatus.RESOLVED
            issue.resolved_at = now
            to_update.append(issue)
    ValidationIssue.objects.bulk_create(to_create)
    ValidationIssue.objects.bulk_update(
        to_update,
        [
            "severity",
            "params",
            "status",
            "resolved_at",
            "acknowledged_by",
            "acknowledged_at",
            "acknowledgement_note",
        ],
    )


def build_issue(
    batch: ImportBatch, finding: Finding, plans_by_label: dict[str, ExtractedPlan]
) -> ValidationIssue:
    return ValidationIssue(
        batch=batch,
        rule_code=finding.rule_code,
        severity=finding.severity,
        extracted_plan=plans_by_label.get(finding.plan_label),
        age_band=int(finding.age_band) if finding.age_band is not None else None,
        params=finding.params,
        fingerprint=finding.fingerprint,
    )


def refresh_issue(issue: ValidationIssue, finding: Finding) -> None:
    # An acknowledgement only covers the exact situation the reviewer saw.
    reopen = issue.status == IssueStatus.RESOLVED or (
        issue.status == IssueStatus.ACKNOWLEDGED and issue.params != finding.params
    )
    issue.severity = finding.severity
    issue.params = finding.params
    if reopen:
        issue.status = IssueStatus.OPEN
        issue.resolved_at = None
        issue.acknowledged_by = None
        issue.acknowledged_at = None
        issue.acknowledgement_note = ""


def count_blocking_issues(batch: ImportBatch) -> Counter:
    counts = batch.issues.filter(status=IssueStatus.OPEN).aggregate(
        errors=Count("id", filter=Q(severity=Severity.ERROR)),
        warnings=Count("id", filter=Q(severity=Severity.WARNING)),
    )
    return Counter({Severity.ERROR: counts["errors"], Severity.WARNING: counts["warnings"]})


def load_quality_thresholds() -> QualityThresholds:
    configured = settings.QUALITY_THRESHOLDS
    return QualityThresholds(
        large_variation_pct=configured["large_variation_pct"],
        non_uniform_tolerance_pp=configured["non_uniform_tolerance_pp"],
        decimal_shift_tolerance=configured["decimal_shift_tolerance"],
        late_capture_days=configured["late_capture_days"],
    )


def _read_anchoring_text(batch: ImportBatch) -> str:
    if batch.extraction_method != ExtractionMethod.LLM:
        return ""
    return batch.document.text_content
