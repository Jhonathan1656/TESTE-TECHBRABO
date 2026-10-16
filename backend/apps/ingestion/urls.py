from django.urls import path

from apps.ingestion import views

batch_route = "batches/<uuid:batch_id>"
plan_route = f"{batch_route}/plans/<uuid:extracted_plan_id>"

urlpatterns = [
    path("documents", views.DocumentUploadView.as_view(), name="document-upload"),
    path(
        "documents/<uuid:document_id>/file", views.DocumentFileView.as_view(), name="document-file"
    ),
    path("batches", views.BatchListView.as_view(), name="batch-list"),
    path(batch_route, views.BatchDetailView.as_view(), name="batch-detail"),
    path(
        f"{batch_route}/prices/<uuid:price_id>",
        views.PriceCorrectionView.as_view(),
        name="batch-price-correction",
    ),
    path(f"{plan_route}/mapping", views.PlanMappingView.as_view(), name="batch-plan-mapping"),
    path(f"{plan_route}/exclusion", views.PlanExclusionView.as_view(), name="batch-plan-exclusion"),
    path(
        f"{batch_route}/issues/<uuid:issue_id>/acknowledgement",
        views.IssueAcknowledgementView.as_view(),
        name="batch-issue-acknowledgement",
    ),
    path(f"{batch_route}/effective-dates", views.EffectiveDatesView.as_view(), name="batch-dates"),
    path(f"{batch_route}/publication", views.PublicationView.as_view(), name="batch-publication"),
    path(f"{batch_route}/rejection", views.RejectionView.as_view(), name="batch-rejection"),
    path(
        f"{batch_route}/reprocessing", views.ReprocessingView.as_view(), name="batch-reprocessing"
    ),
]
