from django.conf import settings
from django.db import models
from django.utils import timezone


class AuditAction(models.TextChoices):
    DOCUMENT_RECEIVED = "document.received", "Document received"
    BATCH_CREATED = "batch.created", "Batch created"
    BATCH_FAILED = "batch.failed", "Batch extraction failed"
    BATCH_DATES_CHANGED = "batch.dates_changed", "Batch effective dates changed"
    PRICE_CORRECTED = "price.corrected", "Extracted price corrected"
    PLAN_MAPPED = "plan.mapped", "Plan label mapped"
    PLAN_EXCLUDED = "plan.excluded", "Plan excluded from batch"
    PLAN_INCLUDED = "plan.included", "Plan included back in batch"
    PLAN_DEACTIVATED = "plan.deactivated", "Plan removed from the quoter"
    ISSUE_ACKNOWLEDGED = "issue.acknowledged", "Warning acknowledged"
    BATCH_PUBLISHED = "batch.published", "Batch published"
    BATCH_AUTO_PUBLISHED = "batch.auto_published", "Batch auto-published"
    BATCH_REJECTED = "batch.rejected", "Batch rejected"
    SOURCE_CHECKED = "source.checked", "Source checked"
    ANS_SYNCED = "ans.synced", "ANS reference synced"
    MONITORING_RAN = "monitoring.ran", "Monitoring checks ran"
    BROKER_REPORTED = "broker.reported", "Broker reported a divergence"


class AuditEvent(models.Model):
    """Append-only trail: application code only ever inserts rows."""

    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    action = models.CharField(max_length=40, choices=AuditAction.choices)
    operator = models.ForeignKey(
        "catalog.Operator",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    target_type = models.CharField(max_length=40, blank=True)
    target_public_id = models.UUIDField(null=True, blank=True, db_index=True)
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-occurred_at", "-id"]

    def __str__(self) -> str:
        return f"{self.occurred_at:%Y-%m-%d %H:%M} {self.action}"
