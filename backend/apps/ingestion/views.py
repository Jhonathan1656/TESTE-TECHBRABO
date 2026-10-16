from django.http import FileResponse
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.services.plan_catalog_service import find_plan
from apps.core.permissions import IsAnalyst, IsReviewer
from apps.ingestion.models import CONTENT_TYPES_BY_FORMAT, ImportBatch
from apps.ingestion.serializers import (
    BatchDetailResponseSerializer,
    BatchListQuerySerializer,
    BatchSummaryResponseSerializer,
    DocumentUploadRequestSerializer,
    EffectiveDatesRequestSerializer,
    IssueAcknowledgementRequestSerializer,
    PlanExclusionRequestSerializer,
    PlanMappingRequestSerializer,
    PriceCorrectionRequestSerializer,
    PublicationRequestSerializer,
    RejectionRequestSerializer,
)
from apps.ingestion.services import batch_review_service
from apps.ingestion.services.batch_processing_service import BatchOverrides
from apps.ingestion.services.batch_query_service import (
    find_batch,
    find_document,
    find_extracted_plan,
    find_extracted_price,
    find_issue,
    list_batch_timeline,
    list_batches,
    list_mapping_candidates,
    load_batch_detail,
)
from apps.ingestion.services.document_intake_service import IncomingFile, receive_document
from apps.sources.services import find_source


def build_batch_detail_payload(batch: ImportBatch) -> dict:
    detailed = load_batch_detail(batch.public_id)
    context = {
        "timeline": list_batch_timeline(detailed),
        "plan_candidates": list_mapping_candidates(detailed),
    }
    return BatchDetailResponseSerializer(detailed, context=context).data


class DocumentUploadView(APIView):
    permission_classes = [IsAnalyst]
    parser_classes = [MultiPartParser]

    def post(self, request):
        payload = DocumentUploadRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        upload = data["file"]
        batch = receive_document(
            IncomingFile(upload.name, upload.read()),
            find_source(data["source"]),
            uploaded_by=request.user,
            overrides=BatchOverrides(
                effective_from=data.get("effective_from"),
                effective_until=data.get("effective_until"),
                region=data.get("region") or None,
            ),
        )
        return Response(build_batch_detail_payload(batch), status=status.HTTP_201_CREATED)


class DocumentFileView(APIView):
    def get(self, request, document_id):
        document = find_document(document_id)
        return FileResponse(
            document.file.open("rb"),
            filename=document.original_filename,
            content_type=CONTENT_TYPES_BY_FORMAT[document.file_format],
        )


class BatchListView(APIView):
    def get(self, request):
        query = BatchListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        batches = list_batches(
            status=query.validated_data.get("status"),
            operator_id=query.validated_data.get("operator"),
        )
        return Response(BatchSummaryResponseSerializer(batches, many=True).data)


class BatchDetailView(APIView):
    def get(self, request, batch_id):
        return Response(build_batch_detail_payload(find_batch(batch_id)))


class PriceCorrectionView(APIView):
    permission_classes = [IsAnalyst]

    def patch(self, request, batch_id, price_id):
        payload = PriceCorrectionRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        batch = find_batch(batch_id)
        # Omitted field keeps the stored correction; an explicit null clears it.
        if "corrected_value" in payload.validated_data:
            price = find_extracted_price(batch, price_id)
            batch_review_service.correct_price(
                price, payload.validated_data["corrected_value"], request.user
            )
        return Response(build_batch_detail_payload(batch))


class PlanMappingView(APIView):
    permission_classes = [IsAnalyst]

    def post(self, request, batch_id, extracted_plan_id):
        payload = PlanMappingRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        batch = find_batch(batch_id)
        extracted = find_extracted_plan(batch, extracted_plan_id)
        batch_review_service.map_extracted_plan(
            extracted, find_plan(payload.validated_data["plan"]), request.user
        )
        return Response(build_batch_detail_payload(batch))


class PlanExclusionView(APIView):
    permission_classes = [IsAnalyst]

    def post(self, request, batch_id, extracted_plan_id):
        payload = PlanExclusionRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        batch = find_batch(batch_id)
        extracted = find_extracted_plan(batch, extracted_plan_id)
        batch_review_service.set_plan_exclusion(
            extracted, payload.validated_data["excluded"], request.user
        )
        return Response(build_batch_detail_payload(batch))


class IssueAcknowledgementView(APIView):
    permission_classes = [IsAnalyst]

    def post(self, request, batch_id, issue_id):
        payload = IssueAcknowledgementRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        batch = find_batch(batch_id)
        batch_review_service.acknowledge_issue(
            find_issue(batch, issue_id), payload.validated_data["note"], request.user
        )
        return Response(build_batch_detail_payload(batch))


class EffectiveDatesView(APIView):
    permission_classes = [IsAnalyst]

    def put(self, request, batch_id):
        payload = EffectiveDatesRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        batch = find_batch(batch_id)
        batch_review_service.update_effective_dates(
            batch, batch_review_service.EffectiveDates(**payload.validated_data), request.user
        )
        return Response(build_batch_detail_payload(batch))


class PublicationView(APIView):
    permission_classes = [IsReviewer]

    def post(self, request, batch_id):
        payload = PublicationRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        batch = find_batch(batch_id)
        batch_review_service.approve_batch(batch, request.user, note=payload.validated_data["note"])
        return Response(build_batch_detail_payload(batch))


class RejectionView(APIView):
    permission_classes = [IsReviewer]

    def post(self, request, batch_id):
        payload = RejectionRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        batch = find_batch(batch_id)
        batch_review_service.reject_batch(batch, payload.validated_data["reason"], request.user)
        return Response(build_batch_detail_payload(batch))


class ReprocessingView(APIView):
    permission_classes = [IsAnalyst]

    def post(self, request, batch_id):
        new_batch = batch_review_service.reprocess_failed_batch(find_batch(batch_id))
        return Response(build_batch_detail_payload(new_batch), status=status.HTTP_201_CREATED)
