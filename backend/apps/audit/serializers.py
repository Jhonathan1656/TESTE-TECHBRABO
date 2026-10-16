from rest_framework import serializers

from apps.core.serializers import UserSummaryResponseSerializer


class AuditEventResponseSerializer(serializers.Serializer):
    occurred_at = serializers.DateTimeField()
    action = serializers.CharField()
    actor = UserSummaryResponseSerializer(allow_null=True)
    operator_name = serializers.CharField(source="operator.name", allow_null=True, default=None)
    target_type = serializers.CharField()
    target_id = serializers.UUIDField(source="target_public_id", allow_null=True)
    payload = serializers.JSONField()


class AuditEventListQuerySerializer(serializers.Serializer):
    target = serializers.UUIDField(required=False)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=200, default=30)
