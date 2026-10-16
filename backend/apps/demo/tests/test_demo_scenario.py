import pytest

from apps.demo.services.delivery_service import collect_demo_delivery, list_demo_deliveries
from apps.demo.services.seed_service import SeedSummary, seed_demo
from apps.ingestion.models import BatchStatus
from apps.ingestion.services.collector_service import CollectionStatus
from apps.monitoring.models import AlertKind, AlertStatus, MonitoringAlert
from apps.pricing.models import PriceTable
from apps.quality.models import IssueStatus

pytestmark = pytest.mark.django_db


@pytest.fixture
def seeded():
    return seed_demo()


def find_open_codes(batch) -> set[str]:
    return set(batch.issues.filter(status=IssueStatus.OPEN).values_list("rule_code", flat=True))


def test_seed_builds_history_reference_data_and_alerts(seeded):
    assert seeded == SeedSummary(
        created=True, operators=3, plans=11, published_batches=3, open_alerts=3
    )
    assert PriceTable.objects.current().count() == 11
    open_kinds = set(
        MonitoringAlert.objects.filter(status=AlertStatus.OPEN).values_list("kind", flat=True)
    )
    assert open_kinds == {
        AlertKind.PLAN_NOT_ACTIVE_AT_ANS,
        AlertKind.SOURCE_OVERDUE,
        AlertKind.STALE_PRICE_TABLE,
    }


def test_seed_is_idempotent(seeded):
    assert seed_demo() == SeedSummary(created=False)


def test_portal_update_catches_both_typos(seeded):
    outcome = collect_demo_delivery("vida_plena_update")

    assert outcome.status == CollectionStatus.RECEIVED
    assert outcome.batch.status == BatchStatus.PENDING_REVIEW
    assert find_open_codes(outcome.batch) == {
        "rn63.last_band_ratio",
        "rn63.accumulated_variation",
        "consistency.non_uniform_adjustment",
        "consistency.large_variation",
        "validity.scheduled",
    }


def test_email_update_is_held_for_review_despite_auto_approval(seeded):
    outcome = collect_demo_delivery("horizonte_update")

    assert outcome.batch.status == BatchStatus.PENDING_REVIEW
    assert {
        "catalog.unmatched_plan",
        "catalog.similarity_match",
        "consistency.decimal_shift",
        "rn63.negative_variation",
        "ans.outside_registered_band",
    } <= find_open_codes(outcome.batch)


def test_prose_notice_needs_ai_or_manual_handling(seeded):
    outcome = collect_demo_delivery("coop_notice")

    assert outcome.batch.status == BatchStatus.FAILED
    assert outcome.batch.failure_code == "extraction.layout_not_recognized"


def test_resent_file_is_recognized_by_its_hash(seeded):
    outcome = collect_demo_delivery("horizonte_resend")

    assert outcome.status == CollectionStatus.UNCHANGED
    assert outcome.batch.status == BatchStatus.PUBLISHED


def test_delivery_list_tracks_what_was_already_collected(seeded):
    collect_demo_delivery("vida_plena_update")

    deliveries = {delivery.key: delivery for delivery in list_demo_deliveries()}

    assert deliveries["vida_plena_update"].latest_batch is not None
    assert deliveries["horizonte_update"].latest_batch is None
    assert len(deliveries) == 4
