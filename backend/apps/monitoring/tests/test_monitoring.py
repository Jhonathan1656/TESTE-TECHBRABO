from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from apps.ans_reference.models import AnsDataset
from apps.ans_reference.services.sync_service import sync_ans_dataset
from apps.catalog.services.plan_catalog_service import deactivate_plan
from apps.catalog.tests.factories import create_operator, create_plan
from apps.ingestion.services import batch_review_service
from apps.ingestion.tests.builders import (
    REGION,
    create_pricing_world,
    receive_prices,
    standard_prices,
)
from apps.monitoring.models import AlertKind, AlertStatus, MonitoringAlert
from apps.monitoring.services.alert_service import (
    BrokerReportInput,
    register_broker_report,
    resolve_alert,
)
from apps.monitoring.services.dashboard_service import build_dashboard
from apps.monitoring.services.monitoring_service import run_monitoring_checks
from apps.sources.models import CheckOutcome
from apps.sources.services import FreshnessStatus, record_source_check
from apps.sources.tests.factories import create_source

pytestmark = pytest.mark.django_db

NOW = datetime(2026, 10, 16, 12, tzinfo=UTC)
ANS_FIXTURES = Path(__file__).resolve().parents[2] / "ans_reference" / "tests" / "fixtures"


def find_open_kinds() -> set[str]:
    return set(
        MonitoringAlert.objects.filter(status=AlertStatus.OPEN).values_list("kind", flat=True)
    )


def publish_old_table(world, reviewer_user):
    received_at = datetime(2025, 7, 20, 12, tzinfo=UTC)
    batch = receive_prices(world, date(2025, 8, 1), standard_prices(world), received_at=received_at)
    batch_review_service.approve_batch(batch, reviewer_user, now=received_at)


def test_stale_material_raises_alerts_that_close_when_the_source_is_confirmed(reviewer_user):
    world = create_pricing_world()
    publish_old_table(world, reviewer_user)

    run_monitoring_checks(now=NOW)
    assert find_open_kinds() == {AlertKind.SOURCE_OVERDUE, AlertKind.STALE_PRICE_TABLE}

    record_source_check(world.source, CheckOutcome.UNCHANGED, checked_at=NOW)
    summary = run_monitoring_checks(now=NOW + timedelta(minutes=5))

    assert summary.resolved == 1
    assert find_open_kinds() == {AlertKind.STALE_PRICE_TABLE}
    stale = MonitoringAlert.objects.get(kind=AlertKind.STALE_PRICE_TABLE)
    assert stale.params["months"] == 14
    assert stale.params["plans"] == 2
    assert stale.params["region"] == REGION


def test_rerunning_checks_refreshes_instead_of_duplicating(reviewer_user):
    world = create_pricing_world()
    publish_old_table(world, reviewer_user)

    run_monitoring_checks(now=NOW)
    summary = run_monitoring_checks(now=NOW + timedelta(hours=1))

    assert summary.opened == 0
    assert summary.refreshed == 2
    assert MonitoringAlert.objects.count() == 2


def test_failed_collection_after_last_success_is_reported():
    operator = create_operator()
    source = create_source(operator)
    record_source_check(source, CheckOutcome.UNCHANGED, checked_at=NOW - timedelta(days=2))
    record_source_check(
        source, CheckOutcome.FAILED, note="HTTP 503", checked_at=NOW - timedelta(days=1)
    )

    run_monitoring_checks(now=NOW)

    alert = MonitoringAlert.objects.get(kind=AlertKind.SOURCE_CHECK_FAILED)
    assert alert.params["note"] == "HTTP 503"


def test_plan_suspended_at_ans_alerts_until_removed_from_the_quoter(reviewer_user):
    sync_ans_dataset(
        AnsDataset.PLANS,
        str(ANS_FIXTURES / "pda-008-caracteristicas_produtos_saude_suplementar.csv"),
    )
    operator = create_operator(ans_registration="900011")
    suspended = create_plan(operator, name="Plano Teste Apartamento", ans_product_code="990102241")

    run_monitoring_checks(now=NOW)
    assert AlertKind.PLAN_NOT_ACTIVE_AT_ANS in find_open_kinds()

    deactivate_plan(suspended, reviewer_user)
    run_monitoring_checks(now=NOW + timedelta(minutes=1))

    assert AlertKind.PLAN_NOT_ACTIVE_AT_ANS not in find_open_kinds()


def test_broker_report_becomes_an_alert_that_can_be_resolved(analyst_user):
    world = create_pricing_world()

    report = register_broker_report(
        BrokerReportInput(
            plan=world.ward,
            region=REGION,
            quoted_on=NOW.date(),
            reported_value=Decimal("250.00"),
            message="A operadora recusou a proposta: valor da faixa 34-38 diferente.",
            reporter_name="Corretora Exemplo",
        ),
        actor=analyst_user,
    )

    alert = MonitoringAlert.objects.get(kind=AlertKind.BROKER_REPORT)
    assert alert.fingerprint == f"broker_report:{report.public_id}"
    resolve_alert(alert)
    assert find_open_kinds() == set()


def test_dashboard_reports_operator_health_and_confirmed_prices(reviewer_user):
    world = create_pricing_world()
    publish_old_table(world, reviewer_user)
    record_source_check(world.source, CheckOutcome.UNCHANGED, checked_at=NOW - timedelta(days=2))

    dashboard = build_dashboard(now=NOW)

    [health] = dashboard.operators
    assert health.status == FreshnessStatus.FRESH
    assert (health.active_plans, health.priced_plans) == (2, 2)
    assert health.oldest_effective_from == date(2025, 8, 1)
    assert (dashboard.priced_plans, dashboard.confirmed_plans) == (2, 2)
