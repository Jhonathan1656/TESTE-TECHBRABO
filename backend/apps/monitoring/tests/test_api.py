import pytest
from django.test import override_settings

from apps.demo.services.seed_service import seed_demo
from apps.ingestion.tests.builders import REGION, create_pricing_world

pytestmark = pytest.mark.django_db


def test_dashboard_aggregates_the_seeded_scenario(analyst_client):
    seed_demo()

    response = analyst_client.get("/api/dashboard")

    assert response.status_code == 200
    body = response.data
    assert (body["active_plans"], body["priced_plans"]) == (11, 11)
    assert body["confirmed_plans"] == 8
    statuses = {item["operator"]["name"]: item["status"] for item in body["operators"]}
    assert statuses["CoopSaúde Litoral"] == "overdue"
    assert body["alerts"][0]["severity"] == "error"
    assert "Suspenso" in body["alerts"][0]["message"]
    assert body["recent_events"]


def test_monitoring_run_and_alert_resolution(analyst_client):
    seed_demo()
    alert_id = analyst_client.get("/api/alerts").data[0]["id"]

    run = analyst_client.post("/api/monitoring/runs")
    resolved = analyst_client.post(f"/api/alerts/{alert_id}/resolution")

    assert run.status_code == 201
    assert resolved.data["status"] == "resolved"
    assert (
        analyst_client.post(f"/api/alerts/{alert_id}/resolution").data["code"] == "alert.not_open"
    )


def test_broker_report_is_accepted_from_any_authenticated_user(analyst_client):
    world = create_pricing_world()

    response = analyst_client.post(
        "/api/broker-reports",
        {
            "plan": str(world.ward.public_id),
            "region": REGION,
            "quoted_on": "2026-10-16",
            "reported_value": "250.00",
            "message": "Valor diferente do portal.",
            "reporter_name": "Corretora Exemplo",
        },
        format="json",
    )

    assert response.status_code == 201
    [alert] = analyst_client.get("/api/alerts").data
    assert alert["kind"] == "broker_report"
    assert "Valor diferente do portal." in alert["message"]


@override_settings(DEMO_MODE=False)
def test_demo_endpoints_disappear_when_demo_mode_is_off(analyst_client):
    response = analyst_client.get("/api/demo/deliveries")

    assert response.status_code == 404
    assert response.data["code"] == "demo.disabled"


def test_demo_delivery_can_be_collected_and_downloaded(analyst_client):
    seed_demo()

    listed = analyst_client.get("/api/demo/deliveries").data
    collected = analyst_client.post("/api/demo/deliveries/vida_plena_update/collection")
    downloaded = analyst_client.get("/api/demo/deliveries/horizonte_update/file")

    assert listed[0]["key"] == "vida_plena_update"
    assert collected.status_code == 201
    assert collected.data["status"] == "received"
    assert collected.data["batch"]["status"] == "pending_review"
    assert downloaded["Content-Type"].startswith("application/vnd.openxmlformats")
    assert analyst_client.get("/api/demo/deliveries/unknown/file").status_code == 404
