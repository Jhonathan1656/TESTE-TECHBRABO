from collections.abc import Iterator

from apps.core.domain.age_bands import AgeBand
from apps.core.domain.severity import Severity
from apps.quality.rules.formatting import to_money_param
from apps.quality.rules.snapshot import BatchSnapshot, Finding


def check_missing_bands(batch: BatchSnapshot) -> Iterator[Finding]:
    for plan in batch.plans:
        missing = [int(band) for band in AgeBand if band not in plan.raw_texts]
        if missing:
            yield Finding(
                "structure.missing_band",
                Severity.ERROR,
                plan.label,
                params={"plan": plan.display_name, "bands": missing},
            )


def check_unparseable_values(batch: BatchSnapshot) -> Iterator[Finding]:
    for plan in batch.plans:
        for band, raw_text in sorted(plan.raw_texts.items()):
            if plan.values.get(band) is None:
                yield Finding(
                    "structure.unparseable_value",
                    Severity.ERROR,
                    plan.label,
                    band,
                    params={"plan": plan.display_name, "band": int(band), "raw": raw_text},
                )


def check_non_positive_values(batch: BatchSnapshot) -> Iterator[Finding]:
    for plan in batch.plans:
        for band, value in plan.priced_bands().items():
            if value <= 0:
                yield Finding(
                    "structure.non_positive_value",
                    Severity.ERROR,
                    plan.label,
                    band,
                    params={
                        "plan": plan.display_name,
                        "band": int(band),
                        "value_brl": to_money_param(value),
                    },
                )


def check_conflicting_tables(batch: BatchSnapshot) -> Iterator[Finding]:
    if batch.conflicting_duplicates:
        yield Finding(
            "structure.conflicting_tables",
            Severity.WARNING,
            params={"count": batch.conflicting_duplicates},
        )
