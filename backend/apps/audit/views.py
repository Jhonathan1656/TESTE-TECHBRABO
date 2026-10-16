from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.serializers import AuditEventListQuerySerializer, AuditEventResponseSerializer
from apps.audit.services import list_recent_events


class AuditEventListView(APIView):
    def get(self, request):
        query = AuditEventListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        events = list_recent_events(
            limit=query.validated_data["limit"],
            target_public_id=query.validated_data.get("target"),
        )
        return Response(AuditEventResponseSerializer(events, many=True).data)
