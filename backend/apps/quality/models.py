from django.conf import settings
from django.db import models

from apps.core.domain.age_bands import AGE_BAND_CHOICES
from apps.core.domain.severity import SEVERITY_CHOICES
from apps.core.models import PublicModel
from apps.ingestion.models import ExtractedPlan, ImportBatch


class IssueStatus(models.TextChoices):
    OPEN = "open", "Open"
    ACKNOWLEDGED = "acknowledged", "Acknowledged with justification"
    RESOLVED = "resolved", "Resolved"


class ValidationIssue(PublicModel):
    batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name="issues")
    rule_code = models.CharField(max_length=80)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)
    status = models.CharField(max_length=15, choices=IssueStatus.choices, default=IssueStatus.OPEN)
    extracted_plan = models.ForeignKey(
        ExtractedPlan,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="issues",
    )
    age_band = models.PositiveSmallIntegerField(null=True, blank=True, choices=AGE_BAND_CHOICES)
    params = models.JSONField(default=dict, blank=True)
    fingerprint = models.CharField(max_length=255)
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledgement_note = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["batch", "fingerprint"], name="validation_issue_unique_fingerprint"
            ),
        ]
