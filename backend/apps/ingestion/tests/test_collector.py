import pytest
from django.core.management import call_command

from apps.ingestion.services.collector_service import CollectionStatus, collect_file
from apps.ingestion.services.document_intake_service import IncomingFile
from apps.ingestion.tests.builders import (
    RECEIVED_AT,
    build_price_csv,
    create_pricing_world,
    standard_prices,
)
from apps.sources.models import CheckOutcome, SourceChannel
from apps.sources.tests.factories import create_source

pytestmark = pytest.mark.django_db
NEXT_TABLE = RECEIVED_AT.date().replace(month=11, day=1)


def test_collector_routes_material_by_the_ans_registration_it_contains():
    world = create_pricing_world()
    inbox = create_source(world.operator, name="Inbox", channel=SourceChannel.EMAIL_INBOX)

    outcome = collect_file(
        build_price_csv(world.operator, NEXT_TABLE, standard_prices(world)),
        SourceChannel.EMAIL_INBOX,
        now=RECEIVED_AT,
    )

    assert outcome.status == CollectionStatus.RECEIVED
    assert outcome.source == inbox
    assert outcome.batch.operator == world.operator


def test_collecting_the_same_file_again_confirms_the_source_instead_of_reprocessing():
    world = create_pricing_world()
    incoming = build_price_csv(world.operator, NEXT_TABLE, standard_prices(world))
    first = collect_file(incoming, now=RECEIVED_AT)

    second = collect_file(incoming, now=RECEIVED_AT)

    assert second.status == CollectionStatus.UNCHANGED
    assert second.batch == first.batch
    outcomes = list(
        world.source.checks.order_by("checked_at", "id").values_list("outcome", flat=True)
    )
    assert outcomes == [CheckOutcome.NEW_MATERIAL, CheckOutcome.UNCHANGED]


def test_material_without_a_known_registration_is_left_unidentified():
    create_pricing_world()

    outcome = collect_file(IncomingFile("sem-registro.csv", b"Faixa;Plano\n00 a 18 anos;100,00"))

    assert outcome.status == CollectionStatus.UNIDENTIFIED
    assert outcome.batch is None


def test_collect_inbox_command_processes_a_folder(tmp_path):
    world = create_pricing_world()
    incoming = build_price_csv(world.operator, NEXT_TABLE, standard_prices(world))
    (tmp_path / incoming.name).write_bytes(incoming.content)
    (tmp_path / "ignored.txt").write_text("not material")

    call_command("collect_inbox", str(tmp_path))

    assert world.operator.batches.count() == 1
