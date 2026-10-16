from decimal import ROUND_HALF_UP, Decimal

_TWO_PLACES = Decimal("0.01")


def to_money_param(value: Decimal) -> str:
    return str(value.quantize(_TWO_PLACES, rounding=ROUND_HALF_UP))


def to_percent_param(ratio: Decimal) -> str:
    return str((ratio * 100).quantize(_TWO_PLACES, rounding=ROUND_HALF_UP))


def calculate_change(value: Decimal, previous: Decimal) -> Decimal:
    return value / previous - 1
