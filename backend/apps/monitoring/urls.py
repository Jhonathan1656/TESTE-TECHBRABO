from django.urls import path

from apps.monitoring.views import (
    AlertListView,
    AlertResolutionView,
    BrokerReportView,
    DashboardView,
    MonitoringRunView,
)

urlpatterns = [
    path("dashboard", DashboardView.as_view(), name="dashboard"),
    path("alerts", AlertListView.as_view(), name="alert-list"),
    path(
        "alerts/<uuid:alert_id>/resolution", AlertResolutionView.as_view(), name="alert-resolution"
    ),
    path("monitoring/runs", MonitoringRunView.as_view(), name="monitoring-run"),
    path("broker-reports", BrokerReportView.as_view(), name="broker-report"),
]
