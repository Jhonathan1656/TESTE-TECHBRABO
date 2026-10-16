from collections.abc import Iterator
from decimal import Decimal
from itertools import pairwise

from apps.core.domain.age_bands import AgeBand
from apps.core.domain.severity import Severity
from apps.quality.rules.formatting import to_money_param, to_percent_param
from apps.quality.rules.snapshot import BatchSnapshot, Finding

# ANS RN 63/2003, art. 3: (I) last band at most 6x the first; (II) accumulated variation
# from band 7 to 10 not above the one from band 1 to 7 (multiplicative, per STJ Tema 952);
# (III, added by RN 254/2011) no negative variation between consecutive bands.
RN63_MAX_LAST_TO_FIRST_RATIO = Decimal("6")
_RATIO_PRECISION = Decimal("0.01")
_ROUNDING_TOLERANCE = Decimal("0.0001")
NON_SELLABLE_ANS_STATUSES = {"suspended", "cancelled", "transferred"}


def check_rn63_last_band_ratio(batch: BatchSnapshot) -> Iterator[Finding]:
    for plan in batch.plans:
        values = plan.priced_bands()
        first = values.get(AgeBand.BAND_00_18)
        last = values.get(AgeBand.BAND_59_PLUS)
        if not first or not last or first <= 0:
            continue
        if last > first * RN63_MAX_LAST_TO_FIRST_RATIO:
            yield Finding(
                "rn63.last_band_ratio",
                Severity.ERROR,
                plan.label,
                AgeBand.BAND_59_PLUS,
                params={
                    "plan": plan.display_name,
                    "first_brl": to_money_param(first),
                    "last_brl": to_money_param(last),
                    "ratio": str((last / first).quantize(_RATIO_PRECISION)),
                },
            )


def check_rn63_accumulated_variation(batch: BatchSnapshot) -> Iterator[Finding]:
    for plan in batch.plans:
        values = plan.priced_bands()
        first = values.get(AgeBand.BAND_00_18)
        seventh = values.get(AgeBand.BAND_44_48)
        last = values.get(AgeBand.BAND_59_PLUS)
        if not first or not seventh or not last or first <= 0 or seventh <= 0:
            continue
        early_variation = seventh / first - 1
        late_variation = last / seventh - 1
        if late_variation > early_variation + _ROUNDING_TOLERANCE:
            yield Finding(
                "rn63.accumulated_variation",
                Severity.ERROR,
                plan.label,
                AgeBand.BAND_59_PLUS,
                params={
                    "plan": plan.display_name,
                    "early_pct": to_percent_param(early_variation),
                    "late_pct": to_percent_param(late_variation),
                },
            )


def check_rn63_negative_variation(batch: BatchSnapshot) -> Iterator[Finding]:
    for plan in batch.plans:
        ordered = list(plan.priced_bands().items())
        for (previous_band, previous_value), (band, value) in pairwise(ordered):
            if value < previous_value:
                yield Finding(
                    "rn63.negative_variation",
                    Severity.ERROR,
                    plan.label,
                    band,
                    params={
                        "plan": plan.display_name,
                        "band": int(band),
                        "previous_band": int(previous_band),
                        "value_brl": to_money_param(value),
                        "previous_brl": to_money_param(previous_value),
                    },
                )


def check_ans_plan_status(batch: BatchSnapshot) -> Iterator[Finding]:
    for plan in batch.plans:
        if plan.is_matched and plan.ans_status in NON_SELLABLE_ANS_STATUSES:
            yield Finding(
                "ans.plan_not_active",
                Severity.ERROR,
                plan.label,
                params={
                    "plan": plan.display_name,
                    "status": plan.ans_status_label or plan.ans_status,
                    "status_date": plan.ans_status_date.isoformat()
                    if plan.ans_status_date
                    else None,
                },
            )


def check_ans_registered_band(batch: BatchSnapshot) -> Iterator[Finding]:
    for plan in batch.plans:
        for band, value in plan.priced_bands().items():
            registered = plan.registered_bands.get(band)
            if registered is None or registered.min_value <= value <= registered.max_value:
                continue
            yield Finding(
                "ans.outside_registered_band",
                Severity.WARNING,
                plan.label,
                band,
                params={
                    "plan": plan.display_name,
                    "band": int(band),
                    "value_brl": to_money_param(value),
                    "min_brl": to_money_param(registered.min_value),
                    "max_brl": to_money_param(registered.max_value),
                },
            )
