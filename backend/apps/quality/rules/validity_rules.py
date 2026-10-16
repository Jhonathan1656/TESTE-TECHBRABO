from collections.abc import Iterator

from apps.core.domain.severity import Severity
from apps.quality.rules.snapshot import BatchSnapshot, Finding


def check_missing_effective_date(batch: BatchSnapshot) -> Iterator[Finding]:
    if batch.effective_from is None:
        yield Finding("validity.missing_effective_date", Severity.ERROR)


def check_effective_date_against_current(batch: BatchSnapshot) -> Iterator[Finding]:
    if batch.effective_from is None:
        return
    for plan in batch.plans:
        current = plan.current_effective_from
        if not plan.is_matched or current is None:
            continue
        if batch.effective_from == current:
            yield Finding(
                "validity.same_effective_date",
                Severity.WARNING,
                plan.label,
                params={
                    "plan": plan.display_name,
                    "effective_from_date": batch.effective_from.isoformat(),
                },
            )
        elif batch.effective_from < current:
            yield Finding(
                "validity.earlier_than_current",
                Severity.WARNING,
                plan.label,
                params={
                    "plan": plan.display_name,
                    "effective_from_date": batch.effective_from.isoformat(),
                    "current_effective_from_date": current.isoformat(),
                },
            )


def check_late_capture(batch: BatchSnapshot) -> Iterator[Finding]:
    if batch.effective_from is None:
        return
    delay_days = (batch.today - batch.effective_from).days
    if delay_days >= batch.thresholds.late_capture_days:
        yield Finding(
            "validity.late_capture",
            Severity.INFO,
            params={"effective_from_date": batch.effective_from.isoformat(), "days": delay_days},
        )


def check_scheduled_start(batch: BatchSnapshot) -> Iterator[Finding]:
    if batch.effective_from is not None and batch.effective_from > batch.today:
        yield Finding(
            "validity.scheduled",
            Severity.INFO,
            params={"effective_from_date": batch.effective_from.isoformat()},
        )
