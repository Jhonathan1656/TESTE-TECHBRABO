from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.services.plan_catalog_service import find_plan
from apps.core.permissions import IsAnalyst
from apps.monitoring.serializers import (
    AlertResponseSerializer,
    BrokerReportRequestSerializer,
    BrokerReportResponseSerializer,
    DashboardResponseSerializer,
    MonitoringRunResponseSerializer,
)
from apps.monitoring.services.alert_service import (
    BrokerReportInput,
    find_alert,
    list_open_alerts,
    register_broker_report,
    resolve_alert,
)
from apps.monitoring.services.dashboard_service import build_dashboard
from apps.monitoring.services.monitoring_service import run_monitoring_checks


class DashboardView(APIView):
    def get(self, request):
        return Response(DashboardResponseSerializer(build_dashboard()).data)


class AlertListView(APIView):
    def get(self, request):
        return Response(AlertResponseSerializer(list_open_alerts(), many=True).data)


class AlertResolutionView(APIView):
    permission_classes = [IsAnalyst]

    def post(self, request, alert_id):
        return Response(AlertResponseSerializer(resolve_alert(find_alert(alert_id))).data)


class MonitoringRunView(APIView):
    permission_classes = [IsAnalyst]

    def post(self, request):
        summary = run_monitoring_checks()
        return Response(
            MonitoringRunResponseSerializer(summary).data, status=status.HTTP_201_CREATED
        )


class BrokerReportView(APIView):
    def post(self, request):
        payload = BrokerReportRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        report = register_broker_report(
            BrokerReportInput(
                plan=find_plan(data["plan"]),
                region=data["region"],
                quoted_on=data["quoted_on"],
                reported_value=data["reported_value"],
                message=data["message"],
                reporter_name=data["reporter_name"],
                reporter_contact=data["reporter_contact"],
            ),
            actor=request.user,
        )
        return Response(BrokerReportResponseSerializer(report).data, status=status.HTTP_201_CREATED)
