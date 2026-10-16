import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENT = Decimal("0.01")
NO_BREAK_SPACE = "\N{NO-BREAK SPACE}"

_BRAZILIAN_WITH_THOUSANDS = re.compile(r"\d{1,3}(?:\.\d{3})*,\d{1,2}")
_BRAZILIAN_PLAIN = re.compile(r"\d+,\d{1,2}")
_EXPORT_WITH_THOUSANDS = re.compile(r"\d{1,3}(?:,\d{3})*\.\d{1,2}")
_EXPORT_PLAIN = re.compile(r"\d+\.\d{1,2}")
_THOUSANDS_ONLY = re.compile(r"\d{1,3}(?:\.\d{3})+")
_INTEGER = re.compile(r"\d+")


def parse_brl_amount(raw: str | int | float | Decimal | None) -> Decimal | None:
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, Decimal | int | float):
        return _quantize(Decimal(str(raw)))
    text = raw.replace("R$", "").replace(NO_BREAK_SPACE, "").replace(" ", "").strip()
    canonical = _to_canonical_decimal(text)
    if canonical is None:
        return None
    try:
        return _quantize(Decimal(canonical))
    except InvalidOperation:
        return None


def format_brl(value: Decimal) -> str:
    sign = "-" if value < 0 else ""
    grouped = f"{abs(value):,.2f}"
    brazilian = grouped.replace(",", "_").replace(".", ",").replace("_", ".")
    return f"{sign}R$ {brazilian}"


def _to_canonical_decimal(text: str) -> str | None:
    if not text:
        return None
    if _BRAZILIAN_WITH_THOUSANDS.fullmatch(text) or _BRAZILIAN_PLAIN.fullmatch(text):
        return text.replace(".", "").replace(",", ".")
    if _EXPORT_WITH_THOUSANDS.fullmatch(text) or _EXPORT_PLAIN.fullmatch(text):
        return text.replace(",", "")
    if _THOUSANDS_ONLY.fullmatch(text):
        return text.replace(".", "")
    if _INTEGER.fullmatch(text):
        return text
    return None


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)
