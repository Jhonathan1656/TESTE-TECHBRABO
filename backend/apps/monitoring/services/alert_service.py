from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from django.db.models import Case, IntegerField, QuerySet, Value, When
from django.utils import timezone

from apps.audit.models import AuditAction
from apps.audit.services import record_event
from apps.catalog.models import Plan
from apps.core.domain.severity import Severity
from apps.core.exceptions import DomainError, NotFoundError
from apps.monitoring.models import AlertKind, AlertStatus, BrokerReport, MonitoringAlert

_MESSAGE_PREVIEW_LENGTH = 200


@dataclass(frozen=True)
class BrokerReportInput:
    plan: Plan
    region: str
    quoted_on: date
    reported_value: Decimal | None
    message: str
    reporter_name: str
    reporter_contact: str = ""


def register_broker_report(
    report_input: BrokerReportInput, actor=None, now: datetime | None = None
) -> BrokerReport:
    """Brokers are sensors: a divergence they report becomes an alert the data team must close."""
    now = now or timezone.now()
    plan = report_input.plan
    report = BrokerReport.objects.create(
        plan=plan,
        region=report_input.region,
        quoted_on=report_input.quoted_on,
        reported_value=report_input.reported_value,
        message=report_input.message,
        reporter_name=report_input.reporter_name,
        reporter_contact=report_input.reporter_contact,
        created_by=actor if actor is not None and actor.is_authenticated else None,
    )
    MonitoringAlert.objects.create(
        kind=AlertKind.BROKER_REPORT,
        severity=Severity.WARNING,
        operator=plan.operator,
        plan=plan,
        params={
            "plan": plan.name,
            "region": report_input.region,
            "message": report_input.message[:_MESSAGE_PREVIEW_LENGTH],
        },
        fingerprint=f"broker_report:{report.public_id}",
        opened_at=now,
        last_seen_at=now,
    )
    record_event(
        AuditAction.BROKER_REPORTED,
        actor=actor,
        operator=plan.operator,
        target=report,
        payload={"plan": plan.name, "region": report_input.region},
        occurred_at=now,
    )
    return report


def find_alert(alert_id) -> MonitoringAlert:
    alert = (
        MonitoringAlert.objects.select_related("operator", "source", "plan")
        .filter(public_id=alert_id)
        .first()
    )
    if alert is None:
        raise NotFoundError("resource.not_found")
    return alert


def resolve_alert(alert: MonitoringAlert, now: datetime | None = None) -> MonitoringAlert:
    if alert.status != AlertStatus.OPEN:
        raise DomainError("alert.not_open")
    alert.status = AlertStatus.RESOLVED
    alert.resolved_at = now or timezone.now()
    alert.save(update_fields=["status", "resolved_at"])
    return alert


def list_open_alerts() -> QuerySet:
    severity_rank = Case(
        When(severity=Severity.ERROR, then=Value(0)),
        When(severity=Severity.WARNING, then=Value(1)),
        default=Value(2),
        output_field=IntegerField(),
    )
    return (
        MonitoringAlert.objects.filter(status=AlertStatus.OPEN)
        .select_related("operator", "source", "plan")
        .annotate(severity_rank=severity_rank)
        .order_by("severity_rank", "-opened_at")
    )
