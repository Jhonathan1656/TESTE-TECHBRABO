import json
from collections.abc import Mapping
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from functools import cache
from pathlib import Path

from apps.core.domain.age_bands import AgeBand
from apps.core.domain.money import format_brl

_CATALOG_PATH = Path(__file__).with_name("pt_BR.json")
_MISSING_VALUE = "—"


@cache
def load_message_catalog() -> dict[str, str]:
    return json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))


def resolve_message(key: str, params: Mapping[str, object] | None = None) -> str:
    template = load_message_catalog().get(key)
    if template is None:
        return key
    formatted = {name: format_message_param(name, value) for name, value in (params or {}).items()}
    return template.format_map(_KeepUnknownPlaceholders(formatted))


def format_message_param(name: str, value: object) -> str:
    if value is None or value == "":
        return _MISSING_VALUE
    kind = name.rsplit("_", 1)[-1]
    if kind == "brl":
        return format_brl(Decimal(str(value)))
    if kind == "pct":
        return format_percent(Decimal(str(value)), signed="change" in name)
    if kind == "date":
        return format_date(value)
    if kind == "band":
        return AgeBand(int(value)).label
    if kind == "bands":
        return ", ".join(AgeBand(int(band)).label for band in value)
    if kind == "ratio":
        return format_decimal(Decimal(str(value)))
    return str(value)


def format_percent(value: Decimal, signed: bool = False) -> str:
    text = format_decimal(abs(value))
    if signed and value > 0:
        return f"+{text}%"
    if value < 0:
        return f"-{text}%"
    return f"{text}%"


def format_decimal(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)).replace(".", ",")


def format_date(value: object) -> str:
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, str):
        value = date.fromisoformat(value[:10])
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    return str(value)


class _KeepUnknownPlaceholders(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"
