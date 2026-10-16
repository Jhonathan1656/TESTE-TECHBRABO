from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from django.utils import timezone

from apps.catalog.models import Operator
from apps.ingestion.extraction.document_content import read_document_bytes
from apps.ingestion.extraction.metadata_detector import detect_operator_registrations
from apps.ingestion.models import ImportBatch
from apps.ingestion.services.document_intake_service import (
    IncomingFile,
    detect_file_format,
    find_document_by_hash,
    receive_document,
)
from apps.sources.models import CheckOutcome, Source
from apps.sources.services import record_source_check


class CollectionStatus(StrEnum):
    RECEIVED = "received"
    UNCHANGED = "unchanged"
    UNIDENTIFIED = "unidentified"


@dataclass(frozen=True)
class CollectionOutcome:
    filename: str
    status: CollectionStatus
    batch: ImportBatch | None = None
    source: Source | None = None


def collect_file(
    incoming: IncomingFile, preferred_channel: str | None = None, now: datetime | None = None
) -> CollectionOutcome:
    """Entry point for automated collectors (inbox, portal crawler): no human picked the source."""
    now = now or timezone.now()
    existing = find_document_by_hash(incoming.content)
    if existing is not None:
        # Seeing the same file again is still evidence that the source is current.
        record_source_check(
            existing.source, CheckOutcome.UNCHANGED, document=existing, checked_at=now
        )
        latest_batch = existing.batches.order_by("-created_at").first()
        return CollectionOutcome(
            incoming.name, CollectionStatus.UNCHANGED, latest_batch, existing.source
        )
    operator = identify_operator(incoming)
    source = choose_source(operator, preferred_channel) if operator else None
    if source is None:
        return CollectionOutcome(incoming.name, CollectionStatus.UNIDENTIFIED)
    batch = receive_document(incoming, source, received_at=now, now=now)
    return CollectionOutcome(incoming.name, CollectionStatus.RECEIVED, batch, source)


def identify_operator(incoming: IncomingFile) -> Operator | None:
    content = read_document_bytes(incoming.content, detect_file_format(incoming.name))
    registrations = detect_operator_registrations(content.text)
    operators = list(Operator.objects.filter(ans_registration__in=registrations))
    return operators[0] if len(operators) == 1 else None


def choose_source(operator: Operator, preferred_channel: str | None) -> Source | None:
    sources = operator.sources.filter(is_active=True).order_by("-trust_level", "id")
    if preferred_channel:
        preferred = sources.filter(channel=preferred_channel).first()
        if preferred is not None:
            return preferred
    return sources.first()
