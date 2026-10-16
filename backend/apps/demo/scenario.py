import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from functools import cache
from pathlib import Path

from apps.core.domain.age_bands import AgeBand
from apps.core.domain.money import CENT, format_brl
from apps.demo.documents.renderers import (
    GridColumn,
    GridColumnGroup,
    NoticeDocument,
    NoticeSection,
    PriceGridDocument,
    PriceRow,
    PriceRowsWorkbook,
    render_notice_pdf,
    render_price_grid_pdf,
    render_price_rows_xlsx,
)

SCENARIO_PATH = Path(__file__).parent / "data" / "demo_scenario.json"
HISTORY_STAGE = "history"
DEMO_STAGE = "demo"
_BANDS_PER_NOTICE_LINE = 5
_MONTHS_PER_YEAR = 12


@dataclass(frozen=True)
class GeneratedFile:
    name: str
    content: bytes


@cache
def load_scenario() -> dict:
    return json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))


def list_deliveries(stage: str) -> list[dict]:
    return [delivery for delivery in load_scenario()["deliveries"] if delivery["stage"] == stage]


def find_delivery(key: str) -> dict | None:
    return next(
        (delivery for delivery in load_scenario()["deliveries"] if delivery["key"] == key), None
    )


def find_operator_spec(operator_key: str) -> dict:
    return next(spec for spec in load_scenario()["operators"] if spec["key"] == operator_key)


def find_plan_spec(operator_key: str, plan_key: str) -> dict:
    return next(
        plan for plan in find_operator_spec(operator_key)["plans"] if plan["key"] == plan_key
    )


def calculate_effective_from(delivery: dict, today: date) -> date:
    month_index = (
        today.year * _MONTHS_PER_YEAR + today.month - 1 + delivery["effective_month_offset"]
    )
    return date(month_index // _MONTHS_PER_YEAR, month_index % _MONTHS_PER_YEAR + 1, 1)


def calculate_price(base_price: str, band: AgeBand, adjustment: str) -> Decimal:
    multiplier = Decimal(load_scenario()["price_curve"][band - 1])
    return (Decimal(base_price) * multiplier * Decimal(adjustment)).quantize(CENT)


def build_delivery_filename(delivery: dict, today: date) -> str:
    return delivery["filename"].format(effective=calculate_effective_from(delivery, today))


def build_delivery_file(delivery: dict, today: date) -> GeneratedFile:
    effective_from = calculate_effective_from(delivery, today)
    builders = {
        "pdf_grid": build_grid_pdf,
        "xlsx_rows": build_rows_xlsx,
        "pdf_notice": build_notice_pdf,
    }
    content = builders[delivery["layout"]](delivery, effective_from)
    return GeneratedFile(build_delivery_filename(delivery, today), content)


def build_grid_pdf(delivery: dict, effective_from: date) -> bytes:
    scenario = load_scenario()
    labels = scenario["document_labels"]
    typos = {(typo["plan"], typo["band"]): typo["text"] for typo in delivery.get("typos", [])}
    groups = tuple(
        GridColumnGroup(
            title=group["title"],
            columns=tuple(
                build_grid_column(delivery, column, typos) for column in group["columns"]
            ),
        )
        for group in delivery["column_groups"]
    )
    return render_price_grid_pdf(
        PriceGridDocument(
            heading=delivery["heading"],
            info_lines=build_info_lines(delivery, effective_from),
            band_header=labels["band_header"],
            band_labels=tuple(scenario["band_labels"]),
            groups=groups,
            footer=tuple(delivery["footer"]),
        )
    )


def build_grid_column(
    delivery: dict, column: dict, typos: dict[tuple[str, int], str]
) -> GridColumn:
    base_price = find_plan_spec(delivery["operator"], column["plan"])["base_price"]
    values = tuple(
        typos.get((column["plan"], int(band)))
        or format_document_money(
            calculate_price(base_price, band, delivery["adjustment"]), delivery["money_style"]
        )
        for band in AgeBand
    )
    return GridColumn(label=column["label"], values=values)


def build_rows_xlsx(delivery: dict, effective_from: date) -> bytes:
    scenario = load_scenario()
    labels = scenario["document_labels"]
    typos = {
        (typo["plan"], typo["band"]): Decimal(typo["value"]) for typo in delivery.get("typos", [])
    }
    rows = []
    for row in delivery["rows"]:
        base_price = (
            row.get("base_price") or find_plan_spec(delivery["operator"], row["plan"])["base_price"]
        )
        values = tuple(
            typos.get(
                (row["plan"], int(band)), calculate_price(base_price, band, delivery["adjustment"])
            )
            for band in AgeBand
        )
        rows.append(PriceRow(name=row["name"], accommodation=row["accommodation"], values=values))
    workbook = PriceRowsWorkbook(
        heading=delivery["heading"],
        info_lines=build_info_lines(delivery, effective_from),
        header=(labels["plan_header"], labels["accommodation_header"], *scenario["band_labels"]),
        rows=tuple(rows),
        footer=tuple(delivery["footer"]),
        sheet_title=labels["sheet_title"],
    )
    created_at = datetime.combine(effective_from - timedelta(days=7), time(9, 0))
    return render_price_rows_xlsx(workbook, created_at)


def build_notice_pdf(delivery: dict, effective_from: date) -> bytes:
    scenario = load_scenario()
    labels = scenario["document_labels"]
    sections = []
    adjustment = delivery["adjustment"]
    for plan_key in delivery["plans"]:
        plan = find_plan_spec(delivery["operator"], plan_key)
        prices = [
            f"{label}: {format_brl(calculate_price(plan['base_price'], band, adjustment))}"
            for band, label in zip(AgeBand, scenario["band_labels"], strict=True)
        ]
        lines = tuple(
            " · ".join(prices[start : start + _BANDS_PER_NOTICE_LINE])
            for start in range(0, len(prices), _BANDS_PER_NOTICE_LINE)
        )
        sections.append(NoticeSection(title=plan["name"], lines=lines))
    return render_notice_pdf(
        NoticeDocument(
            heading=delivery["heading"],
            title=delivery["title"],
            paragraphs=(
                delivery["intro"].format(effective_from=effective_from.strftime("%d/%m/%Y")),
                f"{labels['region']}: {delivery['region']}",
            ),
            sections=tuple(sections),
            footer=tuple(delivery["footer"]),
        )
    )


def build_info_lines(delivery: dict, effective_from: date) -> tuple[str, ...]:
    labels = load_scenario()["document_labels"]
    return (
        delivery["title"],
        f"{labels['region']}: {delivery['region']}",
        f"{labels['effective_from']}: {effective_from.strftime('%d/%m/%Y')}",
    )


def format_document_money(value: Decimal, style: str) -> str:
    formatted = format_brl(value)
    return formatted if style == "brl" else formatted.removeprefix("R$ ")
