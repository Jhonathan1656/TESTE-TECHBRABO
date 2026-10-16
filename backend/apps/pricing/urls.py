from django.urls import path

from apps.pricing.views import PlanPricingView, QuoteView, RegionListView

urlpatterns = [
    path("regions", RegionListView.as_view(), name="region-list"),
    path("quotes", QuoteView.as_view(), name="quote"),
    path("plans/<uuid:plan_id>/pricing", PlanPricingView.as_view(), name="plan-pricing"),
]
