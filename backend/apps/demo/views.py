from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsAnalyst
from apps.demo.serializers import (
    CollectionOutcomeResponseSerializer,
    DemoDeliveryResponseSerializer,
)
from apps.demo.services.delivery_service import (
    build_demo_file,
    collect_demo_delivery,
    ensure_demo_mode,
    list_demo_deliveries,
    require_demo_delivery,
)
from apps.ingestion.models import CONTENT_TYPES_BY_FORMAT
from apps.ingestion.services.document_intake_service import detect_file_format


class DemoDeliveryListView(APIView):
    def get(self, request):
        ensure_demo_mode()
        return Response(DemoDeliveryResponseSerializer(list_demo_deliveries(), many=True).data)


class DemoDeliveryCollectionView(APIView):
    """Pushes a fictional delivery through the same collector used for real inboxes and portals."""

    permission_classes = [IsAnalyst]

    def post(self, request, key):
        ensure_demo_mode()
        outcome = collect_demo_delivery(key)
        return Response(
            CollectionOutcomeResponseSerializer(outcome).data, status=status.HTTP_201_CREATED
        )


class DemoDeliveryFileView(APIView):
    def get(self, request, key):
        ensure_demo_mode()
        incoming = build_demo_file(require_demo_delivery(key), timezone.localdate())
        response = HttpResponse(
            incoming.content,
            content_type=CONTENT_TYPES_BY_FORMAT[detect_file_format(incoming.name)],
        )
        response["Content-Disposition"] = f'attachment; filename="{incoming.name}"'
        return response
