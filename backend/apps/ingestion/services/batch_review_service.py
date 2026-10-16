from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditAction
from apps.audit.services import record_event
from apps.catalog.models import Plan
from apps.catalog.services.plan_matching_service import learn_plan_alias
from apps.core.domain.severity import Severity
from apps.core.exceptions import DomainError
from apps.ingestion.models import (
    BatchStatus,
    ExtractedPlan,
    ExtractedPrice,
    ImportBatch,
    PlanMatchMethod,
)
from apps.ingestion.services.batch_processing_service import BatchOverrides, process_document
from apps.pricing.models import PriceTable
from apps.pricing.services.publication_service import publish_batch
from apps.quality.models import IssueStatus, ValidationIssue
from apps.quality.services.batch_validation_service import validate_batch


@dataclass(frozen=True)
class EffectiveDates:
    effective_from: date | None
    effective_until: date | None
    region: str


def lock_pending_batch(batch_id: int) -> ImportBatch:
    batch = ImportBatch.objects.select_for_update().select_related("operator").get(pk=batch_id)
    if batch.status != BatchStatus.PENDING_REVIEW:
        raise DomainError("batch.not_pending_review")
    return batch


@transaction.atomic
def correct_price(
    price: ExtractedPrice, corrected_value: Decimal | None, actor, now: datetime | None = None
) -> ImportBatch:
    now = now or timezone.now()
    batch = lock_pending_batch(price.extracted_plan.batch_id)
    previous_value = price.final_value
    price.corrected_value = corrected_value
    price.corrected_by = actor if corrected_value is not None else None
    price.corrected_at = now if corrected_value is not None else None
    price.save(update_fields=["corrected_value", "corrected_by", "corrected_at"])
    record_event(
        AuditAction.PRICE_CORRECTED,
        actor=actor,
        operator=batch.operator,
        target=batch,
        payload={
            "plan": price.extracted_plan.label,
            "age_band": price.age_band,
            "from": str(previous_value) if previous_value is not None else None,
            "to": str(price.final_value) if price.final_value is not None else None,
        },
        occurred_at=now,
    )
    validate_batch(batch, now=now)
    return batch


@transaction.atomic
def map_extracted_plan(
    extracted: ExtractedPlan, plan: Plan, actor, now: datetime | None = None
) -> ImportBatch:
    now = now or timezone.now()
    batch = lock_pending_batch(extracted.batch_id)
    if plan.operator_id != batch.operator_id:
        raise DomainError("batch.plan_from_other_operator")
    extracted.plan = plan
    extracted.match_method = PlanMatchMethod.MANUAL
    extracted.match_score = None
    extracted.save(update_fields=["plan", "match_method", "match_score"])
    learn_plan_alias(batch.operator, plan, extracted.label, actor)
    record_event(
        AuditAction.PLAN_MAPPED,
        actor=actor,
        operator=batch.operator,
        target=batch,
        payload={"label": extracted.label, "plan": plan.name},
        occurred_at=now,
    )
    validate_batch(batch, now=now)
    return batch


@transaction.atomic
def set_plan_exclusion(
    extracted: ExtractedPlan, excluded: bool, actor, now: datetime | None = None
) -> ImportBatch:
    now = now or timezone.now()
    batch = lock_pending_batch(extracted.batch_id)
    extracted.is_excluded = excluded
    extracted.save(update_fields=["is_excluded"])
    record_event(
        AuditAction.PLAN_EXCLUDED if excluded else AuditAction.PLAN_INCLUDED,
        actor=actor,
        operator=batch.operator,
        target=batch,
        payload={"label": extracted.label},
        occurred_at=now,
    )
    validate_batch(batch, now=now)
    return batch


@transaction.atomic
def acknowledge_issue(
    issue: ValidationIssue, note: str, actor, now: datetime | None = None
) -> ImportBatch:
    now = now or timezone.now()
    batch = lock_pending_batch(issue.batch_id)
    if issue.severity != Severity.WARNING:
        raise DomainError("issue.only_warnings_can_be_acknowledged")
    if issue.status != IssueStatus.OPEN:
        raise DomainError("issue.not_open")
    issue.status = IssueStatus.ACKNOWLEDGED
    issue.acknowledged_by = actor
    issue.acknowledged_at = now
    issue.acknowledgement_note = note
    issue.save(
        update_fields=["status", "acknowledged_by", "acknowledged_at", "acknowledgement_note"]
    )
    record_event(
        AuditAction.ISSUE_ACKNOWLEDGED,
        actor=actor,
        operator=batch.operator,
        target=batch,
        payload={"rule": issue.rule_code, "note": note},
        occurred_at=now,
    )
    return batch


@transaction.atomic
def update_effective_dates(
    batch: ImportBatch, dates: EffectiveDates, actor, now: datetime | None = None
) -> ImportBatch:
    now = now or timezone.now()
    batch = lock_pending_batch(batch.pk)
    if (
        dates.effective_from
        and dates.effective_until
        and dates.effective_until < dates.effective_from
    ):
        raise DomainError("batch.effective_date_invalid")
    batch.effective_from = dates.effective_from
    batch.effective_until = dates.effective_until
    batch.region = dates.region
    batch.save(update_fields=["effective_from", "effective_until", "region", "updated_at"])
    record_event(
        AuditAction.BATCH_DATES_CHANGED,
        actor=actor,
        operator=batch.operator,
        target=batch,
        payload={
            "effective_from": dates.effective_from.isoformat() if dates.effective_from else None,
            "effective_until": dates.effective_until.isoformat() if dates.effective_until else None,
            "region": dates.region,
        },
        occurred_at=now,
    )
    validate_batch(batch, now=now)
    return batch


def approve_batch(
    batch: ImportBatch, actor, note: str = "", now: datetime | None = None
) -> list[PriceTable]:
    return publish_batch(batch, actor=actor, now=now, note=note)


@transaction.atomic
def reject_batch(
    batch: ImportBatch, reason: str, actor, now: datetime | None = None
) -> ImportBatch:
    now = now or timezone.now()
    batch = lock_pending_batch(batch.pk)
    batch.status = BatchStatus.REJECTED
    batch.reviewed_by = actor
    batch.reviewed_at = now
    batch.review_note = reason
    batch.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_note", "updated_at"])
    record_event(
        AuditAction.BATCH_REJECTED,
        actor=actor,
        operator=batch.operator,
        target=batch,
        payload={"reason": reason},
        occurred_at=now,
    )
    return batch


def reprocess_failed_batch(batch: ImportBatch, now: datetime | None = None) -> ImportBatch:
    """Runs the stored original again, e.g. after AI extraction was enabled."""
    if batch.status != BatchStatus.FAILED:
        raise DomainError("batch.cannot_retry")
    overrides = BatchOverrides(
        effective_from=batch.effective_from,
        effective_until=batch.effective_until,
        region=batch.region or None,
    )
    return process_document(batch.document, overrides, now=now)
