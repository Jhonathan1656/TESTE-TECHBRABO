from django.contrib import admin
from django.urls import include, path

api_patterns = [
    path("", include("apps.core.urls")),
    path("", include("apps.catalog.urls")),
    path("", include("apps.sources.urls")),
    path("", include("apps.ingestion.urls")),
    path("", include("apps.pricing.urls")),
    path("", include("apps.monitoring.urls")),
    path("", include("apps.ans_reference.urls")),
    path("", include("apps.audit.urls")),
    path("demo/", include("apps.demo.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(api_patterns)),
]
