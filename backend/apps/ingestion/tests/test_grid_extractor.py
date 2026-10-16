from decimal import Decimal

from apps.core.domain.age_bands import AgeBand
from apps.ingestion.extraction.document_content import DocumentContent, build_raw_table
from apps.ingestion.extraction.grid_extractor import AxisOrientation, extract_grid_prices

BAND_LABELS = [
    "00 a 18 anos",
    "19 a 23 anos",
    "24 a 28 anos",
    "29 a 33 anos",
    "34 a 38 anos",
    "39 a 43 anos",
    "44 a 48 anos",
    "49 a 53 anos",
    "54 a 58 anos",
    "59 anos ou mais",
]


def build_content(*tables: list[list[str | None]], page: int | None = 1) -> DocumentContent:
    return DocumentContent(
        text="", tables=tuple(build_raw_table(rows, page=page) for rows in tables)
    )


def find_value(extraction, label: str, band: AgeBand) -> Decimal | None:
    return next(
        cell.value
        for cell in extraction.cells
        if cell.plan_label == label and cell.age_band == band
    )


def test_extracts_bands_in_rows_with_grouped_two_row_header():
    rows = [
        ["Faixa etária", "Essencial", None, "Premium"],
        [None, "Enfermaria", "Apartamento", "Apartamento"],
        *[
            [label, f"{100 + i},00", f"{120 + i},00", f"R$ 1.{200 + i},50"]
            for i, label in enumerate(BAND_LABELS)
        ],
    ]

    extraction = extract_grid_prices(build_content(rows))

    assert extraction.orientations == (AxisOrientation.BANDS_IN_ROWS,)
    labels = {cell.plan_label for cell in extraction.cells}
    assert labels == {"Essencial Enfermaria", "Essencial Apartamento", "Premium Apartamento"}
    assert len(extraction.cells) == 30
    assert find_value(extraction, "Premium Apartamento", AgeBand.BAND_59_PLUS) == Decimal("1209.50")
    first = extraction.cells[0]
    assert first.location == {
        "page": 1,
        "cell": "L3C2",
        "band_text": "00 a 18 anos",
        "plan_text": "Essencial Enfermaria",
    }


def test_title_lines_above_the_header_are_not_part_of_labels():
    rows = [
        ["Tabela PME - valores em R$", None, None],
        [None, None, None],
        ["Idade", "Superior Enf.", "Superior Apto."],
        *[[label, "300,00", "350,00"] for label in BAND_LABELS],
    ]

    extraction = extract_grid_prices(build_content(rows))

    assert {cell.plan_label for cell in extraction.cells} == {"Superior Enf.", "Superior Apto."}


def test_extracts_bands_in_columns_joining_label_columns():
    rows = [
        ["Plano", "Acomodação", *BAND_LABELS],
        ["Horizonte 100", "Enfermaria", *[f"{189 + i}.50" for i in range(10)]],
        ["Horizonte 200", "Apartamento", *[f"{241 + i}.30" for i in range(10)]],
        ["Valores mensais por beneficiário", None, *[None] * 10],
    ]

    extraction = extract_grid_prices(build_content(rows, page=None))

    assert extraction.orientations == (AxisOrientation.BANDS_IN_COLUMNS,)
    assert {cell.plan_label for cell in extraction.cells} == {
        "Horizonte 100 Enfermaria",
        "Horizonte 200 Apartamento",
    }
    assert find_value(extraction, "Horizonte 200 Apartamento", AgeBand.BAND_00_18) == Decimal(
        "241.30"
    )


def test_extracts_long_format_exports():
    rows = [["Plano", "Faixa", "Valor", "Vigência"]]
    for plan in ("Litoral Essencial", "Litoral Básico"):
        rows.extend(
            [plan, label, f"{150 + i},90", "01/11/2026"] for i, label in enumerate(BAND_LABELS)
        )

    extraction = extract_grid_prices(build_content(rows))

    assert extraction.orientations == (AxisOrientation.LONG_FORMAT,)
    assert len(extraction.cells) == 20
    assert find_value(extraction, "Litoral Básico", AgeBand.BAND_24_28) == Decimal("152.90")


def test_ignores_tables_without_age_band_axis():
    rows = [["Plano", "Registro ANS"], ["Essencial", "990.101/24-1"]]

    extraction = extract_grid_prices(build_content(rows))

    assert extraction.cells == ()
    assert extraction.orientations == ()


def test_keeps_first_table_and_counts_conflicting_duplicates():
    first = [["Faixa", "Essencial"], *[[label, "100,00"] for label in BAND_LABELS]]
    second = [["Faixa", "Essencial"], *[[label, "110,00"] for label in BAND_LABELS]]

    extraction = extract_grid_prices(build_content(first, second))

    assert len(extraction.cells) == 10
    assert extraction.conflicting_duplicates == 10
    assert find_value(extraction, "Essencial", AgeBand.BAND_00_18) == Decimal("100.00")


def test_unparseable_values_are_kept_for_review():
    rows = [["Faixa", "Essencial"], *[[label, "100,00"] for label in BAND_LABELS]]
    rows[5][1] = "1OO,OO"

    extraction = extract_grid_prices(build_content(rows))

    broken = next(cell for cell in extraction.cells if cell.age_band == AgeBand.BAND_34_38)
    assert broken.value is None
    assert broken.raw_text == "1OO,OO"
