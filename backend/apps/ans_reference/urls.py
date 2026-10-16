from django.urls import path

from apps.ans_reference.views import AnsSyncRunListView

urlpatterns = [
    path("ans/sync-runs", AnsSyncRunListView.as_view(), name="ans-sync-runs"),
]
