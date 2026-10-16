from rest_framework import serializers


class OperatorSummaryResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField(source="public_id")
    name = serializers.CharField()
    ans_registration = serializers.CharField()
    is_fictional = serializers.BooleanField()


class OperatorResponseSerializer(OperatorSummaryResponseSerializer):
    cnpj = serializers.CharField()
    modality = serializers.CharField()
    access_level = serializers.CharField()


class PlanSummaryResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField(source="public_id")
    name = serializers.CharField()
    product_line = serializers.CharField()
    ans_code = serializers.CharField(source="formatted_ans_code")
    contract_type = serializers.CharField()
    accommodation = serializers.CharField()
    coverage_area = serializers.CharField()
    segmentation = serializers.CharField()
    has_coparticipation = serializers.BooleanField()
    is_active = serializers.BooleanField()


class PlanResponseSerializer(PlanSummaryResponseSerializer):
    operator = OperatorSummaryResponseSerializer()


class PlanListQuerySerializer(serializers.Serializer):
    operator = serializers.UUIDField(required=False)
    include_inactive = serializers.BooleanField(required=False, default=False)
