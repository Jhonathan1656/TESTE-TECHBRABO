from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ans_reference.serializers import AnsSyncRunResponseSerializer
from apps.ans_reference.services.sync_service import list_recent_sync_runs


class AnsSyncRunListView(APIView):
    def get(self, request):
        return Response(AnsSyncRunResponseSerializer(list_recent_sync_runs(), many=True).data)
