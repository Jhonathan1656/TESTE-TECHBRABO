import statistics
from decimal import Decimal

from rest_framework import serializers

from apps.audit.serializers import AuditEventResponseSerializer
from apps.catalog.serializers import (
    OperatorSummaryResponseSerializer,
    PlanSummaryResponseSerializer,
)
from apps.core.domain.age_bands import AgeBand
from apps.core.domain.severity import Severity
from apps.core.messages import resolve_message
from apps.core.serializers import UserSummaryResponseSerializer
from apps.ingestion.models import BatchStatus, ImportBatch
from apps.quality.models import IssueStatus
from apps.sources.serializers import SourceSummaryResponseSerializer

_CHANGE_PRECISION = Decimal("0.0001")
_SEVERITY_ORDER = {Severity.ERROR: 0, Severity.WARNING: 1, Severity.INFO: 2}
_STATUS_ORDER = {IssueStatus.OPEN: 0, IssueStatus.ACKNOWLEDGED: 1, IssueStatus.RESOLVED: 2}


def calculate_change(value: Decimal | None, previous: Decimal | None) -> Decimal | None:
    if value is None or not previous:
        return None
    return (value / previous - 1).quantize(_CHANGE_PRECISION)


class DocumentSummaryResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField(source="public_id")
    filename = serializers.CharField(source="original_filename")
    file_format = serializers.CharField()
    size_bytes = serializers.IntegerField()
    sha256 = serializers.CharField()
    received_at = serializers.DateTimeField()
    uploaded_by = UserSummaryResponseSerializer(allow_null=True)


class BatchSummaryResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField(source="public_id")
    status = serializers.CharField()
    region = serializers.CharField()
    effective_from = serializers.DateField(allow_null=True)
    effective_until = serializers.DateField(allow_null=True)
    extraction_method = serializers.CharField()
    created_at = serializers.DateTimeField()
    reviewed_at = serializers.DateTimeField(allow_null=True)
    reviewed_by = UserSummaryResponseSerializer(allow_null=True)
    review_note = serializers.CharField()
    auto_published = serializers.BooleanField()
    failure_code = serializers.CharField()
    failure_message = serializers.SerializerMethodField()
    operator = OperatorSummaryResponseSerializer()
    source = SourceSummaryResponseSerializer(source="document.source")
    document = DocumentSummaryResponseSerializer()
    counts = serializers.SerializerMethodField()

    def get_failure_message(self, batch: ImportBatch) -> str | None:
        if not batch.failure_code:
            return None
        return resolve_message(
            batch.failure_code, batch.extraction_details.get("failure_params") or {}
        )

    def get_counts(self, batch: ImportBatch) -> dict:
        return {
            "plans": batch.plan_count,
            "open_errors": batch.open_errors,
            "open_warnings": batch.open_warnings,
        }


class ExtractedPriceResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField(source="public_id")
    age_band = serializers.IntegerField()
    band_label = serializers.SerializerMethodField()
    raw_text = serializers.CharField()
    extracted_value = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    corrected_value = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    final_value = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    previous_value = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    change = serializers.SerializerMethodField()
    location = serializers.JSONField()
    corrected_by = UserSummaryResponseSerializer(allow_null=True)
    corrected_at = serializers.DateTimeField(allow_null=True)

    def get_band_label(self, price) -> str:
        return AgeBand(price.age_band).label

    def get_change(self, price) -> str | None:
        change = calculate_change(price.final_value, price.previous_value)
        return str(change) if change is not None else None


class ExtractedPlanResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField(source="public_id")
    label = serializers.CharField()
    position = serializers.IntegerField()
    plan = PlanSummaryResponseSerializer(allow_null=True)
    match_method = serializers.CharField()
    match_score = serializers.FloatField(allow_null=True)
    suggestions = serializers.ListField(child=serializers.CharField())
    is_excluded = serializers.BooleanField()
    prices = ExtractedPriceResponseSerializer(many=True)


class ValidationIssueResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField(source="public_id")
    rule_code = serializers.CharField()
    severity = serializers.CharField()
    status = serializers.CharField()
    message = serializers.SerializerMethodField()
    extracted_plan_id = serializers.UUIDField(
        source="extracted_plan.public_id", allow_null=True, default=None
    )
    age_band = serializers.IntegerField(allow_null=True)
    params = serializers.JSONField()
    acknowledged_by = UserSummaryResponseSerializer(allow_null=True)
    acknowledged_at = serializers.DateTimeField(allow_null=True)
    acknowledgement_note = serializers.CharField()
    resolved_at = serializers.DateTimeField(allow_null=True)

    def get_message(self, issue) -> str:
        return resolve_message(f"rule.{issue.rule_code}", issue.params)


class BatchDetailResponseSerializer(BatchSummaryResponseSerializer):
    plans = ExtractedPlanResponseSerializer(source="extracted_plans", many=True)
    issues = serializers.SerializerMethodField()
    summary = serializers.SerializerMethodField()
    can_publish = serializers.SerializerMethodField()
    plan_candidates = serializers.SerializerMethodField()
    timeline = serializers.SerializerMethodField()

    def get_issues(self, batch: ImportBatch) -> list[dict]:
        issues = sorted(
            batch.issues.all(),
            key=lambda issue: (
                _STATUS_ORDER[issue.status],
                _SEVERITY_ORDER[issue.severity],
                issue.id,
            ),
        )
        return ValidationIssueResponseSerializer(issues, many=True).data

    def get_summary(self, batch: ImportBatch) -> dict:
        prices = [
            price
            for plan in batch.extracted_plans.all()
            if not plan.is_excluded
            for price in plan.prices.all()
        ]
        changes = [
            change
            for price in prices
            if (change := calculate_change(price.final_value, price.previous_value)) is not None
        ]
        issues = list(batch.issues.all())
        return {
            "plans": sum(1 for plan in batch.extracted_plans.all() if not plan.is_excluded),
            "excluded_plans": sum(1 for plan in batch.extracted_plans.all() if plan.is_excluded),
            "prices": len(prices),
            "compared_prices": len(changes),
            "changed_prices": sum(1 for change in changes if change != 0),
            "corrected_prices": sum(1 for price in prices if price.corrected_value is not None),
            "median_change": str(statistics.median(changes)) if changes else None,
            "open_errors": sum(1 for issue in issues if self._is_open(issue, Severity.ERROR)),
            "open_warnings": sum(1 for issue in issues if self._is_open(issue, Severity.WARNING)),
            "acknowledged": sum(1 for issue in issues if issue.status == IssueStatus.ACKNOWLEDGED),
            "infos": sum(1 for issue in issues if self._is_open(issue, Severity.INFO)),
        }

    def get_can_publish(self, batch: ImportBatch) -> bool:
        summary = self.get_summary(batch)
        return (
            batch.status == BatchStatus.PENDING_REVIEW
            and summary["open_errors"] == 0
            and summary["open_warnings"] == 0
            and summary["plans"] > 0
        )

    def get_plan_candidates(self, batch: ImportBatch) -> list[dict]:
        return PlanSummaryResponseSerializer(
            self.context.get("plan_candidates", []), many=True
        ).data

    def get_timeline(self, batch: ImportBatch) -> list[dict]:
        return AuditEventResponseSerializer(self.context.get("timeline", []), many=True).data

    @staticmethod
    def _is_open(issue, severity: Severity) -> bool:
        return issue.status == IssueStatus.OPEN and issue.severity == severity


class BatchListQuerySerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=BatchStatus.choices, required=False)
    operator = serializers.UUIDField(required=False)


class DocumentUploadRequestSerializer(serializers.Serializer):
    file = serializers.FileField()
    source = serializers.UUIDField()
    effective_from = serializers.DateField(required=False, allow_null=True)
    effective_until = serializers.DateField(required=False, allow_null=True)
    region = serializers.CharField(required=False, allow_blank=True, max_length=80)


class PriceCorrectionRequestSerializer(serializers.Serializer):
    corrected_value = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0.01"), allow_null=True, required=False
    )


class PlanMappingRequestSerializer(serializers.Serializer):
    plan = serializers.UUIDField()


class PlanExclusionRequestSerializer(serializers.Serializer):
    excluded = serializers.BooleanField()


class IssueAcknowledgementRequestSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=500)


class EffectiveDatesRequestSerializer(serializers.Serializer):
    effective_from = serializers.DateField(allow_null=True)
    effective_until = serializers.DateField(allow_null=True, required=False, default=None)
    region = serializers.CharField(max_length=80, allow_blank=True)


class PublicationRequestSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class RejectionRequestSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500)
