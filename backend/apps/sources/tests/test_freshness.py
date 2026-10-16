from datetime import UTC, datetime, timedelta

import pytest

from apps.audit.models import AuditAction, AuditEvent
from apps.catalog.tests.factories import create_operator
from apps.sources.models import CheckOutcome
from apps.sources.services import (
    FreshnessStatus,
    evaluate_freshness,
    find_sources_with_freshness,
    record_source_check,
)
from apps.sources.tests.factories import create_source

NOW = datetime(2026, 10, 16, 12, tzinfo=UTC)


@pytest.mark.parametrize(
    ("days_ago", "expected"),
    [
        (0, FreshnessStatus.FRESH),
        (30, FreshnessStatus.FRESH),
        (31, FreshnessStatus.DUE),
        (37, FreshnessStatus.DUE),
        (38, FreshnessStatus.OVERDUE),
    ],
)
def test_evaluate_freshness_uses_cadence_and_tolerance(days_ago, expected):
    last_success = NOW - timedelta(days=days_ago)

    assert evaluate_freshness(last_success, 30, 7, NOW) == expected


def test_evaluate_freshness_reports_never_checked():
    assert evaluate_freshness(None, 30, 7, NOW) == FreshnessStatus.NEVER_CHECKED


@pytest.mark.django_db
def test_failed_checks_do_not_refresh_a_source(analyst_user):
    source = create_source(create_operator())
    record_source_check(source, CheckOutcome.UNCHANGED, checked_at=NOW - timedelta(days=40))
    record_source_check(
        source, CheckOutcome.FAILED, note="timeout", checked_at=NOW - timedelta(days=1)
    )

    [freshness] = find_sources_with_freshness(now=NOW)

    assert freshness.status == FreshnessStatus.OVERDUE
    assert freshness.days_since_success == 40
    assert freshness.last_failure_at == NOW - timedelta(days=1)


@pytest.mark.django_db
def test_confirming_unchanged_material_keeps_source_fresh(analyst_user):
    source = create_source(create_operator())
    record_source_check(
        source, CheckOutcome.UNCHANGED, actor=analyst_user, checked_at=NOW - timedelta(days=3)
    )

    [freshness] = find_sources_with_freshness(now=NOW)

    assert freshness.status == FreshnessStatus.FRESH
    assert freshness.last_new_material_at is None
    event = AuditEvent.objects.get()
    assert event.action == AuditAction.SOURCE_CHECKED
    assert event.actor == analyst_user
