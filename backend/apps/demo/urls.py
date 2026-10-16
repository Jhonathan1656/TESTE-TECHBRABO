from django.urls import path

from apps.demo.views import DemoDeliveryCollectionView, DemoDeliveryFileView, DemoDeliveryListView

urlpatterns = [
    path("deliveries", DemoDeliveryListView.as_view(), name="demo-delivery-list"),
    path(
        "deliveries/<slug:key>/collection",
        DemoDeliveryCollectionView.as_view(),
        name="demo-delivery-collection",
    ),
    path("deliveries/<slug:key>/file", DemoDeliveryFileView.as_view(), name="demo-delivery-file"),
]
