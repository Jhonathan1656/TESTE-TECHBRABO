from collections.abc import Iterator

from apps.core.domain.severity import Severity
from apps.quality.rules.snapshot import BatchSnapshot, Finding

SIMILARITY_MATCH = "similarity"


def check_unmatched_plans(batch: BatchSnapshot) -> Iterator[Finding]:
    for plan in batch.plans:
        if not plan.is_matched:
            yield Finding(
                "catalog.unmatched_plan",
                Severity.ERROR,
                plan.label,
                params={"label": plan.label, "suggestions": ", ".join(plan.suggestions)},
            )


def check_similarity_matches(batch: BatchSnapshot) -> Iterator[Finding]:
    for plan in batch.plans:
        if plan.is_matched and plan.match_method == SIMILARITY_MATCH:
            yield Finding(
                "catalog.similarity_match",
                Severity.WARNING,
                plan.label,
                params={
                    "label": plan.label,
                    "plan": plan.plan_name,
                    "score": str(round((plan.match_score or 0) * 100)),
                },
            )


def check_plans_without_history(batch: BatchSnapshot) -> Iterator[Finding]:
    for plan in batch.plans:
        if plan.is_matched and not plan.previous_values and plan.current_effective_from is None:
            yield Finding(
                "catalog.no_previous_table",
                Severity.INFO,
                plan.label,
                params={"plan": plan.display_name},
            )


def check_missing_plans(batch: BatchSnapshot) -> Iterator[Finding]:
    for missing in batch.missing_plans:
        yield Finding(
            "catalog.plan_missing_from_document",
            Severity.WARNING,
            discriminator=str(missing.plan_id),
            params={
                "plan": missing.plan_name,
                "effective_from_date": missing.effective_from.isoformat(),
            },
        )
