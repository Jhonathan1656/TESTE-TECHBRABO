from dataclasses import replace
from datetime import date
from decimal import Decimal

from apps.core.domain.age_bands import AgeBand
from apps.core.domain.money import CENT, format_brl
from apps.quality.rules.snapshot import BatchSnapshot, PlanSnapshot

# A realistic RN 63-compliant price curve (multiples of the first band).
PRICE_CURVE = tuple(
    Decimal(multiplier)
    for multiplier in (
        "1.00",
        "1.19",
        "1.39",
        "1.51",
        "1.63",
        "1.87",
        "2.40",
        "3.11",
        "3.98",
        "5.70",
    )
)
EFFECTIVE_FROM = date(2026, 11, 1)
PREVIOUS_EFFECTIVE_FROM = date(2026, 5, 1)


def build_values(base: str, adjustment: str = "1") -> dict[AgeBand, Decimal]:
    return {
        band: (Decimal(base) * multiplier * Decimal(adjustment)).quantize(CENT)
        for band, multiplier in zip(AgeBand, PRICE_CURVE, strict=True)
    }


def build_plan(
    label: str = "Essencial Enfermaria",
    base: str = "200",
    adjustment: str = "1.098",
    overrides: dict[AgeBand, Decimal | None] | None = None,
    with_history: bool = True,
    plan_id: int = 1,
    **fields,
) -> PlanSnapshot:
    values: dict[AgeBand, Decimal | None] = build_values(base, adjustment)
    values.update(overrides or {})
    defaults = {
        "label": label,
        "plan_id": plan_id,
        "plan_name": label,
        "product_line": label.split()[0],
        "contract_type": "sme",
        "accommodation": "private_room" if "Apartamento" in label else "ward",
        "has_coparticipation": False,
        "values": values,
        "raw_texts": {band: format_brl(value) if value else "?" for band, value in values.items()},
        "previous_values": build_values(base) if with_history else {},
        "current_effective_from": PREVIOUS_EFFECTIVE_FROM if with_history else None,
        "ans_status": "active",
    }
    defaults.update(fields)
    return PlanSnapshot(**defaults)


def build_batch(*plans: PlanSnapshot, **fields) -> BatchSnapshot:
    defaults = {
        "today": EFFECTIVE_FROM,
        "effective_from": EFFECTIVE_FROM,
        "extraction_method": "grid",
        "plans": plans,
    }
    defaults.update(fields)
    return BatchSnapshot(**defaults)


def with_values(plan: PlanSnapshot, overrides: dict[AgeBand, Decimal]) -> PlanSnapshot:
    values = {**plan.values, **overrides}
    raw_texts = {**plan.raw_texts, **{band: format_brl(value) for band, value in overrides.items()}}
    return replace(plan, values=values, raw_texts=raw_texts)
