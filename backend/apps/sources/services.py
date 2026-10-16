from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from django.db.models import Max, Q
from django.utils import timezone

from apps.audit.models import AuditAction
from apps.audit.services import record_event
from apps.core.exceptions import NotFoundError
from apps.sources.models import CheckOutcome, Source, SourceCheck

_SUCCESSFUL_OUTCOMES = (CheckOutcome.NEW_MATERIAL, CheckOutcome.UNCHANGED)


class FreshnessStatus(StrEnum):
    FRESH = "fresh"
    DUE = "due"
    OVERDUE = "overdue"
    NEVER_CHECKED = "never_checked"


@dataclass(frozen=True)
class SourceFreshness:
    source: Source
    status: FreshnessStatus
    last_success_at: datetime | None
    last_new_material_at: datetime | None
    last_failure_at: datetime | None
    days_since_success: int | None


def evaluate_freshness(
    last_success_at: datetime | None,
    expected_update_days: int,
    tolerance_days: int,
    now: datetime,
) -> FreshnessStatus:
    if last_success_at is None:
        return FreshnessStatus.NEVER_CHECKED
    age = now - last_success_at
    if age <= timedelta(days=expected_update_days):
        return FreshnessStatus.FRESH
    if age <= timedelta(days=expected_update_days + tolerance_days):
        return FreshnessStatus.DUE
    return FreshnessStatus.OVERDUE


def find_sources_with_freshness(
    now: datetime | None = None, operator=None
) -> list[SourceFreshness]:
    now = now or timezone.now()
    sources = (
        Source.objects.filter(is_active=True)
        .select_related("operator")
        .annotate(
            last_success_at=Max(
                "checks__checked_at", filter=Q(checks__outcome__in=_SUCCESSFUL_OUTCOMES)
            ),
            last_new_material_at=Max(
                "checks__checked_at", filter=Q(checks__outcome=CheckOutcome.NEW_MATERIAL)
            ),
            last_failure_at=Max(
                "checks__checked_at", filter=Q(checks__outcome=CheckOutcome.FAILED)
            ),
        )
    )
    if operator is not None:
        sources = sources.filter(operator=operator)
    return [build_source_freshness(source, now) for source in sources]


def build_source_freshness(source: Source, now: datetime) -> SourceFreshness:
    last_success_at = source.last_success_at
    return SourceFreshness(
        source=source,
        status=evaluate_freshness(
            last_success_at, source.expected_update_days, source.tolerance_days, now
        ),
        last_success_at=last_success_at,
        last_new_material_at=source.last_new_material_at,
        last_failure_at=source.last_failure_at,
        days_since_success=(now - last_success_at).days if last_success_at else None,
    )


def find_source(source_id) -> Source:
    source = Source.objects.select_related("operator").filter(public_id=source_id).first()
    if source is None:
        raise NotFoundError("resource.not_found")
    return source


def find_source_freshness(source: Source, now: datetime | None = None) -> SourceFreshness:
    return next(
        freshness
        for freshness in find_sources_with_freshness(now, operator=source.operator)
        if freshness.source.id == source.id
    )


def list_recent_checks(source: Source, limit: int = 20) -> list[SourceCheck]:
    return list(
        source.checks.select_related("checked_by", "document").order_by("-checked_at")[:limit]
    )


def record_source_check(
    source: Source,
    outcome: CheckOutcome,
    *,
    document=None,
    note: str = "",
    actor=None,
    checked_at: datetime | None = None,
) -> SourceCheck:
    checked_at = checked_at or timezone.now()
    check = SourceCheck.objects.create(
        source=source,
        outcome=outcome,
        document=document,
        note=note,
        checked_by=actor if actor is not None and actor.is_authenticated else None,
        checked_at=checked_at,
    )
    record_event(
        AuditAction.SOURCE_CHECKED,
        actor=actor,
        operator=source.operator,
        target=source,
        payload={"outcome": outcome, "note": note},
        occurred_at=checked_at,
    )
    return check
