from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.serializers import (
    OperatorResponseSerializer,
    PlanListQuerySerializer,
    PlanResponseSerializer,
)
from apps.catalog.services.plan_catalog_service import (
    deactivate_plan,
    find_plan,
    list_operators,
    list_plans,
)
from apps.core.permissions import IsReviewer


class OperatorListView(APIView):
    def get(self, request):
        return Response(OperatorResponseSerializer(list_operators(), many=True).data)


class PlanListView(APIView):
    def get(self, request):
        query = PlanListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        plans = list_plans(
            operator_id=query.validated_data.get("operator"),
            include_inactive=query.validated_data["include_inactive"],
        )
        return Response(PlanResponseSerializer(plans, many=True).data)


class PlanDeactivationView(APIView):
    permission_classes = [IsReviewer]

    def post(self, request, plan_id):
        plan = deactivate_plan(find_plan(plan_id), request.user)
        return Response(PlanResponseSerializer(plan).data)
