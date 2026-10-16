from datetime import date
from decimal import Decimal

import pytest

from apps.catalog.models import PlanAlias
from apps.core.domain.age_bands import AgeBand
from apps.core.exceptions import ConflictError, DomainError
from apps.ingestion.models import BatchStatus, ExtractionMethod, PlanMatchMethod
from apps.ingestion.services import batch_review_service
from apps.ingestion.services.document_intake_service import IncomingFile, receive_document
from apps.ingestion.tests.builders import (
    RECEIVED_AT,
    build_price_csv,
    create_pricing_world,
    receive_prices,
    standard_prices,
)
from apps.pricing.models import PriceTable
from apps.quality.models import IssueStatus
from apps.sources.models import CheckOutcome

pytestmark = pytest.mark.django_db

FIRST_TABLE = date(2026, 5, 1)
NEXT_TABLE = date(2026, 11, 1)


def find_open_codes(batch) -> set[str]:
    return set(batch.issues.filter(status=IssueStatus.OPEN).values_list("rule_code", flat=True))


def publish_first_table(world, reviewer_user):
    batch = receive_prices(world, FIRST_TABLE, standard_prices(world))
    batch_review_service.approve_batch(batch, reviewer_user, now=RECEIVED_AT)
    return batch


def test_received_document_is_extracted_matched_and_validated():
    world = create_pricing_world()

    batch = receive_prices(world, NEXT_TABLE, standard_prices(world))

    assert batch.status == BatchStatus.PENDING_REVIEW
    assert batch.extraction_method == ExtractionMethod.GRID
    assert (batch.effective_from, batch.region) == (NEXT_TABLE, "São Paulo – Capital")
    extracted = list(batch.extracted_plans.order_by("position"))
    assert [item.plan for item in extracted] == [world.ward, world.room]
    assert {item.match_method for item in extracted} == {PlanMatchMethod.ALIAS}
    assert sum(item.prices.count() for item in extracted) == 20
    assert find_open_codes(batch) == {"catalog.no_previous_table", "validity.scheduled"}
    assert world.source.checks.get().outcome == CheckOutcome.NEW_MATERIAL


def test_same_file_twice_is_a_conflict():
    world = create_pricing_world()
    incoming = build_price_csv(world.operator, NEXT_TABLE, standard_prices(world))
    receive_document(incoming, world.source, received_at=RECEIVED_AT, now=RECEIVED_AT)

    with pytest.raises(ConflictError) as raised:
        receive_document(incoming, world.source)

    assert raised.value.message_key == "document.duplicate"


def test_unsupported_and_unreadable_files_are_rejected():
    world = create_pricing_world()

    with pytest.raises(DomainError) as unsupported:
        receive_document(IncomingFile("tabela.docx", b"x"), world.source)
    with pytest.raises(DomainError) as unreadable:
        receive_document(IncomingFile("tabela.pdf", b"not a pdf"), world.source)

    assert unsupported.value.message_key == "document.unsupported_type"
    assert unreadable.value.message_key == "document.unreadable"


def test_trusted_source_publishes_clean_batches_automatically():
    world = create_pricing_world(auto_approve=True)

    batch = receive_prices(world, FIRST_TABLE, standard_prices(world))

    batch.refresh_from_db()
    assert batch.status == BatchStatus.PUBLISHED
    assert batch.auto_published
    assert batch.reviewed_by is None
    assert PriceTable.objects.current().count() == 2


def test_trusted_source_still_needs_review_when_something_looks_wrong(reviewer_user):
    world = create_pricing_world(auto_approve=True)
    receive_prices(world, FIRST_TABLE, standard_prices(world))
    prices = standard_prices(world, "1.098")
    prices[world.ward.name][AgeBand.BAND_44_48] = Decimal("580.00")

    batch = receive_prices(world, NEXT_TABLE, prices)

    assert batch.status == BatchStatus.PENDING_REVIEW
    assert "consistency.non_uniform_adjustment" in find_open_codes(batch)


def test_publication_keeps_bitemporal_history(reviewer_user):
    world = create_pricing_world()
    publish_first_table(world, reviewer_user)
    first_version = PriceTable.objects.get(plan=world.ward)
    batch = receive_prices(world, NEXT_TABLE, standard_prices(world, "1.098"))

    batch_review_service.approve_batch(batch, reviewer_user)

    current = PriceTable.objects.current().filter(plan=world.ward).order_by("validity")
    assert [(table.validity.lower, table.validity.upper) for table in current] == [
        (FIRST_TABLE, NEXT_TABLE),
        (NEXT_TABLE, None),
    ]
    first_version.refresh_from_db()
    assert first_version.superseded_at is not None
    assert current[0].derived_from == first_version
    assert current[0].batch == first_version.batch


def test_same_effective_date_replaces_the_published_version(reviewer_user):
    world = create_pricing_world()
    publish_first_table(world, reviewer_user)
    corrected = standard_prices(world, "1.01")

    batch = receive_prices(world, FIRST_TABLE, corrected)
    assert "validity.same_effective_date" in find_open_codes(batch)
    for issue in batch.issues.filter(status=IssueStatus.OPEN, severity="warning"):
        batch_review_service.acknowledge_issue(issue, "Operadora corrigiu a tabela.", reviewer_user)
    batch_review_service.approve_batch(batch, reviewer_user)

    [current] = PriceTable.objects.current().filter(plan=world.ward)
    assert current.batch == batch
    assert PriceTable.objects.filter(plan=world.ward, superseded_at__isnull=False).count() == 1


def test_correcting_a_typo_resolves_the_issue_and_unblocks_publication(reviewer_user, analyst_user):
    world = create_pricing_world()
    publish_first_table(world, reviewer_user)
    prices = standard_prices(world, "1.098")
    prices[world.ward.name][AgeBand.BAND_44_48] = Decimal("580.00")
    batch = receive_prices(world, NEXT_TABLE, prices)
    with pytest.raises(DomainError) as blocked:
        batch_review_service.approve_batch(batch, reviewer_user)
    assert blocked.value.message_key == "batch.has_blocking_issues"

    typo = batch.extracted_plans.get(plan=world.ward).prices.get(age_band=AgeBand.BAND_44_48)
    batch_review_service.correct_price(typo, Decimal("527.04"), analyst_user)
    tables = batch_review_service.approve_batch(batch, reviewer_user)

    assert "consistency.non_uniform_adjustment" not in find_open_codes(batch)
    published = next(table for table in tables if table.plan == world.ward)
    entry = published.entries.get(age_band=AgeBand.BAND_44_48)
    assert (entry.value, entry.was_corrected) == (Decimal("527.04"), True)


def test_mapping_an_unknown_label_teaches_an_alias(analyst_user):
    world = create_pricing_world()
    prices = {"Linha Ouro Max": standard_prices(world)[world.ward.name]}
    first = receive_prices(world, FIRST_TABLE, prices)
    extracted = first.extracted_plans.get()
    assert extracted.match_method == PlanMatchMethod.UNMATCHED

    batch_review_service.map_extracted_plan(extracted, world.ward, analyst_user)
    second = receive_prices(
        world, NEXT_TABLE, {"Linha Ouro Max": standard_prices(world, "1.05")[world.ward.name]}
    )

    assert PlanAlias.objects.get().plan == world.ward
    assert "catalog.unmatched_plan" not in find_open_codes(first)
    assert second.extracted_plans.get().match_method == PlanMatchMethod.ALIAS


def test_only_warnings_can_be_acknowledged(analyst_user):
    world = create_pricing_world()
    batch = receive_prices(
        world, NEXT_TABLE, {"Plano Desconhecido": standard_prices(world)[world.ward.name]}
    )
    error = batch.issues.get(rule_code="catalog.unmatched_plan")

    with pytest.raises(DomainError) as raised:
        batch_review_service.acknowledge_issue(error, "ok", analyst_user)

    assert raised.value.message_key == "issue.only_warnings_can_be_acknowledged"


def test_excluding_a_plan_drops_its_issues_and_publication(reviewer_user):
    world = create_pricing_world()
    prices = {
        **standard_prices(world),
        "Plano Desconhecido": standard_prices(world)[world.ward.name],
    }
    batch = receive_prices(world, NEXT_TABLE, prices)
    unknown = batch.extracted_plans.get(label="Plano Desconhecido")

    batch_review_service.set_plan_exclusion(unknown, True, reviewer_user)
    tables = batch_review_service.approve_batch(batch, reviewer_user)

    assert {table.plan for table in tables} == {world.ward, world.room}


def test_rejected_batch_cannot_be_published(reviewer_user):
    world = create_pricing_world()
    batch = receive_prices(world, NEXT_TABLE, standard_prices(world))

    batch_review_service.reject_batch(batch, "Tabela de outra região.", reviewer_user)

    batch.refresh_from_db()
    assert batch.status == BatchStatus.REJECTED
    with pytest.raises(DomainError):
        batch_review_service.approve_batch(batch, reviewer_user)


def test_missing_effective_date_can_be_supplied_by_the_reviewer(analyst_user):
    world = create_pricing_world()
    incoming = IncomingFile(
        "sem-data.csv",
        build_price_csv(world.operator, NEXT_TABLE, standard_prices(world)).content.replace(
            b"Vig\xc3\xaancia: 01/11/2026", b"Tabela comercial"
        ),
    )
    batch = receive_document(incoming, world.source, received_at=RECEIVED_AT, now=RECEIVED_AT)
    assert "validity.missing_effective_date" in find_open_codes(batch)

    dates = batch_review_service.EffectiveDates(NEXT_TABLE, None, batch.region)
    batch_review_service.update_effective_dates(batch, dates, analyst_user)

    assert "validity.missing_effective_date" not in find_open_codes(batch)


def test_failed_extraction_can_be_reprocessed():
    world = create_pricing_world()
    incoming = IncomingFile("comunicado.csv", b"Comunicado;sem tabela\nValores;em breve")
    failed = receive_document(incoming, world.source, received_at=RECEIVED_AT, now=RECEIVED_AT)
    assert (failed.status, failed.failure_code) == (
        BatchStatus.FAILED,
        "extraction.layout_not_recognized",
    )

    retried = batch_review_service.reprocess_failed_batch(failed)

    assert retried.pk != failed.pk
    assert retried.document == failed.document
    assert retried.status == BatchStatus.FAILED
