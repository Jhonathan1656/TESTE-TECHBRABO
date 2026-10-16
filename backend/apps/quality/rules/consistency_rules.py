import statistics
from collections.abc import Iterator
from decimal import Decimal

from apps.core.domain.age_bands import AgeBand
from apps.core.domain.severity import Severity
from apps.quality.rules.formatting import calculate_change, to_money_param, to_percent_param
from apps.quality.rules.snapshot import BatchSnapshot, Finding, PlanSnapshot

_POWERS_OF_TEN = (10, 100, 1000)
# Adjacent age bands rarely differ by more than ~60%; a 6x gap only happens with a shifted comma.
_NEIGHBOR_SHIFT_RATIO = Decimal("6")
_MIN_BANDS_FOR_UNIFORMITY = 4
_WARD = "ward"
_PRIVATE_ROOM = "private_room"


def find_decimal_shift_factor(
    plan: PlanSnapshot, band: AgeBand, tolerance: Decimal
) -> tuple[str, Decimal] | None:
    """Returns (factor label, reference value) when the value looks like a misplaced comma."""
    value = plan.priced_bands().get(band)
    if value is None or value <= 0:
        return None
    previous = plan.previous_values.get(band)
    if previous:
        return _match_power_of_ten(value, previous, tolerance)
    neighbors = [
        plan.priced_bands()[neighbor]
        for neighbor in _neighbor_bands(band)
        if neighbor in plan.priced_bands()
    ]
    if not neighbors:
        return None
    reference = Decimal(statistics.median(neighbors))
    ratio = value / reference
    if ratio >= _NEIGHBOR_SHIFT_RATIO or ratio <= 1 / _NEIGHBOR_SHIFT_RATIO:
        return _nearest_power_label(ratio), reference
    return None


def check_decimal_shift(batch: BatchSnapshot) -> Iterator[Finding]:
    tolerance = batch.thresholds.decimal_shift_tolerance
    for plan in batch.plans:
        for band, value in plan.priced_bands().items():
            shift = find_decimal_shift_factor(plan, band, tolerance)
            if shift is None:
                continue
            factor, reference = shift
            yield Finding(
                "consistency.decimal_shift",
                Severity.ERROR,
                plan.label,
                band,
                params={
                    "plan": plan.display_name,
                    "band": int(band),
                    "value_brl": to_money_param(value),
                    "reference_brl": to_money_param(reference),
                    "factor": factor,
                },
            )


def check_large_variation(batch: BatchSnapshot) -> Iterator[Finding]:
    limit = batch.thresholds.large_variation_pct / 100
    for plan in batch.plans:
        changes = calculate_band_changes(plan, batch)
        large = {band: change for band, change in changes.items() if abs(change) > limit}
        if not large:
            continue
        if len(changes) >= _MIN_BANDS_FOR_UNIFORMITY and len(large) == len(changes):
            yield Finding(
                "consistency.large_adjustment",
                Severity.WARNING,
                plan.label,
                params={
                    "plan": plan.display_name,
                    "change_pct": to_percent_param(Decimal(statistics.median(changes.values()))),
                    "limit_pct": str(batch.thresholds.large_variation_pct),
                },
            )
            continue
        for band, change in large.items():
            yield Finding(
                "consistency.large_variation",
                Severity.WARNING,
                plan.label,
                band,
                params={
                    "plan": plan.display_name,
                    "band": int(band),
                    "change_pct": to_percent_param(change),
                    "previous_brl": to_money_param(plan.previous_values[band]),
                    "value_brl": to_money_param(plan.priced_bands()[band]),
                },
            )


def check_non_uniform_adjustment(batch: BatchSnapshot) -> Iterator[Finding]:
    """Operators reajust every band by the same percentage; an outlier band is usually a typo."""
    tolerance = batch.thresholds.non_uniform_tolerance_pp / 100
    for plan in batch.plans:
        changes = calculate_band_changes(plan, batch)
        if len(changes) < _MIN_BANDS_FOR_UNIFORMITY:
            continue
        median_change = Decimal(statistics.median(changes.values()))
        outliers = {
            band: change
            for band, change in changes.items()
            if abs(change - median_change) > tolerance
        }
        if not outliers:
            continue
        if len(outliers) > len(changes) / 2:
            yield Finding(
                "consistency.non_uniform_plan",
                Severity.WARNING,
                plan.label,
                params={
                    "plan": plan.display_name,
                    "min_change_pct": to_percent_param(min(changes.values())),
                    "max_change_pct": to_percent_param(max(changes.values())),
                },
            )
            continue
        for band, change in outliers.items():
            yield Finding(
                "consistency.non_uniform_adjustment",
                Severity.WARNING,
                plan.label,
                band,
                params={
                    "plan": plan.display_name,
                    "band": int(band),
                    "change_pct": to_percent_param(change),
                    "median_change_pct": to_percent_param(median_change),
                },
            )


def check_expected_price_order(batch: BatchSnapshot) -> Iterator[Finding]:
    for cheaper, pricier in find_expected_order_pairs(batch.plans):
        cheaper_values, pricier_values = cheaper.priced_bands(), pricier.priced_bands()
        inverted = [
            int(band)
            for band in AgeBand
            if band in cheaper_values
            and band in pricier_values
            and cheaper_values[band] > pricier_values[band]
        ]
        if inverted:
            yield Finding(
                "consistency.expected_price_order",
                Severity.WARNING,
                cheaper.label,
                discriminator=pricier.label,
                params={
                    "cheaper_plan": cheaper.display_name,
                    "pricier_plan": pricier.display_name,
                    "bands": inverted,
                },
            )


def find_expected_order_pairs(
    plans: tuple[PlanSnapshot, ...],
) -> list[tuple[PlanSnapshot, PlanSnapshot]]:
    """Pairs (expected cheaper, expected pricier) within the same product line."""
    matched = [plan for plan in plans if plan.is_matched and plan.product_line]
    pairs = []
    for cheaper in matched:
        for pricier in matched:
            if cheaper is pricier or not _share_product_line(cheaper, pricier):
                continue
            ward_versus_room = (
                cheaper.has_coparticipation == pricier.has_coparticipation
                and cheaper.accommodation == _WARD
                and pricier.accommodation == _PRIVATE_ROOM
            )
            copay_versus_full = (
                cheaper.accommodation == pricier.accommodation
                and cheaper.has_coparticipation
                and not pricier.has_coparticipation
            )
            if ward_versus_room or copay_versus_full:
                pairs.append((cheaper, pricier))
    return pairs


def calculate_band_changes(plan: PlanSnapshot, batch: BatchSnapshot) -> dict[AgeBand, Decimal]:
    """Change against the previous table, leaving out bands already flagged as decimal shifts."""
    tolerance = batch.thresholds.decimal_shift_tolerance
    changes = {}
    for band, value in plan.priced_bands().items():
        previous = plan.previous_values.get(band)
        if not previous or find_decimal_shift_factor(plan, band, tolerance):
            continue
        changes[band] = calculate_change(value, previous)
    return changes


def _share_product_line(left: PlanSnapshot, right: PlanSnapshot) -> bool:
    return left.product_line == right.product_line and left.contract_type == right.contract_type


def _match_power_of_ten(
    value: Decimal, reference: Decimal, tolerance: Decimal
) -> tuple[str, Decimal] | None:
    ratio = value / reference
    for power in _POWERS_OF_TEN:
        if abs(ratio - power) / power <= tolerance:
            return str(power), reference
        inverse = Decimal(1) / power
        if abs(ratio - inverse) / inverse <= tolerance:
            return f"1/{power}", reference
    return None


def _nearest_power_label(ratio: Decimal) -> str:
    if ratio >= 1:
        power = min(_POWERS_OF_TEN, key=lambda candidate: abs(ratio - candidate))
        return str(power)
    power = min(_POWERS_OF_TEN, key=lambda candidate: abs(ratio - Decimal(1) / candidate))
    return f"1/{power}"


def _neighbor_bands(band: AgeBand) -> list[AgeBand]:
    return [AgeBand(position) for position in (band - 1, band + 1) if 1 <= position <= 10]
