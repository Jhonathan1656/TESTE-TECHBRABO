from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from apps.core.domain.age_bands import AgeBand
from apps.core.domain.severity import Severity


@dataclass(frozen=True)
class QualityThresholds:
    large_variation_pct: Decimal = Decimal("25")
    non_uniform_tolerance_pp: Decimal = Decimal("1.0")
    decimal_shift_tolerance: Decimal = Decimal("0.15")
    late_capture_days: int = 1


@dataclass(frozen=True)
class RegisteredBand:
    min_value: Decimal
    max_value: Decimal


@dataclass(frozen=True)
class PlanSnapshot:
    """One plan as found in a batch, with everything the rules need to judge it."""

    label: str
    plan_id: int | None = None
    plan_name: str | None = None
    product_line: str | None = None
    contract_type: str | None = None
    accommodation: str | None = None
    has_coparticipation: bool | None = None
    match_method: str = "alias"
    match_score: float | None = None
    suggestions: tuple[str, ...] = ()
    values: Mapping[AgeBand, Decimal | None] = field(default_factory=dict)
    raw_texts: Mapping[AgeBand, str] = field(default_factory=dict)
    previous_values: Mapping[AgeBand, Decimal] = field(default_factory=dict)
    current_effective_from: date | None = None
    ans_status: str | None = None
    ans_status_label: str | None = None
    ans_status_date: date | None = None
    registered_bands: Mapping[AgeBand, RegisteredBand] = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        return self.plan_name or self.label

    @property
    def is_matched(self) -> bool:
        return self.plan_id is not None

    def priced_bands(self) -> dict[AgeBand, Decimal]:
        return {band: value for band, value in sorted(self.values.items()) if value is not None}


@dataclass(frozen=True)
class MissingPlan:
    plan_id: int
    plan_name: str
    effective_from: date


@dataclass(frozen=True)
class BatchSnapshot:
    today: date
    effective_from: date | None
    extraction_method: str
    extraction_model: str = ""
    document_text: str = ""
    plans: tuple[PlanSnapshot, ...] = ()
    missing_plans: tuple[MissingPlan, ...] = ()
    conflicting_duplicates: int = 0
    thresholds: QualityThresholds = field(default_factory=QualityThresholds)


@dataclass(frozen=True)
class Finding:
    rule_code: str
    severity: Severity
    plan_label: str = ""
    age_band: AgeBand | None = None
    params: dict = field(default_factory=dict)
    discriminator: str = ""

    @property
    def fingerprint(self) -> str:
        band = str(int(self.age_band)) if self.age_band is not None else ""
        return "|".join((self.rule_code, self.plan_label, band, self.discriminator))[:255]
