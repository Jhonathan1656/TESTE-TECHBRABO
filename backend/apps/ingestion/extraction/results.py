from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from apps.core.domain.age_bands import AgeBand


@dataclass(frozen=True)
class ExtractedCell:
    plan_label: str
    age_band: AgeBand
    raw_text: str
    value: Decimal | None
    location: dict = field(default_factory=dict)


@dataclass(frozen=True)
class DocumentMetadata:
    effective_from: date | None = None
    effective_until: date | None = None
    region: str | None = None


@dataclass(frozen=True)
class ExtractionResult:
    method: str
    cells: tuple[ExtractedCell, ...] = ()
    details: dict = field(default_factory=dict)
    failure_code: str = ""
    failure_params: dict = field(default_factory=dict)
    metadata: DocumentMetadata = field(default_factory=DocumentMetadata)

    @property
    def succeeded(self) -> bool:
        return not self.failure_code and bool(self.cells)

    @property
    def plan_labels(self) -> list[str]:
        return list(dict.fromkeys(cell.plan_label for cell in self.cells))
