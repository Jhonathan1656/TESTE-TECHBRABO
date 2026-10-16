from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.db.backends.postgresql.psycopg_any import DateRange

from apps.core.domain.age_bands import AgeBand
from apps.ingestion.services import batch_review_service
from apps.ingestion.tests.builders import (
    REGION,
    create_pricing_world,
    receive_prices,
    standard_prices,
)
from apps.pricing.models import PriceTable
from apps.pricing.services.price_lookup_service import (
    TableState,
    classify_table_state,
    find_table_valid_on,
    list_pricing_regions,
)
from apps.pricing.services.publication_service import subtract_range
from apps.pricing.services.quote_service import QuoteRequest, build_quote

pytestmark = pytest.mark.django_db

FIRST_TABLE = date(2026, 5, 1)
NEXT_TABLE = date(2026, 11, 1)
FIRST_PUBLISHED_AT = datetime(2026, 4, 25, 15, tzinfo=UTC)
NEXT_PUBLISHED_AT = datetime(2026, 10, 20, 15, tzinfo=UTC)


@pytest.fixture
def world_with_two_versions(reviewer_user):
    world = create_pricing_world()
    first = receive_prices(
        world, FIRST_TABLE, standard_prices(world), received_at=FIRST_PUBLISHED_AT
    )
    batch_review_service.approve_batch(first, reviewer_user, now=FIRST_PUBLISHED_AT)
    second = receive_prices(
        world, NEXT_TABLE, standard_prices(world, "1.098"), received_at=NEXT_PUBLISHED_AT
    )
    batch_review_service.approve_batch(second, reviewer_user, now=NEXT_PUBLISHED_AT)
    return world


def test_database_refuses_overlapping_current_versions(world_with_two_versions):
    world = world_with_two_versions
    existing = PriceTable.objects.current().filter(plan=world.ward).first()

    with pytest.raises(IntegrityError), transaction.atomic():
        PriceTable.objects.create(
            plan=world.ward,
            region=REGION,
            validity=DateRange(date(2026, 6, 1), None),
            batch=existing.batch,
            recorded_at=NEXT_PUBLISHED_AT,
        )


def test_current_prices_follow_the_effective_dates(world_with_two_versions):
    world = world_with_two_versions

    before = find_table_valid_on(world.ward, REGION, date(2026, 8, 1))
    after = find_table_valid_on(world.ward, REGION, date(2026, 12, 1))

    assert before.entries.get(age_band=AgeBand.BAND_00_18).value == Decimal("200.00")
    assert after.entries.get(age_band=AgeBand.BAND_00_18).value == Decimal("219.60")


def test_known_at_reproduces_what_the_quoter_showed(world_with_two_versions):
    world = world_with_two_versions
    before_second_publication = NEXT_PUBLISHED_AT - timedelta(days=1)

    shown_then = find_table_valid_on(
        world.ward, REGION, date(2026, 12, 1), known_at=before_second_publication
    )
    shown_now = find_table_valid_on(world.ward, REGION, date(2026, 12, 1))

    assert shown_then.validity.upper is None
    assert shown_then.superseded_at == NEXT_PUBLISHED_AT
    assert shown_then.entries.get(age_band=AgeBand.BAND_00_18).value == Decimal("200.00")
    assert shown_now.entries.get(age_band=AgeBand.BAND_00_18).value == Decimal("219.60")


def test_quote_prices_each_beneficiary_and_announces_the_next_table(world_with_two_versions):
    world = world_with_two_versions

    quotes = build_quote(
        QuoteRequest(ages=(34, 5), on_date=date(2026, 10, 25), region=REGION),
        now=NEXT_PUBLISHED_AT + timedelta(days=5),
    )

    assert [quote.table.plan for quote in quotes] == [world.ward, world.room]
    ward_quote = quotes[0]
    assert [(price.age, price.age_band) for price in ward_quote.beneficiaries] == [
        (34, AgeBand.BAND_34_38),
        (5, AgeBand.BAND_00_18),
    ]
    assert ward_quote.total == Decimal("526.00")
    assert ward_quote.scheduled_change.table.validity.lower == NEXT_TABLE
    assert ward_quote.scheduled_change.total == Decimal("577.55")
    assert ward_quote.source_freshness.status == "fresh"


def test_quote_as_known_before_the_update_has_no_scheduled_change(world_with_two_versions):
    known_at = NEXT_PUBLISHED_AT - timedelta(hours=1)

    quotes = build_quote(
        QuoteRequest(ages=(34,), on_date=date(2026, 10, 25), region=REGION, known_at=known_at)
    )

    assert all(quote.scheduled_change is None for quote in quotes)


def test_table_states_and_regions(world_with_two_versions):
    tables = list(
        PriceTable.objects.filter(plan=world_with_two_versions.ward).order_by(
            "recorded_at", "validity"
        )
    )
    today = date(2026, 10, 25)

    states = [classify_table_state(table, today) for table in tables]

    assert sorted(states) == sorted(
        [TableState.SUPERSEDED, TableState.CURRENT, TableState.SCHEDULED]
    )
    assert list_pricing_regions() == [REGION]


@pytest.mark.parametrize(
    ("original", "removed", "expected"),
    [
        (
            (date(2026, 1, 1), None),
            (date(2026, 6, 1), None),
            [(date(2026, 1, 1), date(2026, 6, 1))],
        ),
        (
            (date(2026, 1, 1), None),
            (date(2026, 3, 1), date(2026, 4, 1)),
            [(date(2026, 1, 1), date(2026, 3, 1)), (date(2026, 4, 1), None)],
        ),
        ((date(2026, 6, 1), None), (date(2026, 1, 1), None), []),
    ],
)
def test_subtract_range_keeps_the_parts_that_still_hold(original, removed, expected):
    remaining = subtract_range(DateRange(*original, "[)"), DateRange(*removed, "[)"))

    assert [(piece.lower, piece.upper) for piece in remaining] == expected
