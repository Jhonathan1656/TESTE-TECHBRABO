from django.db import models

from apps.core.domain.age_bands import AGE_BAND_CHOICES
from apps.core.models import PublicModel


class AnsOperatorRecord(models.Model):
    """Mirror of the ANS open-data file of active operators (Relatorio_cadop.csv)."""

    registration = models.CharField(max_length=6, primary_key=True)
    cnpj = models.CharField(max_length=14)
    corporate_name = models.CharField(max_length=255)
    trade_name = models.CharField(max_length=255, blank=True)
    modality = models.CharField(max_length=80)
    state = models.CharField(max_length=2, blank=True)
    registered_on = models.DateField(null=True, blank=True)
    synced_at = models.DateTimeField()

    def __str__(self) -> str:
        return f"{self.registration} {self.corporate_name}"


class AnsPlanRecord(models.Model):
    """Mirror of the ANS open-data plan characteristics file (pda-008)."""

    ans_plan_id = models.BigIntegerField(primary_key=True)
    product_code = models.CharField(max_length=30)
    name = models.CharField(max_length=255)
    operator_registration = models.CharField(max_length=6)
    contract_type = models.CharField(max_length=80, blank=True)
    segmentation = models.CharField(max_length=120, blank=True)
    coverage_area = models.CharField(max_length=60, blank=True)
    moderating_factor = models.CharField(max_length=60, blank=True)
    accommodation = models.CharField(max_length=60, blank=True)
    status = models.CharField(max_length=40)
    status_date = models.DateField(null=True, blank=True)
    synced_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(
                fields=["operator_registration", "product_code"], name="ans_plan_operator_code_idx"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.product_code} {self.name}"


class AnsPriceBandRecord(models.Model):
    """Mirror of the ANS technical-note price bands (VCM per age band, NTRP)."""

    ans_plan_id = models.BigIntegerField()
    operator_registration = models.CharField(max_length=6)
    note_code = models.BigIntegerField()
    note_registered_at = models.DateField()
    age_band = models.PositiveSmallIntegerField(choices=AGE_BAND_CHOICES)
    commercial_value = models.DecimalField(max_digits=12, decimal_places=2)
    care_expense = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    min_value = models.DecimalField(max_digits=12, decimal_places=2)
    max_value = models.DecimalField(max_digits=12, decimal_places=2)
    synced_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["ans_plan_id", "note_code", "age_band"],
                name="ans_price_band_unique_note_band",
            ),
        ]
        indexes = [models.Index(fields=["ans_plan_id"], name="ans_price_band_plan_idx")]

    def __str__(self) -> str:
        return f"{self.ans_plan_id} note {self.note_code} band {self.age_band}"


class AnsDataset(models.TextChoices):
    OPERATORS = "operators", "Active operators (CADOP)"
    PLANS = "plans", "Plan characteristics"
    PRICE_BANDS = "price_bands", "Technical-note price bands (VCM)"


class SyncStatus(models.TextChoices):
    RUNNING = "running", "Running"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"


class AnsSyncRun(PublicModel):
    dataset = models.CharField(max_length=20, choices=AnsDataset.choices)
    source_location = models.CharField(max_length=500)
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=SyncStatus.choices)
    rows_read = models.PositiveIntegerField(default=0)
    rows_saved = models.PositiveIntegerField(default=0)
    error_message = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["-started_at"]
