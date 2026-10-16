from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateRangeField, RangeOperators
from django.db import models

from apps.catalog.models import Plan
from apps.core.domain.age_bands import AGE_BAND_CHOICES
from apps.core.models import PublicModel
from apps.ingestion.models import ImportBatch


class PriceTableQuerySet(models.QuerySet):
    def current(self) -> "PriceTableQuerySet":
        return self.filter(superseded_at__isnull=True)

    def known_at(self, moment) -> "PriceTableQuerySet":
        return self.filter(recorded_at__lte=moment).filter(
            models.Q(superseded_at__isnull=True) | models.Q(superseded_at__gt=moment)
        )


class PriceTable(PublicModel):
    """A published price table version.

    Bitemporal: `validity` is when the prices apply in the real world (vigência);
    `recorded_at`/`superseded_at` is when the system held that belief. Rows are never
    updated in place — a correction supersedes the row and records a new one.
    """

    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="price_tables")
    region = models.CharField(max_length=80)
    validity = DateRangeField()
    batch = models.ForeignKey(ImportBatch, on_delete=models.PROTECT, related_name="price_tables")
    recorded_at = models.DateTimeField()
    superseded_at = models.DateTimeField(null=True, blank=True)
    superseded_by = models.ForeignKey(
        ImportBatch,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="superseded_price_tables",
    )
    derived_from = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="derivatives"
    )

    objects = PriceTableQuerySet.as_manager()

    class Meta:
        ordering = ["plan_id", "region", "validity"]
        constraints = [
            ExclusionConstraint(
                name="price_table_current_validity_no_overlap",
                expressions=[
                    ("plan", RangeOperators.EQUAL),
                    ("region", RangeOperators.EQUAL),
                    ("validity", RangeOperators.OVERLAPS),
                ],
                condition=models.Q(superseded_at__isnull=True),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.plan_id} {self.region} {self.validity}"


class PriceEntry(models.Model):
    table = models.ForeignKey(PriceTable, on_delete=models.CASCADE, related_name="entries")
    age_band = models.PositiveSmallIntegerField(choices=AGE_BAND_CHOICES)
    value = models.DecimalField(max_digits=12, decimal_places=2)
    location = models.JSONField(default=dict, blank=True)
    was_corrected = models.BooleanField(default=False)

    class Meta:
        ordering = ["age_band"]
        constraints = [
            models.UniqueConstraint(fields=["table", "age_band"], name="price_entry_unique_band"),
            models.CheckConstraint(condition=models.Q(value__gt=0), name="price_entry_positive"),
        ]

    def __str__(self) -> str:
        return f"band {self.age_band}: {self.value}"
