from django.urls import path

from apps.catalog.views import OperatorListView, PlanDeactivationView, PlanListView

urlpatterns = [
    path("operators", OperatorListView.as_view(), name="operator-list"),
    path("plans", PlanListView.as_view(), name="plan-list"),
    path(
        "plans/<uuid:plan_id>/deactivation",
        PlanDeactivationView.as_view(),
        name="plan-deactivation",
    ),
]
