from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from django.utils import timezone

from apps.ans_reference.services.lookup_service import AnsPlanReference, find_plan_references
from apps.core.domain.age_bands import AgeBand, find_band_for_age
from apps.pricing.models import PriceTable
from apps.pricing.services.price_lookup_service import with_provenance
from apps.sources.services import SourceFreshness, find_sources_with_freshness


@dataclass(frozen=True)
class QuoteRequest:
    ages: tuple[int, ...]
    on_date: date
    region: str
    plan_ids: tuple[UUID, ...] = ()
    operator_id: UUID | None = None
    known_at: datetime | None = None


@dataclass(frozen=True)
class BeneficiaryPrice:
    age: int
    age_band: AgeBand
    value: Decimal


@dataclass(frozen=True)
class ScheduledChange:
    table: PriceTable
    total: Decimal
    change: Decimal


@dataclass(frozen=True)
class PlanQuote:
    table: PriceTable
    beneficiaries: tuple[BeneficiaryPrice, ...]
    total: Decimal
    scheduled_change: ScheduledChange | None
    source_freshness: SourceFreshness | None
    ans_reference: AnsPlanReference | None


def build_quote(request: QuoteRequest, now: datetime | None = None) -> list[PlanQuote]:
    now = now or timezone.now()
    tables = list(
        with_provenance(filter_quoted_tables(request).filter(validity__contains=request.on_date))
    )
    plans = [table.plan for table in tables]
    next_tables = find_following_tables(request, plans)
    freshness_by_source = {
        freshness.source.id: freshness for freshness in find_sources_with_freshness(now)
    }
    references = find_plan_references(plans)
    quotes = []
    for table in tables:
        beneficiaries = price_beneficiaries(table, request.ages)
        if beneficiaries is None:
            continue
        total = sum((price.value for price in beneficiaries), Decimal("0"))
        quotes.append(
            PlanQuote(
                table=table,
                beneficiaries=beneficiaries,
                total=total,
                scheduled_change=build_scheduled_change(
                    next_tables.get(table.plan_id), request.ages, total
                ),
                source_freshness=freshness_by_source.get(table.batch.document.source_id),
                ans_reference=references.get(table.plan_id),
            )
        )
    return sorted(quotes, key=lambda quote: quote.total)


def filter_quoted_tables(request: QuoteRequest):
    tables = PriceTable.objects.filter(region=request.region, plan__is_active=True)
    tables = tables.known_at(request.known_at) if request.known_at else tables.current()
    if request.plan_ids:
        tables = tables.filter(plan__public_id__in=request.plan_ids)
    if request.operator_id:
        tables = tables.filter(plan__operator__public_id=request.operator_id)
    return tables


def find_following_tables(request: QuoteRequest, plans: list) -> dict[int, PriceTable]:
    following = (
        filter_quoted_tables(request)
        .filter(plan__in=plans, validity__startswith__gt=request.on_date)
        .order_by("plan_id", "validity")
    )
    next_tables: dict[int, PriceTable] = {}
    for table in with_provenance(following):
        next_tables.setdefault(table.plan_id, table)
    return next_tables


def price_beneficiaries(
    table: PriceTable, ages: tuple[int, ...]
) -> tuple[BeneficiaryPrice, ...] | None:
    values = {AgeBand(entry.age_band): entry.value for entry in table.entries.all()}
    prices = []
    for age in ages:
        band = find_band_for_age(age)
        if band not in values:
            return None
        prices.append(BeneficiaryPrice(age=age, age_band=band, value=values[band]))
    return tuple(prices)


def build_scheduled_change(
    table: PriceTable | None, ages: tuple[int, ...], current_total: Decimal
) -> ScheduledChange | None:
    if table is None:
        return None
    beneficiaries = price_beneficiaries(table, ages)
    if beneficiaries is None:
        return None
    total = sum((price.value for price in beneficiaries), Decimal("0"))
    change = total / current_total - 1 if current_total else Decimal("0")
    return ScheduledChange(table=table, total=total, change=change)
