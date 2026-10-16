from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command

from apps.ans_reference.models import AnsPlanRecord
from apps.catalog.tests.factories import create_operator
from apps.monitoring.models import AlertKind, MonitoringAlert
from apps.sources.tests.factories import create_source

FIXTURES = Path(__file__).parent / "fixtures"

pytestmark = pytest.mark.django_db


def test_import_command_limits_plans_to_catalog_operators():
    create_operator(ans_registration="900022")
    output = StringIO()

    call_command(
        "import_ans_reference",
        "plans",
        "--location",
        str(FIXTURES / "pda-008-caracteristicas_produtos_saude_suplementar.csv"),
        stdout=output,
    )

    assert list(AnsPlanRecord.objects.values_list("operator_registration", flat=True)) == ["900022"]
    assert "1 saved" in output.getvalue()


def test_run_monitoring_command_opens_alerts():
    create_source(create_operator())

    call_command("run_monitoring", stdout=StringIO())

    assert MonitoringAlert.objects.filter(kind=AlertKind.SOURCE_NEVER_CHECKED).exists()
