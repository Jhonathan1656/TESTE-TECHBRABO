from django.conf import settings
from django.db import models

from apps.catalog.models import Operator, Plan
from apps.core.domain.severity import SEVERITY_CHOICES
from apps.core.models import PublicModel
from apps.sources.models import Source


class AlertKind(models.TextChoices):
    SOURCE_OVERDUE = "source_overdue", "Source overdue"
    SOURCE_NEVER_CHECKED = "source_never_checked", "Source never checked"
    SOURCE_CHECK_FAILED = "source_check_failed", "Source check failed"
    STALE_PRICE_TABLE = "stale_price_table", "Stale price table"
    PLAN_NOT_ACTIVE_AT_ANS = "plan_not_active_at_ans", "Plan not active at ANS"
    BROKER_REPORT = "broker_report", "Broker divergence report"


class AlertStatus(models.TextChoices):
    OPEN = "open", "Open"
    RESOLVED = "resolved", "Resolved"


class MonitoringAlert(PublicModel):
    kind = models.CharField(max_length=30, choices=AlertKind.choices)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)
    status = models.CharField(
        max_length=10, choices=AlertStatus.choices, default=AlertStatus.OPEN, db_index=True
    )
    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, null=True, blank=True, related_name="alerts"
    )
    source = models.ForeignKey(
        Source, on_delete=models.CASCADE, null=True, blank=True, related_name="alerts"
    )
    plan = models.ForeignKey(
        Plan, on_delete=models.CASCADE, null=True, blank=True, related_name="alerts"
    )
    params = models.JSONField(default=dict, blank=True)
    fingerprint = models.CharField(max_length=255)
    opened_at = models.DateTimeField()
    last_seen_at = models.DateTimeField()
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-opened_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["fingerprint"],
                condition=models.Q(status="open"),
                name="monitoring_alert_unique_open_fingerprint",
            ),
        ]


class BrokerReport(PublicModel):
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="broker_reports")
    region = models.CharField(max_length=80)
    quoted_on = models.DateField()
    reported_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    message = models.TextField()
    reporter_name = models.CharField(max_length=120)
    reporter_contact = models.CharField(max_length=160, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        ordering = ["-created_at"]
