from pathlib import Path

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.catalog.models import Operator, Plan
from apps.core.domain.age_bands import AGE_BAND_CHOICES
from apps.core.models import PublicModel
from apps.sources.models import Source


def build_document_path(instance: "Document", filename: str) -> str:
    # Content-addressed storage: the file name is its hash, so a stored original never changes.
    extension = Path(filename).suffix.lower()
    return f"documents/{instance.sha256[:2]}/{instance.sha256}{extension}"


class DocumentFormat(models.TextChoices):
    PDF = "pdf", "PDF"
    XLSX = "xlsx", "Excel workbook"
    CSV = "csv", "CSV"


CONTENT_TYPES_BY_FORMAT = {
    DocumentFormat.PDF: "application/pdf",
    DocumentFormat.XLSX: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    DocumentFormat.CSV: "text/csv",
}


class Document(PublicModel):
    source = models.ForeignKey(Source, on_delete=models.PROTECT, related_name="documents")
    file = models.FileField(upload_to=build_document_path, max_length=255)
    original_filename = models.CharField(max_length=255)
    file_format = models.CharField(max_length=10, choices=DocumentFormat.choices)
    size_bytes = models.PositiveIntegerField()
    sha256 = models.CharField(max_length=64, unique=True)
    text_content = models.TextField(blank=True)
    received_at = models.DateTimeField(default=timezone.now, db_index=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        ordering = ["-received_at"]

    def __str__(self) -> str:
        return self.original_filename


class BatchStatus(models.TextChoices):
    PENDING_REVIEW = "pending_review", "Pending review"
    PUBLISHED = "published", "Published"
    REJECTED = "rejected", "Rejected"
    FAILED = "failed", "Extraction failed"


class ExtractionMethod(models.TextChoices):
    GRID = "grid", "Table grid detection"
    LLM = "llm", "AI extraction"
    NONE = "none", "Not extracted"


class ImportBatch(PublicModel):
    document = models.ForeignKey(Document, on_delete=models.PROTECT, related_name="batches")
    operator = models.ForeignKey(Operator, on_delete=models.PROTECT, related_name="batches")
    status = models.CharField(max_length=20, choices=BatchStatus.choices, db_index=True)
    region = models.CharField(max_length=80, blank=True)
    effective_from = models.DateField(null=True, blank=True)
    effective_until = models.DateField(null=True, blank=True)
    extraction_method = models.CharField(max_length=10, choices=ExtractionMethod.choices)
    extraction_details = models.JSONField(default=dict, blank=True)
    failure_code = models.CharField(max_length=80, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True)
    auto_published = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class PlanMatchMethod(models.TextChoices):
    ALIAS = "alias", "Exact name or learned alias"
    SIMILARITY = "similarity", "Similarity"
    MANUAL = "manual", "Mapped by a reviewer"
    UNMATCHED = "unmatched", "Not matched"


class ExtractedPlan(PublicModel):
    """A plan label as found in the document, and the catalog plan it maps to."""

    batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name="extracted_plans")
    label = models.CharField(max_length=200)
    position = models.PositiveSmallIntegerField()
    plan = models.ForeignKey(
        Plan, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    match_method = models.CharField(max_length=12, choices=PlanMatchMethod.choices)
    match_score = models.FloatField(null=True, blank=True)
    suggestions = models.JSONField(default=list, blank=True)
    is_excluded = models.BooleanField(default=False)

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(fields=["batch", "label"], name="extracted_plan_unique_label"),
        ]


class ExtractedPrice(PublicModel):
    extracted_plan = models.ForeignKey(
        ExtractedPlan, on_delete=models.CASCADE, related_name="prices"
    )
    age_band = models.PositiveSmallIntegerField(choices=AGE_BAND_CHOICES)
    raw_text = models.CharField(max_length=120, blank=True)
    extracted_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    corrected_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    corrected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    corrected_at = models.DateTimeField(null=True, blank=True)
    previous_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    location = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["age_band"]
        constraints = [
            models.UniqueConstraint(
                fields=["extracted_plan", "age_band"], name="extracted_price_unique_band"
            ),
        ]

    @property
    def final_value(self):
        return self.corrected_value if self.corrected_value is not None else self.extracted_value
