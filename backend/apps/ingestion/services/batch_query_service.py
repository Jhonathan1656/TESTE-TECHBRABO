from uuid import UUID

from django.db.models import Count, Prefetch, Q, QuerySet

from apps.audit.models import AuditEvent
from apps.catalog.models import Plan
from apps.core.domain.severity import Severity
from apps.core.exceptions import NotFoundError
from apps.ingestion.models import Document, ExtractedPlan, ExtractedPrice, ImportBatch
from apps.quality.models import IssueStatus, ValidationIssue

_SUMMARY_RELATIONS = ("operator", "document__source", "document__uploaded_by", "reviewed_by")
DEFAULT_LIST_LIMIT = 100


def annotate_issue_counts(batches: QuerySet) -> QuerySet:
    open_issues = Q(issues__status=IssueStatus.OPEN)
    return batches.annotate(
        plan_count=Count("extracted_plans", distinct=True),
        open_errors=Count(
            "issues", filter=open_issues & Q(issues__severity=Severity.ERROR), distinct=True
        ),
        open_warnings=Count(
            "issues", filter=open_issues & Q(issues__severity=Severity.WARNING), distinct=True
        ),
    )


def list_batches(
    status: str | None = None, operator_id: UUID | None = None, limit: int = DEFAULT_LIST_LIMIT
) -> list[ImportBatch]:
    batches = annotate_issue_counts(ImportBatch.objects.select_related(*_SUMMARY_RELATIONS))
    if status:
        batches = batches.filter(status=status)
    if operator_id:
        batches = batches.filter(operator__public_id=operator_id)
    return list(batches.order_by("-created_at")[:limit])


def find_batch(batch_id: UUID) -> ImportBatch:
    batch = ImportBatch.objects.filter(public_id=batch_id).first()
    if batch is None:
        raise NotFoundError("resource.not_found")
    return batch


def load_batch_detail(batch_id: UUID) -> ImportBatch:
    prices = ExtractedPrice.objects.select_related("corrected_by").order_by("age_band")
    extracted_plans = (
        ExtractedPlan.objects.select_related("plan")
        .prefetch_related(Prefetch("prices", queryset=prices))
        .order_by("position")
    )
    issues = ValidationIssue.objects.select_related("acknowledged_by", "extracted_plan")
    batch = (
        annotate_issue_counts(ImportBatch.objects.select_related(*_SUMMARY_RELATIONS))
        .prefetch_related(
            Prefetch("extracted_plans", queryset=extracted_plans),
            Prefetch("issues", queryset=issues),
        )
        .filter(public_id=batch_id)
        .first()
    )
    if batch is None:
        raise NotFoundError("resource.not_found")
    return batch


def list_batch_timeline(batch: ImportBatch) -> list[AuditEvent]:
    targets = [batch.public_id, batch.document.public_id]
    return list(
        AuditEvent.objects.filter(target_public_id__in=targets)
        .select_related("actor")
        .order_by("occurred_at", "id")
    )


def list_mapping_candidates(batch: ImportBatch) -> list[Plan]:
    return list(Plan.objects.filter(operator=batch.operator, is_active=True).order_by("name"))


def find_extracted_price(batch: ImportBatch, price_id: UUID) -> ExtractedPrice:
    price = (
        ExtractedPrice.objects.select_related("extracted_plan")
        .filter(public_id=price_id, extracted_plan__batch=batch)
        .first()
    )
    if price is None:
        raise NotFoundError("resource.not_found")
    return price


def find_extracted_plan(batch: ImportBatch, extracted_plan_id: UUID) -> ExtractedPlan:
    extracted = ExtractedPlan.objects.filter(public_id=extracted_plan_id, batch=batch).first()
    if extracted is None:
        raise NotFoundError("resource.not_found")
    return extracted


def find_issue(batch: ImportBatch, issue_id: UUID) -> ValidationIssue:
    issue = ValidationIssue.objects.filter(public_id=issue_id, batch=batch).first()
    if issue is None:
        raise NotFoundError("resource.not_found")
    return issue


def find_document(document_id: UUID) -> Document:
    document = Document.objects.filter(public_id=document_id).first()
    if document is None:
        raise NotFoundError("resource.not_found")
    return document
