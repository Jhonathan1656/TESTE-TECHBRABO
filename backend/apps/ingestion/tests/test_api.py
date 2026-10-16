from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.ingestion.models import ExtractedPrice
from apps.ingestion.tests.builders import build_price_csv, create_pricing_world, standard_prices
from apps.quality.models import IssueStatus
from conftest import create_user_with_role

pytestmark = pytest.mark.django_db

NEXT_TABLE = date(2026, 11, 1)


def upload(client, world, prices=None, effective_from=NEXT_TABLE):
    incoming = build_price_csv(world.operator, effective_from, prices or standard_prices(world))
    file = SimpleUploadedFile(incoming.name, incoming.content, content_type="text/csv")
    return client.post(
        "/api/documents", {"file": file, "source": str(world.source.public_id)}, format="multipart"
    )


def batch_url(batch_id, suffix=""):
    return f"/api/batches/{batch_id}{suffix}"


def test_upload_requires_authentication_and_analyst_role(api_client):
    world = create_pricing_world()
    guest = create_user_with_role("guest", None)

    assert upload(api_client, world).status_code == 401
    api_client.force_authenticate(guest)
    assert upload(api_client, world).status_code == 403


def test_upload_returns_the_review_payload(analyst_client):
    world = create_pricing_world()

    response = upload(analyst_client, world)

    assert response.status_code == 201
    body = response.data
    assert body["status"] == "pending_review"
    assert body["source"]["name"] == world.source.name
    assert [plan["plan"]["name"] for plan in body["plans"]] == [world.ward.name, world.room.name]
    assert body["summary"]["prices"] == 20
    assert {issue["rule_code"] for issue in body["issues"]} == {
        "catalog.no_previous_table",
        "validity.scheduled",
    }
    assert body["timeline"][0]["action"] == "document.received"
    assert body["can_publish"] is True


def test_duplicate_upload_is_a_translated_conflict(analyst_client):
    world = create_pricing_world()
    upload(analyst_client, world)

    response = upload(analyst_client, world)

    assert response.status_code == 409
    assert response.data["code"] == "document.duplicate"
    assert "já foi recebido" in response.data["detail"]
    assert response.data["params"]["batch"]


def test_unknown_batch_is_a_translated_not_found(analyst_client):
    response = analyst_client.get(batch_url(uuid4()))

    assert response.status_code == 404
    assert response.data == {
        "code": "resource.not_found",
        "detail": "Registro não encontrado.",
        "params": {},
    }


def test_patch_with_only_corrected_value_leaves_every_other_field_unchanged(analyst_client):
    world = create_pricing_world()
    batch_id = upload(analyst_client, world).data["id"]
    price = ExtractedPrice.objects.filter(extracted_plan__batch__public_id=batch_id).first()
    before = (
        price.raw_text,
        price.extracted_value,
        price.location,
        price.age_band,
        price.previous_value,
    )

    response = analyst_client.patch(
        batch_url(batch_id, f"/prices/{price.public_id}"),
        {"corrected_value": "199.90"},
        format="json",
    )

    price.refresh_from_db()
    assert response.status_code == 200
    assert price.corrected_value == Decimal("199.90")
    assert (
        price.raw_text,
        price.extracted_value,
        price.location,
        price.age_band,
        price.previous_value,
    ) == before


def test_patch_without_the_field_keeps_and_explicit_null_clears_the_correction(analyst_client):
    world = create_pricing_world()
    batch_id = upload(analyst_client, world).data["id"]
    price = ExtractedPrice.objects.filter(extracted_plan__batch__public_id=batch_id).first()
    url = batch_url(batch_id, f"/prices/{price.public_id}")
    analyst_client.patch(url, {"corrected_value": "199.90"}, format="json")

    analyst_client.patch(url, {}, format="json")
    price.refresh_from_db()
    assert price.corrected_value == Decimal("199.90")

    analyst_client.patch(url, {"corrected_value": None}, format="json")
    price.refresh_from_db()
    assert price.corrected_value is None
    assert price.corrected_by is None


def test_publishing_is_reserved_to_reviewers(analyst_client, reviewer_client):
    world = create_pricing_world()
    batch_id = upload(analyst_client, world).data["id"]

    assert (
        analyst_client.post(batch_url(batch_id, "/publication"), {}, format="json").status_code
        == 403
    )
    response = reviewer_client.post(
        batch_url(batch_id, "/publication"), {"note": "ok"}, format="json"
    )

    assert response.status_code == 200
    assert response.data["status"] == "published"
    assert response.data["reviewed_by"]["username"] == "reviewer"


def test_publishing_with_open_issues_returns_counts(reviewer_client, analyst_client):
    world = create_pricing_world()
    prices = {**standard_prices(world), "Plano Novo": standard_prices(world)[world.ward.name]}
    batch_id = upload(analyst_client, world, prices).data["id"]

    response = reviewer_client.post(batch_url(batch_id, "/publication"), {}, format="json")

    assert response.status_code == 400
    assert response.data["code"] == "batch.has_blocking_issues"
    assert response.data["params"] == {"errors": 1, "warnings": 0}


def test_review_endpoints_map_exclude_and_acknowledge(analyst_client, reviewer_client):
    world = create_pricing_world()
    prices = standard_prices(world, "1.0")
    prices["Linha Ouro Max"] = standard_prices(world)[world.ward.name]
    body = upload(analyst_client, world, prices).data
    unknown = next(plan for plan in body["plans"] if plan["label"] == "Linha Ouro Max")

    mapped = analyst_client.post(
        batch_url(body["id"], f"/plans/{unknown['id']}/mapping"),
        {"plan": str(world.ward.public_id)},
        format="json",
    ).data
    excluded = analyst_client.post(
        batch_url(body["id"], f"/plans/{unknown['id']}/exclusion"),
        {"excluded": True},
        format="json",
    ).data

    assert (
        next(plan for plan in mapped["plans"] if plan["id"] == unknown["id"])["match_method"]
        == "manual"
    )
    assert (
        next(plan for plan in excluded["plans"] if plan["id"] == unknown["id"])["is_excluded"]
        is True
    )
    assert excluded["summary"]["excluded_plans"] == 1


def test_acknowledging_a_warning_requires_a_note(analyst_client, reviewer_user):
    world = create_pricing_world()
    prices = {"Essencial Enfermaria Plus": standard_prices(world)[world.ward.name]}
    body = upload(analyst_client, world, prices).data
    warning = next(
        issue for issue in body["issues"] if issue["rule_code"] == "catalog.similarity_match"
    )
    url = batch_url(body["id"], f"/issues/{warning['id']}/acknowledgement")

    assert analyst_client.post(url, {}, format="json").status_code == 400
    response = analyst_client.post(
        url, {"note": "Valor confirmado com a operadora."}, format="json"
    )

    acknowledged = next(issue for issue in response.data["issues"] if issue["id"] == warning["id"])
    assert acknowledged["status"] == IssueStatus.ACKNOWLEDGED
    assert acknowledged["acknowledgement_note"] == "Valor confirmado com a operadora."


def test_effective_dates_and_rejection(analyst_client, reviewer_client):
    world = create_pricing_world()
    batch_id = upload(analyst_client, world).data["id"]

    invalid = analyst_client.put(
        batch_url(batch_id, "/effective-dates"),
        {"effective_from": "2026-12-01", "effective_until": "2026-11-01", "region": "SP"},
        format="json",
    )
    rejected = reviewer_client.post(
        batch_url(batch_id, "/rejection"), {"reason": "Região errada."}, format="json"
    )

    assert invalid.status_code == 400
    assert invalid.data["code"] == "batch.effective_date_invalid"
    assert rejected.data["status"] == "rejected"
    assert rejected.data["review_note"] == "Região errada."


def test_batch_list_filters_by_status(analyst_client, reviewer_client):
    world = create_pricing_world()
    first = upload(analyst_client, world).data["id"]
    reviewer_client.post(batch_url(first, "/rejection"), {"reason": "x"}, format="json")
    upload(analyst_client, world, standard_prices(world, "1.05"))

    pending = analyst_client.get("/api/batches", {"status": "pending_review"}).data

    assert len(pending) == 1
    assert pending[0]["counts"]["plans"] == 2


def test_original_document_can_be_downloaded(analyst_client):
    world = create_pricing_world()
    document_id = upload(analyst_client, world).data["document"]["id"]

    response = analyst_client.get(f"/api/documents/{document_id}/file")

    assert response.status_code == 200
    assert response["Content-Type"] == "text/csv"
    assert b"Faixa et" in b"".join(response.streaming_content)


def test_review_payload_query_count_does_not_grow_with_plans(
    analyst_client, django_assert_max_num_queries
):
    world = create_pricing_world()
    prices = {f"Plano Extra {index}": standard_prices(world)[world.ward.name] for index in range(8)}
    batch_id = upload(analyst_client, world, prices).data["id"]

    with django_assert_max_num_queries(12):
        analyst_client.get(batch_url(batch_id))
