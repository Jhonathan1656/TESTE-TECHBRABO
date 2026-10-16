import re
from dataclasses import dataclass
from enum import StrEnum

from apps.core.domain.age_bands import AgeBand, parse_age_band
from apps.core.domain.money import parse_brl_amount
from apps.ingestion.extraction.document_content import DocumentContent, RawTable, TableCell
from apps.ingestion.extraction.results import ExtractedCell

MIN_DISTINCT_BANDS = 8
MAX_HEADER_ROWS = 3
MIN_COLUMN_SHARE = 0.8
_DATE_LIKE = re.compile(r"^\d{2}/\d{2}/\d{4}$")


class AxisOrientation(StrEnum):
    BANDS_IN_ROWS = "bands_in_rows"
    BANDS_IN_COLUMNS = "bands_in_columns"
    LONG_FORMAT = "long_format"


@dataclass(frozen=True)
class BandAxis:
    orientation: AxisOrientation
    index: int
    positions: dict[int, AgeBand]


@dataclass(frozen=True)
class GridExtraction:
    cells: tuple[ExtractedCell, ...]
    orientations: tuple[str, ...]
    conflicting_duplicates: int


def extract_grid_prices(content: DocumentContent) -> GridExtraction:
    cells: list[ExtractedCell] = []
    orientations: list[str] = []
    for table in content.tables:
        grid = pad_grid(table)
        axis = find_band_axis(grid)
        if axis is None:
            continue
        table_cells = EXTRACTORS[axis.orientation](grid, axis, table)
        if table_cells:
            cells.extend(table_cells)
            orientations.append(axis.orientation.value)
    unique_cells, conflicts = keep_first_cell_per_band(cells)
    return GridExtraction(tuple(unique_cells), tuple(orientations), conflicts)


def pad_grid(table: RawTable) -> list[list[TableCell]]:
    width = max((len(row) for row in table.rows), default=0)
    return [list(row) + [TableCell(text="")] * (width - len(row)) for row in table.rows]


def find_band_axis(grid: list[list[TableCell]]) -> BandAxis | None:
    height = len(grid)
    width = len(grid[0]) if grid else 0
    candidates: list[BandAxis] = []
    for column in range(width):
        positions = _find_band_positions(grid[row][column] for row in range(height))
        distinct = len(set(positions.values()))
        if distinct >= MIN_DISTINCT_BANDS:
            orientation = (
                AxisOrientation.BANDS_IN_ROWS
                if distinct == len(positions)
                else AxisOrientation.LONG_FORMAT
            )
            candidates.append(BandAxis(orientation, column, positions))
    for row in range(height):
        positions = _find_band_positions(grid[row])
        distinct = len(set(positions.values()))
        if distinct >= MIN_DISTINCT_BANDS and distinct == len(positions):
            candidates.append(BandAxis(AxisOrientation.BANDS_IN_COLUMNS, row, positions))
    if not candidates:
        return None
    return max(candidates, key=lambda axis: len(set(axis.positions.values())))


def extract_bands_in_rows(grid, axis: BandAxis, table: RawTable) -> list[ExtractedCell]:
    band_column = axis.index
    header_rows = find_header_rows(grid, min(axis.positions), band_column)
    cells: list[ExtractedCell] = []
    for column, label in build_column_labels(grid, header_rows, band_column).items():
        column_cells = [
            build_cell(label, band, grid[row][column], table, band_text=grid[row][band_column].text)
            for row, band in sorted(axis.positions.items())
        ]
        cells.extend(_keep_priced_line(column_cells))
    return cells


def extract_bands_in_columns(grid, axis: BandAxis, table: RawTable) -> list[ExtractedCell]:
    band_row = axis.index
    label_columns = range(min(axis.positions))
    cells: list[ExtractedCell] = []
    for row in range(band_row + 1, len(grid)):
        label = " ".join(
            grid[row][column].text for column in label_columns if grid[row][column].text
        )
        if not label:
            continue
        row_cells = [
            build_cell(label, band, grid[row][column], table, band_text=grid[band_row][column].text)
            for column, band in sorted(axis.positions.items())
        ]
        cells.extend(_keep_priced_line(row_cells))
    return cells


def extract_long_format(grid, axis: BandAxis, table: RawTable) -> list[ExtractedCell]:
    band_column = axis.index
    band_rows = sorted(axis.positions)
    value_column = find_value_column(grid, band_rows, excluded={band_column})
    if value_column is None:
        return []
    label_columns = [
        column
        for column in range(len(grid[0]))
        if column not in (band_column, value_column) and _is_label_column(grid, band_rows, column)
    ]
    cells: list[ExtractedCell] = []
    for row in band_rows:
        label = " ".join(
            grid[row][column].text for column in label_columns if grid[row][column].text
        )
        cell = build_cell(
            label, axis.positions[row], grid[row][value_column], table, grid[row][band_column].text
        )
        if label and cell is not None:
            cells.append(cell)
    return cells


EXTRACTORS = {
    AxisOrientation.BANDS_IN_ROWS: extract_bands_in_rows,
    AxisOrientation.BANDS_IN_COLUMNS: extract_bands_in_columns,
    AxisOrientation.LONG_FORMAT: extract_long_format,
}


def find_header_rows(grid, first_band_row: int, band_column: int) -> list[int]:
    header_rows: list[int] = []
    for row in range(first_band_row - 1, -1, -1):
        filled = [
            column for column, cell in enumerate(grid[row]) if column != band_column and cell.text
        ]
        if not filled:
            break
        # A single filled cell above the header block is a title, not a grouped header.
        if header_rows and len(filled) < 2:
            break
        header_rows.insert(0, row)
        if len(header_rows) == MAX_HEADER_ROWS:
            break
    return header_rows


def build_column_labels(grid, header_rows: list[int], band_column: int) -> dict[int, str]:
    labels: dict[int, str] = {}
    for column in range(len(grid[0]) if grid else 0):
        if column == band_column:
            continue
        parts: list[str] = []
        for position, row in enumerate(header_rows):
            is_group_row = position < len(header_rows) - 1
            text = grid[row][column].text
            if not text and is_group_row:
                text = inherit_group_text(grid[row], column, band_column)
            if text and text not in parts:
                parts.append(text)
        if parts:
            labels[column] = " ".join(parts)
    return labels


def inherit_group_text(row_cells: list[TableCell], column: int, band_column: int) -> str:
    # Merged header cells come back empty; they belong to the nearest filled cell on the left.
    for left in range(column - 1, -1, -1):
        if left == band_column:
            return ""
        if row_cells[left].text:
            return row_cells[left].text
    return ""


def find_value_column(grid, rows: list[int], excluded: set[int]) -> int | None:
    best_column, best_share = None, 0.0
    for column in range(len(grid[0])):
        if column in excluded:
            continue
        priced = sum(1 for row in rows if _read_value(grid[row][column]) is not None)
        share = priced / len(rows)
        if share >= MIN_COLUMN_SHARE and share > best_share:
            best_column, best_share = column, share
    return best_column


def build_cell(
    label: str, band: AgeBand, cell: TableCell, table: RawTable, band_text: str
) -> ExtractedCell | None:
    if not cell.text and cell.number is None:
        return None
    location = {
        "page": table.page,
        "sheet": table.sheet,
        "cell": cell.reference,
        "band_text": band_text,
        "plan_text": label,
    }
    return ExtractedCell(
        plan_label=label,
        age_band=band,
        raw_text=cell.text or str(cell.number),
        value=_read_value(cell),
        location={key: value for key, value in location.items() if value},
    )


def keep_first_cell_per_band(cells: list[ExtractedCell]) -> tuple[list[ExtractedCell], int]:
    first_by_key: dict[tuple[str, AgeBand], ExtractedCell] = {}
    conflicts = 0
    for cell in cells:
        key = (cell.plan_label, cell.age_band)
        if key not in first_by_key:
            first_by_key[key] = cell
        elif first_by_key[key].value != cell.value:
            conflicts += 1
    return list(first_by_key.values()), conflicts


def _find_band_positions(cells) -> dict[int, AgeBand]:
    return {
        position: band
        for position, cell in enumerate(cells)
        if (band := parse_age_band(cell.text)) is not None
    }


def _keep_priced_line(cells: list[ExtractedCell | None]) -> list[ExtractedCell]:
    present = [cell for cell in cells if cell is not None]
    return present if any(cell.value is not None for cell in present) else []


def _is_label_column(grid, rows: list[int], column: int) -> bool:
    texts = [grid[row][column].text for row in rows]
    labels = [
        text
        for text in texts
        if text and parse_brl_amount(text) is None and not _DATE_LIKE.match(text)
    ]
    return len(labels) / len(rows) >= MIN_COLUMN_SHARE


def _read_value(cell: TableCell):
    return parse_brl_amount(cell.number if cell.number is not None else cell.text)
