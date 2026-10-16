from rest_framework import serializers


class AnsSyncRunResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField(source="public_id")
    dataset = serializers.CharField()
    status = serializers.CharField()
    source_location = serializers.CharField()
    started_at = serializers.DateTimeField()
    finished_at = serializers.DateTimeField(allow_null=True)
    rows_read = serializers.IntegerField()
    rows_saved = serializers.IntegerField()
    error_message = serializers.CharField()
