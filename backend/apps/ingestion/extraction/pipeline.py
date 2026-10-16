from typing import Protocol

from apps.ingestion.extraction.document_content import DocumentContent
from apps.ingestion.extraction.grid_extractor import extract_grid_prices
from apps.ingestion.extraction.results import ExtractionResult

GRID_METHOD = "grid"
NO_METHOD = "none"


class FallbackExtractor(Protocol):
    def extract(self, content: DocumentContent) -> ExtractionResult: ...


def extract_prices(
    content: DocumentContent, fallback: FallbackExtractor | None = None
) -> ExtractionResult:
    """Layered extraction: deterministic table reading first, AI only for what it cannot read."""
    grid = extract_grid_prices(content)
    if grid.cells:
        return ExtractionResult(
            method=GRID_METHOD,
            cells=grid.cells,
            details={
                "orientations": list(grid.orientations),
                "conflicting_duplicates": grid.conflicting_duplicates,
            },
        )
    if fallback is None:
        return ExtractionResult(method=NO_METHOD, failure_code="extraction.layout_not_recognized")
    return fallback.extract(content)
