from django.core.management.base import BaseCommand

from apps.ans_reference.models import AnsDataset
from apps.ans_reference.services.sync_service import sync_ans_dataset
from apps.catalog.models import Operator


class Command(BaseCommand):
    help = (
        "Imports an ANS open-data dataset from the official portal (default) or a local file. "
        "Plans and price bands are limited to the operators in the catalog unless --all is given."
    )

    def add_arguments(self, parser):
        parser.add_argument("dataset", choices=[dataset.value for dataset in AnsDataset])
        parser.add_argument("--location", help="Local path or URL; defaults to the ANS portal.")
        parser.add_argument("--all", action="store_true", help="Import every operator's rows.")

    def handle(self, *args, dataset: str, location: str | None, all: bool, **options):
        registrations = None
        if not all and dataset != AnsDataset.OPERATORS:
            registrations = set(Operator.objects.values_list("ans_registration", flat=True))
        run = sync_ans_dataset(AnsDataset(dataset), location, registrations)
        self.stdout.write(
            self.style.SUCCESS(
                f"{dataset}: {run.rows_read} rows read, {run.rows_saved} saved from "
                f"{run.source_location}."
            )
        )
