from decimal import Decimal

import pytest

from apps.core.domain.money import format_brl, parse_brl_amount


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("R$ 1.234,56", Decimal("1234.56")),
        ("1.234,56", Decimal("1234.56")),
        ("234,5", Decimal("234.50")),
        ("R$\N{NO-BREAK SPACE}312,45", Decimal("312.45")),
        ("12.345.678,90", Decimal("12345678.90")),
        ("1234.56", Decimal("1234.56")),
        ("1,234.56", Decimal("1234.56")),
        ("1.234", Decimal("1234.00")),
        ("850", Decimal("850.00")),
        (Decimal("99.999"), Decimal("100.00")),
        (1084.9, Decimal("1084.90")),
        (312, Decimal("312.00")),
    ],
)
def test_parse_brl_amount_handles_brazilian_and_export_formats(raw, expected):
    assert parse_brl_amount(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "R$", "abc", "12,3,4", "--", "1.23.4"])
def test_parse_brl_amount_returns_none_for_unparseable_text(raw):
    assert parse_brl_amount(raw) is None


def test_format_brl_uses_brazilian_separators():
    assert format_brl(Decimal("1234.5")) == "R$ 1.234,50"
    assert format_brl(Decimal("0.99")) == "R$ 0,99"
    assert format_brl(Decimal("-10")) == "-R$ 10,00"
