import pytest

from apps.catalog.tests.factories import create_operator
from apps.sources.tests.factories import create_source

pytestmark = pytest.mark.django_db


def test_sources_are_listed_with_freshness(analyst_client):
    create_source(create_operator())

    [source] = analyst_client.get("/api/sources").data

    assert source["freshness"]["status"] == "never_checked"
    assert source["freshness"]["days_since_success"] is None


def test_analyst_confirms_a_source_is_still_current(analyst_client):
    source = create_source(create_operator())

    response = analyst_client.post(
        f"/api/sources/{source.public_id}/confirmations",
        {"note": "Operadora confirmou por telefone."},
        format="json",
    )
    checks = analyst_client.get(f"/api/sources/{source.public_id}/checks").data

    assert response.status_code == 201
    assert response.data["freshness"]["status"] == "fresh"
    assert checks[0]["outcome"] == "unchanged"
    assert checks[0]["checked_by"]["username"] == "analyst"
