from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.ingestion.services.collector_service import collect_file
from apps.ingestion.services.document_intake_service import SUPPORTED_EXTENSIONS, IncomingFile
from apps.sources.models import SourceChannel


class Command(BaseCommand):
    help = "Collects operator material dropped in a folder (stands in for an e-mail inbox)."

    def add_arguments(self, parser):
        parser.add_argument("folder", type=Path)
        parser.add_argument(
            "--channel",
            default=SourceChannel.EMAIL_INBOX,
            choices=[channel.value for channel in SourceChannel],
        )

    def handle(self, *args, folder: Path, channel: str, **options):
        if not folder.is_dir():
            raise CommandError(f"Folder not found: {folder}")
        files = sorted(
            path for path in folder.iterdir() if path.suffix.lower() in SUPPORTED_EXTENSIONS
        )
        for path in files:
            outcome = collect_file(IncomingFile(path.name, path.read_bytes()), channel)
            batch = (
                f" batch={outcome.batch.public_id} ({outcome.batch.status})"
                if outcome.batch
                else ""
            )
            self.stdout.write(f"{path.name}: {outcome.status}{batch}")
        self.stdout.write(self.style.SUCCESS(f"{len(files)} file(s) processed."))
