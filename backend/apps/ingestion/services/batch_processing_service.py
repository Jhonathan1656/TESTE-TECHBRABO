from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditAction
from apps.audit.services import record_event
from apps.catalog.services.plan_matching_service import load_plan_candidates, match_plan_label
from apps.core.domain.severity import Severity
from apps.ingestion.extraction.document_content import DocumentContent, read_document_content
from apps.ingestion.extraction.llm_extractor import build_llm_extractor
from apps.ingestion.extraction.metadata_detector import detect_metadata
from apps.ingestion.extraction.pipeline import extract_prices
from apps.ingestion.extraction.results import DocumentMetadata, ExtractedCell, ExtractionResult
from apps.ingestion.models import (
    BatchStatus,
    Document,
    ExtractedPlan,
    ExtractedPrice,
    ExtractionMethod,
    ImportBatch,
)
from apps.pricing.services.publication_service import publish_batch
from apps.quality.models import IssueStatus
from apps.quality.services.batch_validation_service import validate_batch

_MAX_RAW_TEXT = 120


@dataclass(frozen=True)
class BatchOverrides:
    effective_from: date | None = None
    effective_until: date | None = None
    region: str | None = None


def process_document(
    document: Document,
    overrides: BatchOverrides,
    content: DocumentContent | None = None,
    now: datetime | None = None,
) -> ImportBatch:
    now = now or timezone.now()
    content = content or read_document_content(Path(document.file.path), document.file_format)
    extraction = extract_prices(content, build_llm_extractor())
    metadata = merge_metadata(overrides, extraction.metadata, detect_metadata(content.text))
    with transaction.atomic():
        batch = create_batch(document, extraction, metadata, now)
        if extraction.succeeded:
            create_extracted_plans(batch, extraction.cells)
            validate_batch(batch, now=now)
        record_batch_outcome(batch, extraction, now)
    if batch.status == BatchStatus.PENDING_REVIEW:
        publish_automatically_if_allowed(batch, now)
    return batch


def merge_metadata(
    overrides: BatchOverrides, extracted: DocumentMetadata, detected: DocumentMetadata
) -> DocumentMetadata:
    """A reviewer's input wins, then what the AI read, then what the text patterns found."""
    return DocumentMetadata(
        effective_from=overrides.effective_from
        or extracted.effective_from
        or detected.effective_from,
        effective_until=overrides.effective_until
        or extracted.effective_until
        or detected.effective_until,
        region=overrides.region or extracted.region or detected.region,
    )


def create_batch(
    document: Document, extraction: ExtractionResult, metadata: DocumentMetadata, now: datetime
) -> ImportBatch:
    return ImportBatch.objects.create(
        document=document,
        operator=document.source.operator,
        status=BatchStatus.PENDING_REVIEW if extraction.succeeded else BatchStatus.FAILED,
        region=(metadata.region or "")[:80],
        effective_from=metadata.effective_from,
        effective_until=metadata.effective_until,
        extraction_method=extraction.method,
        extraction_details={**extraction.details, "failure_params": extraction.failure_params},
        failure_code=extraction.failure_code,
    )


def create_extracted_plans(batch: ImportBatch, cells: tuple[ExtractedCell, ...]) -> None:
    candidates = load_plan_candidates(batch.operator)
    labels = list(dict.fromkeys(cell.plan_label for cell in cells))
    extracted_plans = {}
    for position, label in enumerate(labels):
        match = match_plan_label(label, candidates)
        extracted_plans[label] = ExtractedPlan.objects.create(
            batch=batch,
            label=label[:200],
            position=position,
            plan_id=match.plan_id,
            match_method=match.method.value,
            match_score=match.score,
            suggestions=list(match.suggestions),
        )
    ExtractedPrice.objects.bulk_create(
        ExtractedPrice(
            extracted_plan=extracted_plans[cell.plan_label],
            age_band=cell.age_band,
            raw_text=cell.raw_text[:_MAX_RAW_TEXT],
            extracted_value=cell.value,
            location=cell.location,
        )
        for cell in cells
    )


def record_batch_outcome(batch: ImportBatch, extraction: ExtractionResult, now: datetime) -> None:
    if batch.status == BatchStatus.FAILED:
        record_event(
            AuditAction.BATCH_FAILED,
            operator=batch.operator,
            target=batch,
            payload={"failure_code": batch.failure_code, **extraction.failure_params},
            occurred_at=now,
        )
        return
    record_event(
        AuditAction.BATCH_CREATED,
        operator=batch.operator,
        target=batch,
        payload={
            "method": extraction.method,
            "plans": len(extraction.plan_labels),
            "prices": len(extraction.cells),
        },
        occurred_at=now,
    )


def publish_automatically_if_allowed(batch: ImportBatch, now: datetime) -> bool:
    """Level-1 automation: trusted sources publish without review when nothing needs attention."""
    if not batch.document.source.auto_approve or batch.extraction_method != ExtractionMethod.GRID:
        return False
    needs_attention = batch.issues.filter(
        status=IssueStatus.OPEN, severity__in=[Severity.ERROR, Severity.WARNING]
    ).exists()
    if needs_attention:
        return False
    publish_batch(batch, actor=None, now=now, automatic=True)
    batch.refresh_from_db()
    return True
