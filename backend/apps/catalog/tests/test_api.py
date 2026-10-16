import pytest

from apps.catalog.tests.factories import create_operator, create_plan

pytestmark = pytest.mark.django_db


def test_plans_can_be_filtered_by_operator(analyst_client):
    first = create_operator()
    second = create_operator()
    create_plan(first, name="Essencial Enfermaria")
    create_plan(second, name="Outro Plano")

    response = analyst_client.get("/api/plans", {"operator": str(first.public_id)})

    assert [plan["name"] for plan in response.data] == ["Essencial Enfermaria"]
    assert response.data[0]["ans_code"].count(".") == 1


def test_only_reviewers_remove_plans_from_the_quoter(analyst_client, reviewer_client):
    plan = create_plan(create_operator(), name="Essencial Enfermaria")
    url = f"/api/plans/{plan.public_id}/deactivation"

    assert analyst_client.post(url).status_code == 403
    assert reviewer_client.post(url).data["is_active"] is False
    again = reviewer_client.post(url)
    assert again.status_code == 400
    assert again.data["code"] == "plan.already_inactive"


def test_operators_are_listed(analyst_client):
    create_operator(name="Operadora Fictícia")

    assert [operator["name"] for operator in analyst_client.get("/api/operators").data] == [
        "Operadora Fictícia"
    ]
