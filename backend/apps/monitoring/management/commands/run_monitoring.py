from django.core.management.base import BaseCommand

from apps.monitoring.services.monitoring_service import run_monitoring_checks


class Command(BaseCommand):
    help = (
        "Runs freshness and ANS status checks, opening and resolving alerts. Meant for a scheduler."
    )

    def handle(self, *args, **options):
        summary = run_monitoring_checks()
        self.stdout.write(
            self.style.SUCCESS(
                f"Alerts opened: {summary.opened}, refreshed: {summary.refreshed}, "
                f"resolved: {summary.resolved}."
            )
        )
