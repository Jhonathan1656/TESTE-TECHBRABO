from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.catalog.models import Operator
from apps.core.models import PublicModel


class SourceChannel(models.TextChoices):
    OPERATOR_PORTAL = "operator_portal", "Operator broker portal"
    EMAIL_INBOX = "email_inbox", "Commercial e-mail inbox"
    PARTNER = "partner", "Partner (administrator, brokerage)"
    BROKER = "broker", "Material sent by brokers"
    MANUAL_UPLOAD = "manual_upload", "Manual upload by the data team"


class TrustLevel(models.IntegerChoices):
    COMMUNITY = 1, "Community"
    PARTNER = 2, "Partner"
    OFFICIAL = 3, "Official"


class Source(PublicModel):
    operator = models.ForeignKey(Operator, on_delete=models.PROTECT, related_name="sources")
    name = models.CharField(max_length=120)
    channel = models.CharField(max_length=20, choices=SourceChannel.choices)
    trust_level = models.PositiveSmallIntegerField(choices=TrustLevel.choices)
    expected_update_days = models.PositiveSmallIntegerField(default=30)
    tolerance_days = models.PositiveSmallIntegerField(default=7)
    contact = models.CharField(max_length=160, blank=True)
    auto_approve = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["operator__name", "name"]

    def __str__(self) -> str:
        return self.name


class CheckOutcome(models.TextChoices):
    NEW_MATERIAL = "new_material", "New material received"
    UNCHANGED = "unchanged", "Confirmed unchanged"
    FAILED = "failed", "Check failed"


class SourceCheck(PublicModel):
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name="checks")
    checked_at = models.DateTimeField(default=timezone.now, db_index=True)
    outcome = models.CharField(max_length=20, choices=CheckOutcome.choices)
    document = models.ForeignKey(
        "ingestion.Document",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    note = models.CharField(max_length=240, blank=True)
    checked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        ordering = ["-checked_at"]
