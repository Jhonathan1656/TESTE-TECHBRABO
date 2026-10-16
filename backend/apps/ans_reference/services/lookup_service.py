from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum

from django.db.models import Q

from apps.ans_reference.models import AnsPlanRecord, AnsPriceBandRecord
from apps.core.domain.age_bands import AgeBand
from apps.core.domain.text import normalize_text


class AnsPlanStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    TRANSFERRED = "transferred"
    UNKNOWN = "unknown"


# Status labels as published by ANS in the plan characteristics and network datasets.
_STATUS_BY_LABEL = {
    "ativo": AnsPlanStatus.ACTIVE,
    "suspenso": AnsPlanStatus.SUSPENDED,
    "ativo com comercializacao suspensa": AnsPlanStatus.SUSPENDED,
    "cancelado": AnsPlanStatus.CANCELLED,
    "transferido": AnsPlanStatus.TRANSFERRED,
}


@dataclass(frozen=True)
class RegisteredPriceBand:
    commercial_value: Decimal
    min_value: Decimal
    max_value: Decimal


@dataclass(frozen=True)
class AnsPlanReference:
    ans_plan_id: int
    status: AnsPlanStatus
    status_label: str
    status_date: date | None
    note_code: int | None = None
    note_registered_at: date | None = None
    price_bands: dict[AgeBand, RegisteredPriceBand] = field(default_factory=dict)

    @property
    def is_sellable(self) -> bool:
        return self.status == AnsPlanStatus.ACTIVE


def map_plan_status(label: str) -> AnsPlanStatus:
    return _STATUS_BY_LABEL.get(normalize_text(label), AnsPlanStatus.UNKNOWN)


def find_plan_references(plans: Iterable) -> dict[int, AnsPlanReference]:
    """Returns the ANS registration data for each catalog plan, keyed by plan id."""
    keyed_plans = {
        (plan.operator.ans_registration, plan.ans_product_code): plan
        for plan in plans
        if plan.ans_product_code
    }
    if not keyed_plans:
        return {}
    records = list(AnsPlanRecord.objects.filter(_build_plan_filter(keyed_plans.keys())))
    bands_by_ans_plan = find_latest_price_bands(record.ans_plan_id for record in records)
    references = {}
    for record in records:
        plan = keyed_plans.get((record.operator_registration, record.product_code))
        if plan is None:
            continue
        note_code, registered_at, bands = bands_by_ans_plan.get(
            record.ans_plan_id, (None, None, {})
        )
        references[plan.id] = AnsPlanReference(
            ans_plan_id=record.ans_plan_id,
            status=map_plan_status(record.status),
            status_label=record.status,
            status_date=record.status_date,
            note_code=note_code,
            note_registered_at=registered_at,
            price_bands=bands,
        )
    return references


def find_latest_price_bands(
    ans_plan_ids: Iterable[int],
) -> dict[int, tuple[int, date, dict[AgeBand, RegisteredPriceBand]]]:
    rows = AnsPriceBandRecord.objects.filter(ans_plan_id__in=list(ans_plan_ids)).order_by(
        "ans_plan_id", "-note_registered_at", "-note_code", "age_band"
    )
    latest: dict[int, tuple[int, date, dict[AgeBand, RegisteredPriceBand]]] = {}
    for row in rows:
        note_code, _registered_at, bands = latest.setdefault(
            row.ans_plan_id, (row.note_code, row.note_registered_at, {})
        )
        if row.note_code == note_code:
            bands[AgeBand(row.age_band)] = RegisteredPriceBand(
                commercial_value=row.commercial_value,
                min_value=row.min_value,
                max_value=row.max_value,
            )
    return latest


def _build_plan_filter(keys: Iterable[tuple[str, str]]) -> Q:
    condition = Q()
    for registration, product_code in keys:
        condition |= Q(operator_registration=registration, product_code=product_code)
    return condition
