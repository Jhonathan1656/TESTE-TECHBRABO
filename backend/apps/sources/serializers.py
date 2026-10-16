from rest_framework import serializers

from apps.catalog.serializers import OperatorSummaryResponseSerializer
from apps.core.serializers import UserSummaryResponseSerializer


class SourceSummaryResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField(source="public_id")
    name = serializers.CharField()
    channel = serializers.CharField()
    trust_level = serializers.IntegerField()


class FreshnessResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    last_success_at = serializers.DateTimeField(allow_null=True)
    last_new_material_at = serializers.DateTimeField(allow_null=True)
    last_failure_at = serializers.DateTimeField(allow_null=True)
    days_since_success = serializers.IntegerField(allow_null=True)


class SourceResponseSerializer(serializers.Serializer):
    """Serializes a SourceFreshness: the source plus how current its information is."""

    id = serializers.UUIDField(source="source.public_id")
    name = serializers.CharField(source="source.name")
    channel = serializers.CharField(source="source.channel")
    trust_level = serializers.IntegerField(source="source.trust_level")
    expected_update_days = serializers.IntegerField(source="source.expected_update_days")
    tolerance_days = serializers.IntegerField(source="source.tolerance_days")
    contact = serializers.CharField(source="source.contact")
    auto_approve = serializers.BooleanField(source="source.auto_approve")
    operator = OperatorSummaryResponseSerializer(source="source.operator")
    freshness = FreshnessResponseSerializer(source="*")


class SourceCheckResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField(source="public_id")
    checked_at = serializers.DateTimeField()
    outcome = serializers.CharField()
    note = serializers.CharField()
    checked_by = UserSummaryResponseSerializer(allow_null=True)
    document_id = serializers.UUIDField(source="document.public_id", allow_null=True, default=None)
    document_filename = serializers.CharField(
        source="document.original_filename", allow_null=True, default=None
    )


class SourceConfirmationRequestSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=240, allow_blank=True, required=False, default="")
