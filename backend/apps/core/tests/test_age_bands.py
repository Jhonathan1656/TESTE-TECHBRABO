import pytest

from apps.core.domain.age_bands import AgeBand, find_band_for_age, parse_age_band


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("00 a 18 anos", AgeBand.BAND_00_18),
        ("0 a 18", AgeBand.BAND_00_18),
        ("00-18", AgeBand.BAND_00_18),
        ("Até 18 anos", AgeBand.BAND_00_18),
        ("19 a 23 anos", AgeBand.BAND_19_23),
        ("19 – 23", AgeBand.BAND_19_23),
        ("de 44 a 48 anos", AgeBand.BAND_44_48),
        ("54-58", AgeBand.BAND_54_58),
        ("59 anos ou mais", AgeBand.BAND_59_PLUS),
        ("59+", AgeBand.BAND_59_PLUS),
        ("Acima de 59 anos", AgeBand.BAND_59_PLUS),
        ("a partir de 59", AgeBand.BAND_59_PLUS),
    ],
)
def test_parse_age_band_recognizes_common_document_labels(text, expected):
    assert parse_age_band(text) == expected


@pytest.mark.parametrize(
    "text",
    ["", "R$ 19,23", "19,23", "1.023,45", "Horizonte 300", "Essencial 18", "59", "20 a 25", "2026"],
)
def test_parse_age_band_rejects_values_and_unrelated_text(text):
    assert parse_age_band(text) is None


@pytest.mark.parametrize(
    ("age", "expected"),
    [
        (0, AgeBand.BAND_00_18),
        (18, AgeBand.BAND_00_18),
        (19, AgeBand.BAND_19_23),
        (48, AgeBand.BAND_44_48),
        (58, AgeBand.BAND_54_58),
        (59, AgeBand.BAND_59_PLUS),
        (102, AgeBand.BAND_59_PLUS),
    ],
)
def test_find_band_for_age_maps_to_rn63_bands(age, expected):
    assert find_band_for_age(age) == expected


def test_find_band_for_age_rejects_negative_age():
    with pytest.raises(ValueError):
        find_band_for_age(-1)


def test_band_labels_are_compact_ranges():
    assert AgeBand.BAND_00_18.label == "0–18"
    assert AgeBand.BAND_59_PLUS.label == "59+"
