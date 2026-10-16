from apps.core.domain.text import normalize_text


def test_normalize_text_strips_accents_case_and_punctuation():
    assert (
        normalize_text("  Superior — Enfermária (c/ Copart.)  ") == "superior enfermaria c copart"
    )


def test_normalize_text_keeps_digits():
    assert normalize_text("Horizonte 300/Nacional") == "horizonte 300 nacional"


def test_normalize_text_handles_empty_values():
    assert normalize_text("") == ""
    assert normalize_text(None) == ""
