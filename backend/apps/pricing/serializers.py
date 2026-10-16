from rest_framework import serializers

from apps.catalog.serializers import PlanResponseSerializer
from apps.core.domain.age_bands import AgeBand
from apps.core.serializers import UserSummaryResponseSerializer
from apps.ingestion.serializers import DocumentSummaryResponseSerializer
from apps.pricing.services.price_lookup_service import classify_table_state, find_effective_until
from apps.sources.serializers import FreshnessResponseSerializer, SourceSummaryResponseSerializer

MAX_QUOTED_LIVES = 30
MAX_AGE = 120


class AnsReferenceResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    status_label = serializers.CharField()
    status_date = serializers.DateField(allow_null=True)
    note_code = serializers.IntegerField(allow_null=True)
    note_registered_at = serializers.DateField(allow_null=True)


class PriceEntryResponseSerializer(serializers.Serializer):
    age_band = serializers.IntegerField()
    band_label = serializers.SerializerMethodField()
    value = serializers.DecimalField(max_digits=12, decimal_places=2)
    was_corrected = serializers.BooleanField()
    location = serializers.JSONField()

    def get_band_label(self, entry) -> str:
        return AgeBand(entry.age_band).label


class PriceTableProvenanceResponseSerializer(serializers.Serializer):
    """Where a published price came from: the version, its document, source and approval."""

    id = serializers.UUIDField(source="public_id")
    region = serializers.CharField()
    effective_from = serializers.DateField(source="validity.lower")
    effective_until = serializers.SerializerMethodField()
    recorded_at = serializers.DateTimeField()
    superseded_at = serializers.DateTimeField(allow_null=True)
    batch_id = serializers.UUIDField(source="batch.public_id")
    auto_published = serializers.BooleanField(source="batch.auto_published")
    published_by = UserSummaryResponseSerializer(source="batch.reviewed_by", allow_null=True)
    published_at = serializers.DateTimeField(source="batch.reviewed_at", allow_null=True)
    extraction_method = serializers.CharField(source="batch.extraction_method")
    document = DocumentSummaryResponseSerializer(source="batch.document")
    source = SourceSummaryResponseSerializer(source="batch.document.source")

    def get_effective_until(self, table):
        until = find_effective_until(table)
        return until.isoformat() if until else None


class PriceTableVersionResponseSerializer(PriceTableProvenanceResponseSerializer):
    state = serializers.SerializerMethodField()
    derived_from_id = serializers.UUIDField(
        source="derived_from.public_id", allow_null=True, default=None
    )
    superseded_by_batch_id = serializers.UUIDField(
        source="superseded_by.public_id", allow_null=True, default=None
    )
    entries = PriceEntryResponseSerializer(many=True)

    def get_state(self, table) -> str:
        return classify_table_state(table, self.context["today"]).value


class PlanPricingResponseSerializer(serializers.Serializer):
    plan = PlanResponseSerializer()
    ans = AnsReferenceResponseSerializer(allow_null=True)
    versions = PriceTableVersionResponseSerializer(many=True)


class BeneficiaryPriceResponseSerializer(serializers.Serializer):
    age = serializers.IntegerField()
    age_band = serializers.IntegerField()
    band_label = serializers.SerializerMethodField()
    value = serializers.DecimalField(max_digits=12, decimal_places=2)

    def get_band_label(self, price) -> str:
        return price.age_band.label


class ScheduledChangeResponseSerializer(serializers.Serializer):
    effective_from = serializers.DateField(source="table.validity.lower")
    total = serializers.DecimalField(max_digits=14, decimal_places=2)
    change = serializers.DecimalField(max_digits=8, decimal_places=4)
    table_id = serializers.UUIDField(source="table.public_id")


class PlanQuoteResponseSerializer(serializers.Serializer):
    plan = PlanResponseSerializer(source="table.plan")
    total = serializers.DecimalField(max_digits=14, decimal_places=2)
    beneficiaries = BeneficiaryPriceResponseSerializer(many=True)
    table = PriceTableProvenanceResponseSerializer()
    freshness = FreshnessResponseSerializer(source="source_freshness", allow_null=True)
    ans = AnsReferenceResponseSerializer(source="ans_reference", allow_null=True)
    scheduled_change = ScheduledChangeResponseSerializer(allow_null=True)


class QuoteRequestSerializer(serializers.Serializer):
    ages = serializers.ListField(
        child=serializers.IntegerField(min_value=0, max_value=MAX_AGE),
        min_length=1,
        max_length=MAX_QUOTED_LIVES,
    )
    on_date = serializers.DateField()
    region = serializers.CharField(max_length=80)
    plans = serializers.ListField(child=serializers.UUIDField(), required=False, default=list)
    operator = serializers.UUIDField(required=False, allow_null=True, default=None)
    known_at = serializers.DateTimeField(required=False, allow_null=True, default=None)
