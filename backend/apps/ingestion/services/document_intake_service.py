import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditAction
from apps.audit.services import record_event
from apps.core.exceptions import ConflictError, DomainError
from apps.ingestion.extraction.document_content import (
    DocumentContent,
    UnreadableDocumentError,
    read_document_bytes,
)
from apps.ingestion.models import Document, DocumentFormat, ImportBatch
from apps.ingestion.services.batch_processing_service import BatchOverrides, process_document
from apps.sources.models import CheckOutcome, Source
from apps.sources.services import record_source_check

SUPPORTED_EXTENSIONS = {
    ".pdf": DocumentFormat.PDF,
    ".xlsx": DocumentFormat.XLSX,
    ".csv": DocumentFormat.CSV,
}
_BYTES_PER_MEGABYTE = 1024 * 1024


@dataclass(frozen=True)
class IncomingFile:
    name: str
    content: bytes


def receive_document(
    incoming: IncomingFile,
    source: Source,
    *,
    uploaded_by=None,
    overrides: BatchOverrides | None = None,
    received_at: datetime | None = None,
    now: datetime | None = None,
) -> ImportBatch:
    """Stores a new operator material, records the source check and runs it through the pipeline."""
    received_at = received_at or timezone.now()
    if not source.is_active:
        raise DomainError("document.source_inactive")
    document, content = store_document(incoming, source, uploaded_by, received_at)
    record_source_check(
        source,
        CheckOutcome.NEW_MATERIAL,
        document=document,
        actor=uploaded_by,
        checked_at=received_at,
    )
    record_event(
        AuditAction.DOCUMENT_RECEIVED,
        actor=uploaded_by,
        operator=source.operator,
        target=document,
        payload={"filename": document.original_filename, "source": source.name},
        occurred_at=received_at,
    )
    return process_document(document, overrides or BatchOverrides(), content=content, now=now)


def store_document(
    incoming: IncomingFile, source: Source, uploaded_by, received_at: datetime
) -> tuple[Document, DocumentContent]:
    file_format = detect_file_format(incoming.name)
    ensure_size_within_limit(incoming.content)
    sha256 = hashlib.sha256(incoming.content).hexdigest()
    ensure_not_received_before(sha256)
    content = read_incoming_content(incoming, file_format)
    document = Document(
        source=source,
        original_filename=Path(incoming.name).name[:255],
        file_format=file_format,
        size_bytes=len(incoming.content),
        sha256=sha256,
        text_content=content.text,
        received_at=received_at,
        uploaded_by=uploaded_by
        if uploaded_by is not None and uploaded_by.is_authenticated
        else None,
    )
    document.file.save(incoming.name, ContentFile(incoming.content), save=False)
    with transaction.atomic():
        document.save()
    return document, content


def read_incoming_content(incoming: IncomingFile, file_format: DocumentFormat) -> DocumentContent:
    try:
        return read_document_bytes(incoming.content, file_format)
    except UnreadableDocumentError as error:
        raise DomainError("document.unreadable") from error


def detect_file_format(filename: str) -> DocumentFormat:
    file_format = SUPPORTED_EXTENSIONS.get(Path(filename).suffix.lower())
    if file_format is None:
        raise DomainError("document.unsupported_type")
    return file_format


def ensure_size_within_limit(content: bytes) -> None:
    if len(content) > settings.MAX_DOCUMENT_BYTES:
        raise DomainError(
            "document.too_large", {"limit_mb": settings.MAX_DOCUMENT_BYTES // _BYTES_PER_MEGABYTE}
        )


def ensure_not_received_before(sha256: str) -> None:
    existing = Document.objects.select_related("source").filter(sha256=sha256).first()
    if existing is None:
        return
    latest_batch = existing.batches.order_by("-created_at").first()
    raise ConflictError(
        "document.duplicate",
        {
            "received_at_date": timezone.localtime(existing.received_at).date(),
            "source": existing.source.name,
            "document": existing.public_id,
            "batch": latest_batch.public_id if latest_batch else None,
        },
    )


def find_document_by_hash(content: bytes) -> Document | None:
    return Document.objects.filter(sha256=hashlib.sha256(content).hexdigest()).first()
