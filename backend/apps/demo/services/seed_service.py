import tempfile
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.utils import timezone

from apps.ans_reference.services.sync_service import sync_ans_dataset
from apps.catalog.models import Operator, Plan
from apps.core.roles import ROLE_GROUP_NAMES, Role
from apps.demo.scenario import (
    HISTORY_STAGE,
    build_delivery_file,
    calculate_effective_from,
    list_deliveries,
    load_scenario,
)
from apps.demo.services.ans_sample_service import write_ans_samples
from apps.ingestion.models import BatchStatus, ImportBatch
from apps.ingestion.services.batch_review_service import approve_batch
from apps.ingestion.services.document_intake_service import IncomingFile, receive_document
from apps.monitoring.services.monitoring_service import run_monitoring_checks
from apps.sources.models import CheckOutcome, Source
from apps.sources.services import record_source_check


class DemoScenarioError(Exception):
    pass


@dataclass
class DemoCatalog:
    operators: dict[str, Operator] = field(default_factory=dict)
    sources: dict[tuple[str, str], Source] = field(default_factory=dict)
    plans: dict[tuple[str, str], Plan] = field(default_factory=dict)


@dataclass(frozen=True)
class SeedSummary:
    created: bool
    operators: int = 0
    plans: int = 0
    published_batches: int = 0
    open_alerts: int = 0


def is_demo_seeded() -> bool:
    registrations = [operator["ans_registration"] for operator in load_scenario()["operators"]]
    return Operator.objects.filter(ans_registration__in=registrations).exists()


def seed_demo(today: date | None = None) -> SeedSummary:
    if is_demo_seeded():
        return SeedSummary(created=False)
    if not settings.DEMO_PASSWORD:
        raise ImproperlyConfigured("DEMO_PASSWORD must be set to create the demo users.")
    today = today or timezone.localdate()
    scenario = load_scenario()
    with transaction.atomic():
        users = create_demo_users(scenario["users"], settings.DEMO_PASSWORD)
        catalog = create_demo_catalog(scenario["operators"])
        receipts = {
            delivery["key"]: ingest_history_delivery(delivery, today, catalog, users)
            for delivery in list_deliveries(HISTORY_STAGE)
        }
        sync_demo_ans_reference(scenario, today)
        record_demo_source_history(scenario["source_history"], today, catalog, users, receipts)
        monitoring = run_monitoring_checks()
    return SeedSummary(
        created=True,
        operators=len(catalog.operators),
        plans=len(catalog.plans),
        published_batches=len(receipts),
        open_alerts=monitoring.opened,
    )


def create_demo_users(user_specs: list[dict], password: str) -> dict[str, User]:
    users = {}
    for spec in user_specs:
        user = User.objects.create_user(
            username=spec["username"],
            password=password,
            first_name=spec["first_name"],
            last_name=spec["last_name"],
        )
        group, _ = Group.objects.get_or_create(name=ROLE_GROUP_NAMES[Role(spec["role"])])
        user.groups.add(group)
        users[spec["username"]] = user
    return users


def create_demo_catalog(operator_specs: list[dict]) -> DemoCatalog:
    catalog = DemoCatalog()
    for spec in operator_specs:
        operator = Operator.objects.create(
            name=spec["name"],
            ans_registration=spec["ans_registration"],
            cnpj=spec["cnpj"],
            modality=spec["modality"],
            access_level=spec["access_level"],
            is_fictional=True,
        )
        catalog.operators[spec["key"]] = operator
        for source_spec in spec["sources"]:
            catalog.sources[(spec["key"], source_spec["key"])] = Source.objects.create(
                operator=operator,
                name=source_spec["name"],
                channel=source_spec["channel"],
                trust_level=source_spec["trust_level"],
                expected_update_days=source_spec["expected_update_days"],
                tolerance_days=source_spec["tolerance_days"],
                contact=source_spec["contact"],
                auto_approve=source_spec["auto_approve"],
            )
        for plan_spec in spec["plans"]:
            catalog.plans[(spec["key"], plan_spec["key"])] = Plan.objects.create(
                operator=operator,
                name=plan_spec["name"],
                product_line=plan_spec["product_line"],
                ans_product_code=plan_spec["ans_product_code"],
                contract_type=plan_spec["contract_type"],
                accommodation=plan_spec["accommodation"],
                coverage_area=plan_spec["coverage_area"],
                segmentation=plan_spec["segmentation"],
                has_coparticipation=plan_spec["has_coparticipation"],
            )
    return catalog


def ingest_history_delivery(
    delivery: dict, today: date, catalog: DemoCatalog, users: dict[str, User]
) -> datetime:
    """Replays a past delivery at its original moment so audit and history stay coherent."""
    effective_from = calculate_effective_from(delivery, today)
    received_at = at_local_time(
        effective_from - timedelta(days=delivery["received_days_before_effective"]), 10
    )
    generated = build_delivery_file(delivery, today)
    batch = receive_document(
        IncomingFile(generated.name, generated.content),
        catalog.sources[(delivery["operator"], delivery["source"])],
        uploaded_by=users.get(delivery.get("uploaded_by", "")),
        received_at=received_at,
        now=received_at,
    )
    review = delivery.get("review")
    if review and batch.status == BatchStatus.PENDING_REVIEW:
        reviewed_at = received_at + timedelta(days=review["days_after_receipt"], hours=4)
        approve_batch(batch, users[review["user"]], note=review["note"], now=reviewed_at)
    ensure_published(batch, delivery["key"])
    return received_at


def ensure_published(batch: ImportBatch, delivery_key: str) -> None:
    batch.refresh_from_db()
    if batch.status != BatchStatus.PUBLISHED:
        open_rules = list(batch.issues.filter(status="open").values_list("rule_code", flat=True))
        raise DemoScenarioError(f"History delivery {delivery_key} was not published: {open_rules}")


def sync_demo_ans_reference(scenario: dict, today: date) -> None:
    synced_at = at_local_time(today - timedelta(days=1), 6)
    with tempfile.TemporaryDirectory() as folder:
        for dataset, path in write_ans_samples(scenario, today, Path(folder)).items():
            sync_ans_dataset(dataset, str(path), now=synced_at)


def record_demo_source_history(
    history: list[dict],
    today: date,
    catalog: DemoCatalog,
    users: dict[str, User],
    receipts: dict[str, datetime],
) -> None:
    first_receipt = min(receipts.values())
    for entry in history:
        source = catalog.sources[(entry["operator"], entry["source"])]
        if entry["kind"] == "collector_unchanged":
            record_collector_routine(source, entry["every_days"], first_receipt.date(), today)
            continue
        outcome = CheckOutcome.FAILED if entry["kind"] == "failed" else CheckOutcome.UNCHANGED
        record_source_check(
            source,
            outcome,
            note=entry.get("note", ""),
            actor=users.get(entry.get("user", "")),
            checked_at=at_local_time(today - timedelta(days=entry["days_ago"]), 8),
        )


def record_collector_routine(source: Source, every_days: int, since: date, today: date) -> None:
    last_receipt = source.checks.order_by("-checked_at").first()
    day = (last_receipt.checked_at.date() if last_receipt else since) + timedelta(days=every_days)
    while day < today - timedelta(days=3):
        record_source_check(source, CheckOutcome.UNCHANGED, checked_at=at_local_time(day, 8))
        day += timedelta(days=every_days)


def at_local_time(day: date, hour: int) -> datetime:
    return timezone.make_aware(datetime.combine(day, time(hour)))
