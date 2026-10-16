from rest_framework import serializers


class BatchReferenceResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField(source="public_id")
    status = serializers.CharField()


class DemoDeliveryResponseSerializer(serializers.Serializer):
    key = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    operator_name = serializers.CharField()
    channel = serializers.CharField()
    layout = serializers.CharField()
    filename = serializers.CharField()
    latest_batch = BatchReferenceResponseSerializer(allow_null=True)


class CollectionOutcomeResponseSerializer(serializers.Serializer):
    filename = serializers.CharField()
    status = serializers.CharField()
    batch = BatchReferenceResponseSerializer(allow_null=True)
    source_name = serializers.CharField(source="source.name", allow_null=True, default=None)
