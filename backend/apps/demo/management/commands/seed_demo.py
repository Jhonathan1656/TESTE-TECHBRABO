from django.core.management.base import BaseCommand

from apps.demo.services.seed_service import seed_demo


class Command(BaseCommand):
    help = "Seeds the fictional demo scenario (catalog, history, ANS data, alerts). Idempotent."

    def handle(self, *args, **options):
        summary = seed_demo()
        if not summary.created:
            self.stdout.write("Demo data already present; nothing to do.")
            return
        self.stdout.write(
            self.style.SUCCESS(
                f"Demo seeded: {summary.operators} operators, {summary.plans} plans, "
                f"{summary.published_batches} published batches, {summary.open_alerts} alerts."
            )
        )
