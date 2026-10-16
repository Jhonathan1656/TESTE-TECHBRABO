from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsAnalyst
from apps.sources.models import CheckOutcome
from apps.sources.serializers import (
    SourceCheckResponseSerializer,
    SourceConfirmationRequestSerializer,
    SourceResponseSerializer,
)
from apps.sources.services import (
    find_source,
    find_source_freshness,
    find_sources_with_freshness,
    list_recent_checks,
    record_source_check,
)


class SourceListView(APIView):
    def get(self, request):
        return Response(SourceResponseSerializer(find_sources_with_freshness(), many=True).data)


class SourceCheckListView(APIView):
    def get(self, request, source_id):
        checks = list_recent_checks(find_source(source_id))
        return Response(SourceCheckResponseSerializer(checks, many=True).data)


class SourceConfirmationView(APIView):
    """An analyst confirms with the operator that the current material is still valid."""

    permission_classes = [IsAnalyst]

    def post(self, request, source_id):
        payload = SourceConfirmationRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        source = find_source(source_id)
        record_source_check(
            source, CheckOutcome.UNCHANGED, note=payload.validated_data["note"], actor=request.user
        )
        freshness = find_source_freshness(source)
        return Response(SourceResponseSerializer(freshness).data, status=status.HTTP_201_CREATED)
