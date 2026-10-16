from decimal import Decimal

from rest_framework import serializers

from apps.audit.serializers import AuditEventResponseSerializer
from apps.catalog.serializers import OperatorResponseSerializer
from apps.core.messages import resolve_message
from apps.sources.serializers import SourceResponseSerializer


class AlertResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField(source="public_id")
    kind = serializers.CharField()
    severity = serializers.CharField()
    status = serializers.CharField()
    message = serializers.SerializerMethodField()
    operator_id = serializers.UUIDField(source="operator.public_id", allow_null=True, default=None)
    operator_name = serializers.CharField(source="operator.name", allow_null=True, default=None)
    source_id = serializers.UUIDField(source="source.public_id", allow_null=True, default=None)
    plan_id = serializers.UUIDField(source="plan.public_id", allow_null=True, default=None)
    plan_is_active = serializers.BooleanField(
        source="plan.is_active", allow_null=True, default=None
    )
    opened_at = serializers.DateTimeField()
    last_seen_at = serializers.DateTimeField()

    def get_message(self, alert) -> str:
        return resolve_message(f"alert.{alert.kind}", alert.params)


class OperatorHealthResponseSerializer(serializers.Serializer):
    operator = OperatorResponseSerializer()
    status = serializers.CharField()
    sources = SourceResponseSerializer(many=True)
    active_plans = serializers.IntegerField()
    priced_plans = serializers.IntegerField()
    oldest_effective_from = serializers.DateField(allow_null=True)
    next_change_on = serializers.DateField(allow_null=True)
    open_alerts = serializers.IntegerField()
    pending_batches = serializers.IntegerField()


class DashboardResponseSerializer(serializers.Serializer):
    generated_at = serializers.DateTimeField()
    pending_batches = serializers.IntegerField()
    open_errors = serializers.IntegerField()
    open_warnings = serializers.IntegerField()
    active_plans = serializers.IntegerField()
    priced_plans = serializers.IntegerField()
    confirmed_plans = serializers.IntegerField()
    operators = OperatorHealthResponseSerializer(many=True)
    alerts = AlertResponseSerializer(many=True)
    recent_events = AuditEventResponseSerializer(many=True)


class MonitoringRunResponseSerializer(serializers.Serializer):
    opened = serializers.IntegerField()
    refreshed = serializers.IntegerField()
    resolved = serializers.IntegerField()


class BrokerReportRequestSerializer(serializers.Serializer):
    plan = serializers.UUIDField()
    region = serializers.CharField(max_length=80)
    quoted_on = serializers.DateField()
    reported_value = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
        required=False,
        allow_null=True,
        default=None,
    )
    message = serializers.CharField(max_length=2000)
    reporter_name = serializers.CharField(max_length=120)
    reporter_contact = serializers.CharField(
        max_length=160, required=False, allow_blank=True, default=""
    )


class BrokerReportResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField(source="public_id")
    created_at = serializers.DateTimeField()
    plan_name = serializers.CharField(source="plan.name")
    region = serializers.CharField()
    quoted_on = serializers.DateField()
    reported_value = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    message = serializers.CharField()
    reporter_name = serializers.CharField()
