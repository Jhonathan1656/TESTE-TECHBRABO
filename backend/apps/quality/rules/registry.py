from collections.abc import Callable, Iterator

from apps.quality.rules import (
    catalog_rules,
    consistency_rules,
    extraction_rules,
    regulatory_rules,
    structure_rules,
    validity_rules,
)
from apps.quality.rules.snapshot import BatchSnapshot, Finding

Rule = Callable[[BatchSnapshot], Iterator[Finding]]

ALL_RULES: tuple[Rule, ...] = (
    validity_rules.check_missing_effective_date,
    catalog_rules.check_unmatched_plans,
    catalog_rules.check_similarity_matches,
    structure_rules.check_missing_bands,
    structure_rules.check_unparseable_values,
    structure_rules.check_non_positive_values,
    structure_rules.check_conflicting_tables,
    extraction_rules.check_value_anchoring,
    extraction_rules.check_ai_extraction,
    regulatory_rules.check_ans_plan_status,
    regulatory_rules.check_rn63_last_band_ratio,
    regulatory_rules.check_rn63_accumulated_variation,
    regulatory_rules.check_rn63_negative_variation,
    consistency_rules.check_decimal_shift,
    regulatory_rules.check_ans_registered_band,
    consistency_rules.check_non_uniform_adjustment,
    consistency_rules.check_large_variation,
    consistency_rules.check_expected_price_order,
    catalog_rules.check_missing_plans,
    validity_rules.check_effective_date_against_current,
    catalog_rules.check_plans_without_history,
    validity_rules.check_late_capture,
    validity_rules.check_scheduled_start,
)


def run_rules(batch: BatchSnapshot, rules: tuple[Rule, ...] = ALL_RULES) -> list[Finding]:
    return [finding for rule in rules for finding in rule(batch)]
