from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone

from apps.ans_reference.services.lookup_service import find_plan_references
from apps.audit.models import AuditAction
from apps.audit.services import record_event
from apps.catalog.models import Operator, Plan
from apps.core.domain.severity import Severity
from apps.monitoring.models import AlertKind, AlertStatus, MonitoringAlert
from apps.pricing.models import PriceTable
from apps.sources.models import CheckOutcome, Source, SourceCheck
from apps.sources.services import FreshnessStatus, SourceFreshness, find_sources_with_freshness

# Kinds owned by the periodic checks: they open and resolve automatically.
MANAGED_KINDS = (
    AlertKind.SOURCE_OVERDUE,
    AlertKind.SOURCE_NEVER_CHECKED,
    AlertKind.SOURCE_CHECK_FAILED,
    AlertKind.STALE_PRICE_TABLE,
    AlertKind.PLAN_NOT_ACTIVE_AT_ANS,
)
_DAYS_PER_MONTH = 30


@dataclass(frozen=True)
class AlertObservation:
    kind: AlertKind
    severity: Severity
    fingerprint: str
    params: dict
    operator: Operator | None = None
    source: Source | None = None
    plan: Plan | None = None


@dataclass
class MonitoringSummary:
    opened: int = 0
    refreshed: int = 0
    resolved: int = 0
    by_kind: dict[str, int] = field(default_factory=dict)


def run_monitoring_checks(now: datetime | None = None) -> MonitoringSummary:
    now = now or timezone.now()
    source_freshness = find_sources_with_freshness(now)
    observations = [
        *observe_source_freshness(source_freshness),
        *observe_failed_checks(source_freshness),
        *observe_stale_price_tables(now),
        *observe_ans_plan_status(),
    ]
    summary = sync_alerts(observations, now)
    record_event(
        AuditAction.MONITORING_RAN,
        payload={"opened": summary.opened, "resolved": summary.resolved, "open": len(observations)},
        occurred_at=now,
    )
    return summary


def observe_source_freshness(source_freshness: list[SourceFreshness]) -> list[AlertObservation]:
    observations = []
    for freshness in source_freshness:
        source = freshness.source
        if freshness.status == FreshnessStatus.OVERDUE:
            observations.append(
                AlertObservation(
                    kind=AlertKind.SOURCE_OVERDUE,
                    severity=Severity.WARNING,
                    fingerprint=f"source_overdue:{source.public_id}",
                    params={
                        "source": source.name,
                        "days": freshness.days_since_success,
                        "expected_days": source.expected_update_days,
                    },
                    operator=source.operator,
                    source=source,
                )
            )
        elif freshness.status == FreshnessStatus.NEVER_CHECKED:
            observations.append(
                AlertObservation(
                    kind=AlertKind.SOURCE_NEVER_CHECKED,
                    severity=Severity.INFO,
                    fingerprint=f"source_never_checked:{source.public_id}",
                    params={"source": source.name},
                    operator=source.operator,
                    source=source,
                )
            )
    return observations


def observe_failed_checks(source_freshness: list[SourceFreshness]) -> list[AlertObservation]:
    failing = [
        freshness
        for freshness in source_freshness
        if freshness.last_failure_at is not None
        and (
            freshness.last_success_at is None
            or freshness.last_failure_at > freshness.last_success_at
        )
    ]
    notes = find_latest_failure_notes([freshness.source for freshness in failing])
    return [
        AlertObservation(
            kind=AlertKind.SOURCE_CHECK_FAILED,
            severity=Severity.WARNING,
            fingerprint=f"source_check_failed:{freshness.source.public_id}",
            params={
                "source": freshness.source.name,
                "checked_at_date": timezone.localtime(freshness.last_failure_at).date().isoformat(),
                "note": notes.get(freshness.source.id, ""),
            },
            operator=freshness.source.operator,
            source=freshness.source,
        )
        for freshness in failing
    ]


def find_latest_failure_notes(sources: list[Source]) -> dict[int, str]:
    notes: dict[int, str] = {}
    failed_checks = SourceCheck.objects.filter(
        source__in=sources, outcome=CheckOutcome.FAILED
    ).order_by("source_id", "-checked_at")
    for check in failed_checks:
        notes.setdefault(check.source_id, check.note)
    return notes


def observe_stale_price_tables(now: datetime) -> list[AlertObservation]:
    today = timezone.localdate(now)
    stale_before = today - timedelta(days=settings.MONITORING_STALE_TABLE_DAYS)
    tables = (
        PriceTable.objects.current()
        .filter(
            validity__contains=today, plan__is_active=True, validity__startswith__lt=stale_before
        )
        .select_related("plan__operator")
    )
    grouped: dict[tuple[int, str], list[PriceTable]] = defaultdict(list)
    for table in tables:
        grouped[(table.plan.operator_id, table.region)].append(table)
    observations = []
    for (_, region), group in grouped.items():
        operator = group[0].plan.operator
        oldest = min(table.validity.lower for table in group)
        observations.append(
            AlertObservation(
                kind=AlertKind.STALE_PRICE_TABLE,
                severity=Severity.WARNING,
                fingerprint=f"stale_price_table:{operator.public_id}:{region}"[:255],
                params={
                    "operator": operator.name,
                    "region": region,
                    "effective_from_date": oldest.isoformat(),
                    "months": (today - oldest).days // _DAYS_PER_MONTH,
                    "plans": len(group),
                },
                operator=operator,
            )
        )
    return observations


def observe_ans_plan_status() -> list[AlertObservation]:
    plans = list(Plan.objects.filter(is_active=True).select_related("operator"))
    references = find_plan_references(plans)
    observations = []
    for plan in plans:
        reference = references.get(plan.id)
        if reference is None or reference.is_sellable:
            continue
        observations.append(
            AlertObservation(
                kind=AlertKind.PLAN_NOT_ACTIVE_AT_ANS,
                severity=Severity.ERROR,
                fingerprint=f"plan_not_active_at_ans:{plan.public_id}",
                params={
                    "plan": plan.name,
                    "operator": plan.operator.name,
                    "status": reference.status_label,
                    "status_date": reference.status_date.isoformat()
                    if reference.status_date
                    else None,
                },
                operator=plan.operator,
                plan=plan,
            )
        )
    return observations


def sync_alerts(observations: list[AlertObservation], now: datetime) -> MonitoringSummary:
    summary = MonitoringSummary()
    open_alerts = {
        alert.fingerprint: alert
        for alert in MonitoringAlert.objects.filter(status=AlertStatus.OPEN, kind__in=MANAGED_KINDS)
    }
    for observation in observations:
        summary.by_kind[observation.kind] = summary.by_kind.get(observation.kind, 0) + 1
        alert = open_alerts.pop(observation.fingerprint, None)
        if alert is None:
            create_alert(observation, now)
            summary.opened += 1
            continue
        alert.params = observation.params
        alert.severity = observation.severity
        alert.last_seen_at = now
        alert.save(update_fields=["params", "severity", "last_seen_at"])
        summary.refreshed += 1
    for alert in open_alerts.values():
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = now
        alert.save(update_fields=["status", "resolved_at"])
        summary.resolved += 1
    return summary


def create_alert(observation: AlertObservation, now: datetime) -> MonitoringAlert:
    return MonitoringAlert.objects.create(
        kind=observation.kind,
        severity=observation.severity,
        operator=observation.operator,
        source=observation.source,
        plan=observation.plan,
        params=observation.params,
        fingerprint=observation.fingerprint,
        opened_at=now,
        last_seen_at=now,
    )
