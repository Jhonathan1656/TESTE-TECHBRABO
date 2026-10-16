from django.urls import path

from apps.sources.views import SourceCheckListView, SourceConfirmationView, SourceListView

urlpatterns = [
    path("sources", SourceListView.as_view(), name="source-list"),
    path("sources/<uuid:source_id>/checks", SourceCheckListView.as_view(), name="source-checks"),
    path(
        "sources/<uuid:source_id>/confirmations",
        SourceConfirmationView.as_view(),
        name="source-confirmation",
    ),
]
