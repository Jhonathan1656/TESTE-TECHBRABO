from datetime import date, datetime, timedelta

from django.db import transaction
from django.db.backends.postgresql.psycopg_any import DateRange
from django.utils import timezone

from apps.audit.models import AuditAction
from apps.audit.services import record_event
from apps.core.domain.severity import Severity
from apps.core.exceptions import DomainError
from apps.ingestion.models import BatchStatus, ExtractedPlan, ImportBatch
from apps.pricing.models import PriceEntry, PriceTable
from apps.quality.services.batch_validation_service import count_blocking_issues


@transaction.atomic
def publish_batch(
    batch: ImportBatch,
    actor=None,
    now: datetime | None = None,
    note: str = "",
    automatic: bool = False,
) -> list[PriceTable]:
    now = now or timezone.now()
    batch = ImportBatch.objects.select_for_update().select_related("operator").get(pk=batch.pk)
    ensure_batch_publishable(batch)
    validity = build_validity_range(batch.effective_from, batch.effective_until)
    extracted_plans = (
        batch.extracted_plans.filter(is_excluded=False, plan__isnull=False)
        .select_related("plan")
        .prefetch_related("prices")
    )
    tables = [publish_plan_prices(batch, extracted, validity, now) for extracted in extracted_plans]
    if not tables:
        raise DomainError("batch.nothing_to_publish")
    batch.status = BatchStatus.PUBLISHED
    batch.reviewed_by = actor
    batch.reviewed_at = now
    batch.review_note = note
    batch.auto_published = automatic
    batch.save(
        update_fields=["status", "reviewed_by", "reviewed_at", "review_note", "auto_published"]
    )
    record_event(
        AuditAction.BATCH_AUTO_PUBLISHED if automatic else AuditAction.BATCH_PUBLISHED,
        actor=actor,
        operator=batch.operator,
        target=batch,
        payload={"plans": len(tables), "effective_from": batch.effective_from.isoformat()},
        occurred_at=now,
    )
    return tables


def ensure_batch_publishable(batch: ImportBatch) -> None:
    if batch.status != BatchStatus.PENDING_REVIEW:
        raise DomainError("batch.not_pending_review")
    blocking = count_blocking_issues(batch)
    if blocking[Severity.ERROR] or blocking[Severity.WARNING]:
        raise DomainError(
            "batch.has_blocking_issues",
            {"errors": blocking[Severity.ERROR], "warnings": blocking[Severity.WARNING]},
        )


def publish_plan_prices(
    batch: ImportBatch, extracted: ExtractedPlan, validity: DateRange, now: datetime
) -> PriceTable:
    supersede_overlapping_tables(extracted.plan, batch.region, validity, batch, now)
    table = PriceTable.objects.create(
        plan=extracted.plan, region=batch.region, validity=validity, batch=batch, recorded_at=now
    )
    PriceEntry.objects.bulk_create(
        PriceEntry(
            table=table,
            age_band=price.age_band,
            value=price.final_value,
            location=price.location,
            was_corrected=price.corrected_value is not None,
        )
        for price in extracted.prices.all()
    )
    return table


def supersede_overlapping_tables(
    plan, region: str, validity: DateRange, batch: ImportBatch, now: datetime
) -> None:
    """Retires overlapping current versions and re-records the parts that still hold."""
    overlapping = list(
        PriceTable.objects.current()
        .select_for_update()
        .filter(plan=plan, region=region, validity__overlap=validity)
        .prefetch_related("entries")
    )
    for table in overlapping:
        table.superseded_at = now
        table.superseded_by = batch
        table.save(update_fields=["superseded_at", "superseded_by"])
    for table in overlapping:
        for remaining in subtract_range(table.validity, validity):
            copy_table(table, remaining, now)


def subtract_range(original: DateRange, removed: DateRange) -> list[DateRange]:
    remaining = []
    if original.lower < removed.lower:
        remaining.append(DateRange(original.lower, removed.lower, "[)"))
    if removed.upper is not None and (original.upper is None or original.upper > removed.upper):
        remaining.append(DateRange(removed.upper, original.upper, "[)"))
    return remaining


def copy_table(table: PriceTable, validity: DateRange, now: datetime) -> PriceTable:
    copy = PriceTable.objects.create(
        plan_id=table.plan_id,
        region=table.region,
        validity=validity,
        batch_id=table.batch_id,
        recorded_at=now,
        derived_from=table,
    )
    PriceEntry.objects.bulk_create(
        PriceEntry(
            table=copy,
            age_band=entry.age_band,
            value=entry.value,
            location=entry.location,
            was_corrected=entry.was_corrected,
        )
        for entry in table.entries.all()
    )
    return copy


def build_validity_range(effective_from: date, effective_until: date | None) -> DateRange:
    upper = effective_until + timedelta(days=1) if effective_until else None
    return DateRange(effective_from, upper, "[)")
