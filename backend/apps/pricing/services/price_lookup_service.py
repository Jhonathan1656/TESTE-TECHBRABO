from collections.abc import Iterable
from datetime import date, datetime, timedelta
from enum import StrEnum

from django.db.models import QuerySet

from apps.pricing.models import PriceTable


class TableState(StrEnum):
    CURRENT = "current"
    SCHEDULED = "scheduled"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"


def classify_table_state(table: PriceTable, today: date) -> TableState:
    if table.superseded_at is not None:
        return TableState.SUPERSEDED
    if table.validity.lower > today:
        return TableState.SCHEDULED
    if table.validity.upper is not None and table.validity.upper <= today:
        return TableState.EXPIRED
    return TableState.CURRENT


def find_effective_until(table: PriceTable) -> date | None:
    """Validity ranges are stored half-open; documents state the last valid day."""
    return table.validity.upper - timedelta(days=1) if table.validity.upper else None


_PROVENANCE_RELATIONS = (
    "plan__operator",
    "batch__document__source",
    "batch__document__uploaded_by",
    "batch__reviewed_by",
)


def with_provenance(tables: QuerySet) -> QuerySet:
    return tables.select_related(*_PROVENANCE_RELATIONS).prefetch_related("entries")


def find_table_valid_on(
    plan, region: str, on_date: date, known_at: datetime | None = None
) -> PriceTable | None:
    tables = PriceTable.objects.filter(plan=plan, region=region, validity__contains=on_date)
    tables = tables.known_at(known_at) if known_at else tables.current()
    return with_provenance(tables).order_by("-recorded_at").first()


def find_tables_valid_on(plans: Iterable, region: str, on_date: date) -> dict[int, PriceTable]:
    tables = PriceTable.objects.current().filter(
        plan__in=list(plans), region=region, validity__contains=on_date
    )
    return {table.plan_id: table for table in with_provenance(tables)}


def find_next_tables(plans: Iterable, region: str, after_date: date) -> dict[int, PriceTable]:
    tables = (
        PriceTable.objects.current()
        .filter(plan__in=list(plans), region=region, validity__startswith__gt=after_date)
        .order_by("plan_id", "validity")
    )
    next_tables: dict[int, PriceTable] = {}
    for table in with_provenance(tables):
        next_tables.setdefault(table.plan_id, table)
    return next_tables


def find_latest_effective_starts(plans: Iterable, region: str) -> dict[int, date]:
    starts: dict[int, date] = {}
    tables = PriceTable.objects.current().filter(plan__in=list(plans), region=region)
    for plan_id, validity in tables.values_list("plan_id", "validity"):
        if plan_id not in starts or validity.lower > starts[plan_id]:
            starts[plan_id] = validity.lower
    return starts


def find_operator_tables_valid_on(operator, region: str, on_date: date) -> list[PriceTable]:
    tables = PriceTable.objects.current().filter(
        plan__operator=operator, plan__is_active=True, region=region, validity__contains=on_date
    )
    return list(tables.select_related("plan"))


def list_plan_history(plan) -> list[PriceTable]:
    tables = PriceTable.objects.filter(plan=plan).order_by("region", "validity", "recorded_at")
    return list(with_provenance(tables).select_related("superseded_by", "derived_from"))


def list_pricing_regions() -> list[str]:
    return list(
        PriceTable.objects.current().values_list("region", flat=True).distinct().order_by("region")
    )
