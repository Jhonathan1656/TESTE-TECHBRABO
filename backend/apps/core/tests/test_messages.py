from datetime import date

from apps.core.messages import format_message_param, load_message_catalog, resolve_message


def test_resolve_message_formats_typed_params():
    message = resolve_message(
        "rule.consistency.large_variation",
        {
            "plan": "Essencial Enfermaria",
            "band": 7,
            "change_pct": "31.5",
            "previous_brl": "716.88",
            "value_brl": "942.70",
        },
    )

    assert message == (
        "Essencial Enfermaria, faixa 44–48: variação de +31,50% em relação à tabela vigente "
        "(R$ 716,88 → R$ 942,70)."
    )


def test_resolve_message_returns_key_when_unknown():
    assert resolve_message("missing.key") == "missing.key"


def test_resolve_message_keeps_placeholders_without_params():
    assert "{plan}" in resolve_message("rule.catalog.no_previous_table")


def test_format_message_param_handles_dates_bands_and_missing_values():
    assert format_message_param("effective_from_date", date(2026, 11, 1)) == "01/11/2026"
    assert format_message_param("effective_from_date", "2026-11-01") == "01/11/2026"
    assert format_message_param("bands", [1, 10]) == "0–18, 59+"
    assert format_message_param("median_change_pct", "-2.5") == "-2,50%"
    assert format_message_param("plan", None) == "—"


def test_every_catalog_entry_is_a_non_empty_string():
    catalog = load_message_catalog()

    assert catalog
    assert all(isinstance(text, str) and text.strip() for text in catalog.values())
