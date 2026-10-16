import zipfile
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from apps.ans_reference.importers.row_mappers import map_price_band_row
from apps.ans_reference.models import (
    AnsDataset,
    AnsOperatorRecord,
    AnsPlanRecord,
    AnsPriceBandRecord,
    AnsSyncRun,
    SyncStatus,
)
from apps.ans_reference.services.lookup_service import (
    AnsPlanStatus,
    find_plan_references,
    map_plan_status,
)
from apps.ans_reference.services.sync_service import build_default_location, sync_ans_dataset
from apps.catalog.tests.factories import create_operator, create_plan
from apps.core.domain.age_bands import AgeBand

FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 10, 16, 9, tzinfo=UTC)

pytestmark = pytest.mark.django_db


@pytest.fixture
def price_band_zip(tmp_path) -> str:
    archive_path = tmp_path / "nota_tecnica_vcm_faixa_etaria.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.write(FIXTURES / "NOTA_TECNICA_VCM_FAIXA_ETARIA_2026.csv", "NOTA_TECNICA_2026.csv")
    return str(archive_path)


def test_sync_operators_reads_cadop_format():
    run = sync_ans_dataset(AnsDataset.OPERATORS, str(FIXTURES / "Relatorio_cadop.csv"), now=NOW)

    assert run.status == SyncStatus.SUCCEEDED
    assert (run.rows_read, run.rows_saved) == (2, 2)
    operator = AnsOperatorRecord.objects.get(registration="900011")
    assert operator.modality == "Medicina de Grupo"
    assert operator.registered_on == date(2010, 3, 15)
    assert operator.state == "SP"


def test_sync_plans_filters_by_operator_and_is_idempotent():
    location = str(FIXTURES / "pda-008-caracteristicas_produtos_saude_suplementar.csv")

    sync_ans_dataset(AnsDataset.PLANS, location, operator_registrations={"900011"}, now=NOW)
    run = sync_ans_dataset(AnsDataset.PLANS, location, operator_registrations={"900011"}, now=NOW)

    assert (run.rows_read, run.rows_saved) == (3, 2)
    assert AnsPlanRecord.objects.count() == 2
    suspended = AnsPlanRecord.objects.get(product_code="990102241")
    assert suspended.status == "Suspenso"
    assert suspended.accommodation == "Individual"


def test_sync_price_bands_reads_zip_and_widens_duplicated_bands(price_band_zip):
    run = sync_ans_dataset(AnsDataset.PRICE_BANDS, price_band_zip, now=NOW)

    assert run.rows_saved == 5
    widened = AnsPriceBandRecord.objects.get(note_code=55501, age_band=AgeBand.BAND_59_PLUS)
    assert (widened.min_value, widened.max_value) == (Decimal("870.00"), Decimal("1640.00"))


def test_sync_failure_is_recorded_and_raised(tmp_path):
    with pytest.raises(FileNotFoundError):
        sync_ans_dataset(AnsDataset.OPERATORS, str(tmp_path / "missing.csv"), now=NOW)

    run = AnsSyncRun.objects.get()
    assert run.status == SyncStatus.FAILED
    assert "FileNotFoundError" in run.error_message


def test_default_location_points_to_configured_base_url():
    assert build_default_location(AnsDataset.OPERATORS) == (
        "http://localhost:1/ans/operadoras_de_plano_de_saude_ativas/Relatorio_cadop.csv"
    )


def test_map_price_band_row_skips_unknown_band_labels():
    row = {
        "CD_OPERADORA": "1",
        "ID_PLANO": "1",
        "CD_NOTA": "1",
        "DT_NTRP": "01/01/2026",
        "FAIXA_ETARIA": "faixa desconhecida",
        "VL_COMERCIAL_MENSALIDADE": "1",
        "VCM_MINIMO": "1",
        "VCM_MAXIMO": "1",
    }

    assert map_price_band_row(row) is None


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("Ativo", AnsPlanStatus.ACTIVE),
        ("Suspenso", AnsPlanStatus.SUSPENDED),
        ("ATIVO COM COMERCIALIZACAO SUSPENSA", AnsPlanStatus.SUSPENDED),
        ("Cancelado", AnsPlanStatus.CANCELLED),
        ("algo novo", AnsPlanStatus.UNKNOWN),
    ],
)
def test_map_plan_status_understands_ans_labels(label, expected):
    assert map_plan_status(label) == expected


def test_find_plan_references_returns_status_and_latest_note_bands(price_band_zip):
    sync_ans_dataset(
        AnsDataset.PLANS,
        str(FIXTURES / "pda-008-caracteristicas_produtos_saude_suplementar.csv"),
        now=NOW,
    )
    sync_ans_dataset(AnsDataset.PRICE_BANDS, price_band_zip, now=NOW)
    operator = create_operator(ans_registration="900011")
    ward = create_plan(operator, name="Plano Teste Enfermaria", ans_product_code="990101241")
    room = create_plan(operator, name="Plano Teste Apartamento", ans_product_code="990102241")
    unknown = create_plan(operator, name="Plano Sem Registro", ans_product_code="")

    references = find_plan_references([ward, room, unknown])

    assert set(references) == {ward.id, room.id}
    assert references[ward.id].status == AnsPlanStatus.ACTIVE
    assert references[ward.id].note_code == 55501
    assert references[ward.id].price_bands[AgeBand.BAND_00_18].max_value == Decimal("286.00")
    assert AgeBand.BAND_24_28 not in references[ward.id].price_bands
    assert not references[room.id].is_sellable
    assert references[room.id].price_bands == {}
