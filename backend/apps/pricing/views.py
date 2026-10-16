from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ans_reference.services.lookup_service import find_plan_references
from apps.catalog.services.plan_catalog_service import find_plan
from apps.pricing.serializers import (
    PlanPricingResponseSerializer,
    PlanQuoteResponseSerializer,
    QuoteRequestSerializer,
)
from apps.pricing.services.price_lookup_service import list_plan_history, list_pricing_regions
from apps.pricing.services.quote_service import QuoteRequest, build_quote


class RegionListView(APIView):
    def get(self, request):
        return Response(list_pricing_regions())


class QuoteView(APIView):
    def post(self, request):
        payload = QuoteRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        quotes = build_quote(
            QuoteRequest(
                ages=tuple(data["ages"]),
                on_date=data["on_date"],
                region=data["region"],
                plan_ids=tuple(data["plans"]),
                operator_id=data["operator"],
                known_at=data["known_at"],
            )
        )
        return Response(PlanQuoteResponseSerializer(quotes, many=True).data)


class PlanPricingView(APIView):
    def get(self, request, plan_id):
        plan = find_plan(plan_id)
        pricing = {
            "plan": plan,
            "ans": find_plan_references([plan]).get(plan.id),
            "versions": list_plan_history(plan),
        }
        context = {"today": timezone.localdate()}
        return Response(PlanPricingResponseSerializer(pricing, context=context).data)
