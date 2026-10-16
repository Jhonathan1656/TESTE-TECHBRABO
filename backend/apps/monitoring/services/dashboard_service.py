from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime

from django.db.models import Count, Q
from django.utils import timezone

from apps.audit.services import list_recent_events
from apps.catalog.models import Operator
from apps.core.domain.severity import Severity
from apps.ingestion.models import BatchStatus
from apps.monitoring.services.alert_service import list_open_alerts
from apps.pricing.models import PriceTable
from apps.quality.models import IssueStatus, ValidationIssue
from apps.sources.services import FreshnessStatus, SourceFreshness, find_sources_with_freshness

# Ordered from best to worst; an operator is as fresh as its stalest active source.
_FRESHNESS_RANK = {
    FreshnessStatus.FRESH: 0,
    FreshnessStatus.DUE: 1,
    FreshnessStatus.NEVER_CHECKED: 2,
    FreshnessStatus.OVERDUE: 3,
}
_CONFIRMED_STATUSES = {FreshnessStatus.FRESH, FreshnessStatus.DUE}
_RECENT_EVENTS = 12


@dataclass(frozen=True)
class OperatorHealth:
    operator: Operator
    status: FreshnessStatus
    sources: tuple[SourceFreshness, ...]
    active_plans: int
    priced_plans: int
    oldest_effective_from: date | None
    next_change_on: date | None
    open_alerts: int
    pending_batches: int


@dataclass(frozen=True)
class Dashboard:
    generated_at: datetime
    pending_batches: int
    open_errors: int
    open_warnings: int
    active_plans: int
    priced_plans: int
    confirmed_plans: int
    operators: tuple[OperatorHealth, ...]
    alerts: list = field(default_factory=list)
    recent_events: list = field(default_factory=list)


@dataclass
class _PricingFootprint:
    priced_plans: set = field(default_factory=set)
    confirmed_plans: set = field(default_factory=set)
    oldest_effective_from: date | None = None
    next_change_on: date | None = None


def build_dashboard(now: datetime | None = None) -> Dashboard:
    now = now or timezone.now()
    today = timezone.localdate(now)
    freshness = find_sources_with_freshness(now)
    footprints = measure_pricing_footprints(today, {item.source.id: item for item in freshness})
    operators = list(
        Operator.objects.annotate(
            active_plans=Count("plans", filter=Q(plans__is_active=True), distinct=True),
            pending_batches=Count(
                "batches", filter=Q(batches__status=BatchStatus.PENDING_REVIEW), distinct=True
            ),
            open_alerts=Count("alerts", filter=Q(alerts__status="open"), distinct=True),
        ).order_by("name")
    )
    health = tuple(
        build_operator_health(operator, freshness, footprints.get(operator.id, _PricingFootprint()))
        for operator in operators
    )
    open_issues = ValidationIssue.objects.filter(
        batch__status=BatchStatus.PENDING_REVIEW, status=IssueStatus.OPEN
    ).aggregate(
        errors=Count("id", filter=Q(severity=Severity.ERROR)),
        warnings=Count("id", filter=Q(severity=Severity.WARNING)),
    )
    return Dashboard(
        generated_at=now,
        pending_batches=sum(item.pending_batches for item in health),
        open_errors=open_issues["errors"],
        open_warnings=open_issues["warnings"],
        active_plans=sum(item.active_plans for item in health),
        priced_plans=sum(item.priced_plans for item in health),
        confirmed_plans=sum(len(footprint.confirmed_plans) for footprint in footprints.values()),
        operators=health,
        alerts=list(list_open_alerts()),
        recent_events=list(list_recent_events(limit=_RECENT_EVENTS)),
    )


def measure_pricing_footprints(
    today: date, freshness_by_source: dict[int, SourceFreshness]
) -> dict[int, _PricingFootprint]:
    footprints: dict[int, _PricingFootprint] = defaultdict(_PricingFootprint)
    valid_today = PriceTable.objects.current().filter(
        validity__contains=today, plan__is_active=True
    )
    for operator_id, plan_id, validity, source_id in valid_today.values_list(
        "plan__operator_id", "plan_id", "validity", "batch__document__source_id"
    ):
        footprint = footprints[operator_id]
        footprint.priced_plans.add(plan_id)
        source_freshness = freshness_by_source.get(source_id)
        if source_freshness and source_freshness.status in _CONFIRMED_STATUSES:
            footprint.confirmed_plans.add(plan_id)
        footprint.oldest_effective_from = min(
            filter(None, (footprint.oldest_effective_from, validity.lower))
        )
    upcoming = PriceTable.objects.current().filter(
        validity__startswith__gt=today, plan__is_active=True
    )
    for operator_id, validity in upcoming.values_list("plan__operator_id", "validity"):
        footprint = footprints[operator_id]
        footprint.next_change_on = min(filter(None, (footprint.next_change_on, validity.lower)))
    return footprints


def build_operator_health(
    operator: Operator, freshness: list[SourceFreshness], footprint: _PricingFootprint
) -> OperatorHealth:
    sources = tuple(item for item in freshness if item.source.operator_id == operator.id)
    status = max(
        (item.status for item in sources),
        key=_FRESHNESS_RANK.__getitem__,
        default=FreshnessStatus.NEVER_CHECKED,
    )
    return OperatorHealth(
        operator=operator,
        status=status,
        sources=sources,
        active_plans=operator.active_plans,
        priced_plans=len(footprint.priced_plans),
        oldest_effective_from=footprint.oldest_effective_from,
        next_change_on=footprint.next_change_on,
        open_alerts=operator.open_alerts,
        pending_batches=operator.pending_batches,
    )
