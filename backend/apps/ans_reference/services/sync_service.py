from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from datetime import datetime
from itertools import islice

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

from apps.ans_reference.importers.dataset_reader import read_dataset_rows
from apps.ans_reference.importers.row_mappers import (
    map_operator_row,
    map_plan_row,
    map_price_band_row,
)
from apps.ans_reference.models import (
    AnsDataset,
    AnsOperatorRecord,
    AnsPlanRecord,
    AnsPriceBandRecord,
    AnsSyncRun,
    SyncStatus,
)
from apps.audit.models import AuditAction
from apps.audit.services import record_event

UPSERT_CHUNK_SIZE = 2000


def keep_latest_record(_previous: dict, latest: dict) -> dict:
    return latest


def widen_price_band(previous: dict, latest: dict) -> dict:
    # Regionalized notes can repeat a band; the widest range avoids false "outside band" alarms.
    return {
        **previous,
        "min_value": min(previous["min_value"], latest["min_value"]),
        "max_value": max(previous["max_value"], latest["max_value"]),
    }


@dataclass(frozen=True)
class DatasetSpec:
    path: str
    model: type[models.Model]
    map_row: Callable[[dict[str, str]], dict | None]
    unique_fields: tuple[str, ...]
    operator_field: str
    merge_duplicates: Callable[[dict, dict], dict] = keep_latest_record


DATASET_SPECS: dict[AnsDataset, DatasetSpec] = {
    AnsDataset.OPERATORS: DatasetSpec(
        path="operadoras_de_plano_de_saude_ativas/Relatorio_cadop.csv",
        model=AnsOperatorRecord,
        map_row=map_operator_row,
        unique_fields=("registration",),
        operator_field="registration",
    ),
    AnsDataset.PLANS: DatasetSpec(
        path="caracteristicas_produtos_saude_suplementar-008/"
        "pda-008-caracteristicas_produtos_saude_suplementar.csv",
        model=AnsPlanRecord,
        map_row=map_plan_row,
        unique_fields=("ans_plan_id",),
        operator_field="operator_registration",
    ),
    AnsDataset.PRICE_BANDS: DatasetSpec(
        path="nota_tecnica_ntrp_vcm_faixa_etaria/nota_tecnica_vcm_faixa_etaria.zip",
        model=AnsPriceBandRecord,
        map_row=map_price_band_row,
        unique_fields=("ans_plan_id", "note_code", "age_band"),
        operator_field="operator_registration",
        merge_duplicates=widen_price_band,
    ),
}


def list_recent_sync_runs(limit: int = 20) -> list[AnsSyncRun]:
    return list(AnsSyncRun.objects.order_by("-started_at")[:limit])


def build_default_location(dataset: AnsDataset) -> str:
    return f"{settings.ANS_OPEN_DATA_BASE_URL.rstrip('/')}/{DATASET_SPECS[dataset].path}"


def sync_ans_dataset(
    dataset: AnsDataset,
    location: str | None = None,
    operator_registrations: set[str] | None = None,
    now: datetime | None = None,
) -> AnsSyncRun:
    now = now or timezone.now()
    location = location or build_default_location(dataset)
    run = AnsSyncRun.objects.create(
        dataset=dataset, source_location=location, started_at=now, status=SyncStatus.RUNNING
    )
    try:
        rows_read, rows_saved = upsert_dataset(
            DATASET_SPECS[dataset], read_dataset_rows(location), operator_registrations, now
        )
    except Exception as error:
        mark_run_failed(run, error)
        raise
    run.status = SyncStatus.SUCCEEDED
    run.rows_read, run.rows_saved = rows_read, rows_saved
    run.finished_at = timezone.now()
    run.save(update_fields=["status", "rows_read", "rows_saved", "finished_at"])
    record_event(
        AuditAction.ANS_SYNCED,
        target=run,
        payload={"dataset": dataset, "rows_saved": rows_saved},
        occurred_at=now,
    )
    return run


def upsert_dataset(
    spec: DatasetSpec,
    rows: Iterable[dict[str, str]],
    operator_registrations: set[str] | None,
    synced_at: datetime,
) -> tuple[int, int]:
    counted_rows = _CountingIterator(rows)
    selected_records = (
        record
        for record in map(spec.map_row, counted_rows)
        if record is not None
        and (
            operator_registrations is None or record[spec.operator_field] in operator_registrations
        )
    )
    update_fields = [
        field.name
        for field in spec.model._meta.concrete_fields
        if not field.primary_key and field.name not in spec.unique_fields
    ]
    rows_saved = 0
    while chunk := list(islice(selected_records, UPSERT_CHUNK_SIZE)):
        instances = [
            spec.model(**record, synced_at=synced_at) for record in deduplicate_records(chunk, spec)
        ]
        with transaction.atomic():
            spec.model.objects.bulk_create(
                instances,
                update_conflicts=True,
                unique_fields=list(spec.unique_fields),
                update_fields=update_fields,
            )
        rows_saved += len(instances)
    return counted_rows.count, rows_saved


def deduplicate_records(records: list[dict], spec: DatasetSpec) -> list[dict]:
    merged: dict[tuple, dict] = {}
    for record in records:
        key = tuple(record[field] for field in spec.unique_fields)
        merged[key] = spec.merge_duplicates(merged[key], record) if key in merged else record
    return list(merged.values())


def mark_run_failed(run: AnsSyncRun, error: Exception) -> None:
    run.status = SyncStatus.FAILED
    run.error_message = f"{type(error).__name__}: {error}"[:500]
    run.finished_at = timezone.now()
    run.save(update_fields=["status", "error_message", "finished_at"])


class _CountingIterator:
    def __init__(self, rows: Iterable[dict[str, str]]):
        self._rows = iter(rows)
        self.count = 0

    def __iter__(self) -> Iterator[dict[str, str]]:
        for row in self._rows:
            self.count += 1
            yield row
