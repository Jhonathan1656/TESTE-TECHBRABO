from datetime import UTC, date, datetime

import pytest

from apps.ingestion.services import batch_review_service
from apps.ingestion.tests.builders import (
    REGION,
    create_pricing_world,
    receive_prices,
    standard_prices,
)

pytestmark = pytest.mark.django_db

PUBLISHED_AT = datetime(2026, 4, 25, 15, tzinfo=UTC)


@pytest.fixture
def published_world(reviewer_user):
    world = create_pricing_world()
    batch = receive_prices(
        world, date(2026, 5, 1), standard_prices(world), received_at=PUBLISHED_AT
    )
    batch_review_service.approve_batch(batch, reviewer_user, now=PUBLISHED_AT)
    return world


def test_quote_returns_prices_with_provenance(analyst_client, published_world):
    response = analyst_client.post(
        "/api/quotes", {"ages": [34, 5], "on_date": "2026-08-01", "region": REGION}, format="json"
    )

    assert response.status_code == 200
    [cheapest, _] = response.data
    assert cheapest["plan"]["name"] == published_world.ward.name
    assert cheapest["total"] == "526.00"
    assert [item["band_label"] for item in cheapest["beneficiaries"]] == ["34–38", "0–18"]
    assert cheapest["table"]["effective_from"] == "2026-05-01"
    assert cheapest["table"]["published_by"]["username"] == "reviewer"
    assert cheapest["table"]["document"]["filename"].endswith(".csv")
    assert cheapest["scheduled_change"] is None


def test_quote_validates_its_input(analyst_client):
    response = analyst_client.post(
        "/api/quotes", {"ages": [], "on_date": "2026-08-01", "region": REGION}, format="json"
    )

    assert response.status_code == 400
    assert "ages" in response.data


def test_plan_pricing_lists_every_version_with_its_state(analyst_client, published_world):
    response = analyst_client.get(f"/api/plans/{published_world.ward.public_id}/pricing")

    assert response.status_code == 200
    [version] = response.data["versions"]
    assert version["state"] == "current"
    assert len(version["entries"]) == 10
    assert response.data["ans"] is None


def test_regions_list_only_published_regions(analyst_client, published_world):
    assert analyst_client.get("/api/regions").data == [REGION]
