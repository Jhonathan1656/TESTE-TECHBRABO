from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from apps.catalog.models import Operator, Plan
from apps.catalog.tests.factories import create_operator, create_plan
from apps.core.domain.age_bands import AgeBand
from apps.core.domain.money import format_brl
from apps.ingestion.models import ImportBatch
from apps.ingestion.services.document_intake_service import IncomingFile, receive_document
from apps.quality.tests.builders import build_values
from apps.sources.models import Source
from apps.sources.tests.factories import create_source

REGION = "São Paulo – Capital"
BAND_TEXT = {
    AgeBand.BAND_00_18: "00 a 18 anos",
    AgeBand.BAND_19_23: "19 a 23 anos",
    AgeBand.BAND_24_28: "24 a 28 anos",
    AgeBand.BAND_29_33: "29 a 33 anos",
    AgeBand.BAND_34_38: "34 a 38 anos",
    AgeBand.BAND_39_43: "39 a 43 anos",
    AgeBand.BAND_44_48: "44 a 48 anos",
    AgeBand.BAND_49_53: "49 a 53 anos",
    AgeBand.BAND_54_58: "54 a 58 anos",
    AgeBand.BAND_59_PLUS: "59 anos ou mais",
}
RECEIVED_AT = datetime(2026, 10, 16, 13, tzinfo=UTC)


@dataclass
class PricingWorld:
    operator: Operator
    source: Source
    ward: Plan
    room: Plan


def create_pricing_world(auto_approve: bool = False) -> PricingWorld:
    operator = create_operator()
    return PricingWorld(
        operator=operator,
        source=create_source(operator, auto_approve=auto_approve),
        ward=create_plan(operator, name="Essencial Enfermaria"),
        room=create_plan(operator, name="Essencial Apartamento"),
    )


def build_price_csv(
    operator: Operator,
    effective_from: date,
    prices_by_label: dict[str, dict[AgeBand, Decimal | str]],
    region: str = REGION,
) -> IncomingFile:
    lines = [
        f"Registro ANS {operator.ans_registration}",
        f"Região: {region}",
        f"Vigência: {effective_from:%d/%m/%Y}",
        "",
        ";".join(["Faixa etária", *prices_by_label]),
    ]
    for band in AgeBand:
        cells = [_format_cell(prices[band]) for prices in prices_by_label.values()]
        lines.append(";".join([BAND_TEXT[band], *cells]))
    fingerprint = abs(hash(str(prices_by_label)))
    name = f"tabela-{operator.ans_registration}-{effective_from:%Y%m%d}-{fingerprint}.csv"
    return IncomingFile(name, "\n".join(lines).encode("utf-8"))


def standard_prices(
    world: PricingWorld, adjustment: str = "1"
) -> dict[str, dict[AgeBand, Decimal]]:
    return {
        world.ward.name: build_values("200", adjustment),
        world.room.name: build_values("240", adjustment),
    }


def receive_prices(
    world: PricingWorld,
    effective_from: date,
    prices_by_label: dict,
    received_at: datetime = RECEIVED_AT,
    uploaded_by=None,
) -> ImportBatch:
    incoming = build_price_csv(world.operator, effective_from, prices_by_label)
    return receive_document(
        incoming, world.source, uploaded_by=uploaded_by, received_at=received_at, now=received_at
    )


def _format_cell(value: Decimal | str) -> str:
    return value if isinstance(value, str) else format_brl(value)
