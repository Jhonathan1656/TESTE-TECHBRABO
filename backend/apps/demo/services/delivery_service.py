from dataclasses import dataclass
from datetime import date, datetime

from django.conf import settings
from django.utils import timezone

from apps.catalog.models import Operator
from apps.core.exceptions import NotFoundError
from apps.demo.scenario import (
    DEMO_STAGE,
    build_delivery_file,
    build_delivery_filename,
    find_delivery,
    find_operator_spec,
    list_deliveries,
)
from apps.ingestion.models import BatchStatus, Document, ImportBatch
from apps.ingestion.services.collector_service import CollectionOutcome, collect_file
from apps.ingestion.services.document_intake_service import IncomingFile

RESEND_LAYOUT = "resend"


@dataclass(frozen=True)
class DemoDelivery:
    key: str
    title: str
    description: str
    operator_name: str
    channel: str
    layout: str
    filename: str
    latest_batch: ImportBatch | None


def ensure_demo_mode() -> None:
    if not settings.DEMO_MODE:
        raise NotFoundError("demo.disabled")


def list_demo_deliveries(today: date | None = None) -> list[DemoDelivery]:
    today = today or timezone.localdate()
    deliveries = []
    for delivery in list_deliveries(DEMO_STAGE):
        is_resend = delivery["layout"] == RESEND_LAYOUT
        filename = "" if is_resend else build_delivery_filename(delivery, today)
        document = (
            None
            if is_resend
            else Document.objects.filter(original_filename=filename)
            .order_by("-received_at")
            .first()
        )
        deliveries.append(
            DemoDelivery(
                key=delivery["key"],
                title=delivery["title_for_demo"],
                description=delivery["description_for_demo"],
                operator_name=find_operator_spec(delivery["operator"])["name"],
                channel=delivery["channel"],
                layout=delivery["layout"],
                filename=filename,
                latest_batch=document.batches.order_by("-created_at").first() if document else None,
            )
        )
    return deliveries


def collect_demo_delivery(
    key: str, today: date | None = None, now: datetime | None = None
) -> CollectionOutcome:
    delivery = require_demo_delivery(key)
    incoming = build_demo_file(delivery, today or timezone.localdate())
    return collect_file(incoming, delivery["channel"], now=now)


def build_demo_file(delivery: dict, today: date) -> IncomingFile:
    if delivery["layout"] == RESEND_LAYOUT:
        return find_published_original(delivery)
    generated = build_delivery_file(delivery, today)
    return IncomingFile(generated.name, generated.content)


def find_published_original(delivery: dict) -> IncomingFile:
    original = find_delivery(delivery["resend_of"])
    operator = Operator.objects.get(
        ans_registration=find_operator_spec(original["operator"])["ans_registration"]
    )
    document = (
        Document.objects.filter(source__operator=operator, batches__status=BatchStatus.PUBLISHED)
        .order_by("-received_at")
        .first()
    )
    if document is None:
        raise NotFoundError("demo.resend_unavailable")
    with document.file.open("rb") as stored:
        return IncomingFile(document.original_filename, stored.read())


def require_demo_delivery(key: str) -> dict:
    delivery = find_delivery(key)
    if delivery is None or delivery["stage"] != DEMO_STAGE:
        raise NotFoundError("demo.delivery_not_found")
    return delivery
