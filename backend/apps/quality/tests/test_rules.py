from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from apps.core.domain.age_bands import AgeBand
from apps.core.domain.severity import Severity
from apps.quality.rules.registry import run_rules
from apps.quality.rules.snapshot import MissingPlan, RegisteredBand
from apps.quality.tests.builders import EFFECTIVE_FROM, build_batch, build_plan, with_values


def find_codes(findings) -> list[str]:
    return [finding.rule_code for finding in findings]


def find_one(findings, code: str):
    matches = [finding for finding in findings if finding.rule_code == code]
    assert len(matches) == 1, f"expected one {code}, got {find_codes(findings)}"
    return matches[0]


def test_clean_uniform_adjustment_produces_no_findings():
    batch = build_batch(
        build_plan("Superior Enfermaria"), build_plan("Superior Apartamento", base="240", plan_id=2)
    )

    assert run_rules(batch) == []


class TestRn63:
    def test_last_band_above_six_times_first_is_an_error(self):
        plan = with_values(build_plan(), {AgeBand.BAND_59_PLUS: Decimal("1400.00")})

        finding = find_one(run_rules(build_batch(plan)), "rn63.last_band_ratio")

        assert finding.severity == Severity.ERROR
        assert finding.age_band == AgeBand.BAND_59_PLUS
        assert finding.params["ratio"] == "6.38"

    def test_late_accumulated_variation_above_early_variation_is_an_error(self):
        values = {
            AgeBand.BAND_44_48: Decimal("360.00"),
            AgeBand.BAND_49_53: Decimal("400.00"),
            AgeBand.BAND_54_58: Decimal("700.00"),
            AgeBand.BAND_59_PLUS: Decimal("1100.00"),
        }
        plan = with_values(build_plan(with_history=False), values)

        finding = find_one(run_rules(build_batch(plan)), "rn63.accumulated_variation")

        assert finding.params["early_pct"] == "63.93"
        assert finding.params["late_pct"] == "205.56"

    def test_cheaper_older_band_is_a_negative_variation_error(self):
        plan = with_values(build_plan(), {AgeBand.BAND_34_38: Decimal("300.00")})

        finding = find_one(run_rules(build_batch(plan)), "rn63.negative_variation")

        assert finding.age_band == AgeBand.BAND_34_38
        assert finding.params["previous_band"] == int(AgeBand.BAND_29_33)


class TestConsistency:
    def test_subtle_typo_breaks_uniform_adjustment(self):
        plan = with_values(build_plan(), {AgeBand.BAND_44_48: Decimal("580.00")})

        findings = run_rules(build_batch(plan))

        finding = find_one(findings, "consistency.non_uniform_adjustment")
        assert finding.age_band == AgeBand.BAND_44_48
        assert finding.params["median_change_pct"] == "9.80"
        assert "consistency.large_variation" not in find_codes(findings)

    def test_uniform_large_adjustment_is_reported_once_per_plan(self):
        plan = build_plan(adjustment="1.32")

        findings = run_rules(build_batch(plan))

        assert find_codes(findings) == ["consistency.large_adjustment"]
        assert findings[0].params["change_pct"] == "32.00"

    def test_isolated_large_variation_is_reported_per_band(self):
        plan = with_values(build_plan(), {AgeBand.BAND_54_58: Decimal("1010.00")})

        findings = run_rules(build_batch(plan))

        finding = find_one(findings, "consistency.large_variation")
        assert finding.age_band == AgeBand.BAND_54_58
        assert finding.params["change_pct"] == "26.88"

    def test_decimal_shift_against_previous_table_is_an_error_without_noise(self):
        plan = with_values(build_plan(), {AgeBand.BAND_54_58: Decimal("8740.00")})

        findings = run_rules(build_batch(plan))

        finding = find_one(findings, "consistency.decimal_shift")
        assert finding.params["factor"] == "10"
        assert "consistency.non_uniform_adjustment" not in find_codes(findings)
        assert "consistency.large_variation" not in find_codes(findings)

    def test_decimal_shift_without_history_uses_neighbor_bands(self):
        plan = with_values(build_plan(with_history=False), {AgeBand.BAND_24_28: Decimal("30.53")})

        finding = find_one(run_rules(build_batch(plan)), "consistency.decimal_shift")

        assert finding.params["factor"] == "1/10"

    def test_ward_more_expensive_than_private_room_suggests_swapped_columns(self):
        ward = build_plan("Superior Enfermaria", base="260")
        room = build_plan("Superior Apartamento", base="240", plan_id=2)

        finding = find_one(run_rules(build_batch(ward, room)), "consistency.expected_price_order")

        assert finding.plan_label == "Superior Enfermaria"
        assert finding.params["bands"] == list(range(1, 11))


class TestCatalogAndStructure:
    def test_unmatched_plan_is_an_error_with_suggestions(self):
        plan = build_plan("Ouro Max", plan_id=None, suggestions=("Ouro Plus",), with_history=False)

        finding = find_one(run_rules(build_batch(plan)), "catalog.unmatched_plan")

        assert finding.params == {"label": "Ouro Max", "suggestions": "Ouro Plus"}

    def test_similarity_match_must_be_confirmed(self):
        plan = build_plan(match_method="similarity", match_score=0.92)

        finding = find_one(run_rules(build_batch(plan)), "catalog.similarity_match")

        assert finding.severity == Severity.WARNING
        assert finding.params["score"] == "92"

    def test_missing_and_unparseable_bands_are_errors(self):
        plan = build_plan(with_history=False)
        values = {
            band: value for band, value in plan.values.items() if band != AgeBand.BAND_59_PLUS
        }
        raw_texts = {
            band: text for band, text in plan.raw_texts.items() if band != AgeBand.BAND_59_PLUS
        }
        values[AgeBand.BAND_19_23] = None
        raw_texts[AgeBand.BAND_19_23] = "2O3,OO"
        plan = replace(plan, values=values, raw_texts=raw_texts)

        findings = run_rules(build_batch(plan))

        assert find_one(findings, "structure.missing_band").params["bands"] == [10]
        assert find_one(findings, "structure.unparseable_value").params["raw"] == "2O3,OO"

    def test_plan_with_current_table_absent_from_document_is_a_warning(self):
        missing = MissingPlan(
            plan_id=7, plan_name="Premium Apartamento", effective_from=date(2026, 5, 1)
        )

        finding = find_one(
            run_rules(build_batch(build_plan(), missing_plans=(missing,))),
            "catalog.plan_missing_from_document",
        )

        assert finding.discriminator == "7"
        assert finding.plan_label == ""

    def test_new_plan_without_history_is_informational(self):
        finding = find_one(
            run_rules(build_batch(build_plan(with_history=False))), "catalog.no_previous_table"
        )

        assert finding.severity == Severity.INFO


class TestAnsReference:
    def test_suspended_plan_cannot_be_published(self):
        plan = build_plan(
            ans_status="suspended", ans_status_label="Suspenso", ans_status_date=date(2026, 8, 14)
        )

        finding = find_one(run_rules(build_batch(plan)), "ans.plan_not_active")

        assert finding.severity == Severity.ERROR
        assert finding.params["status"] == "Suspenso"

    def test_value_outside_registered_note_band_is_a_warning(self):
        bands = {AgeBand.BAND_00_18: RegisteredBand(Decimal("150.00"), Decimal("210.00"))}
        plan = build_plan(registered_bands=bands)

        finding = find_one(run_rules(build_batch(plan)), "ans.outside_registered_band")

        assert finding.params["value_brl"] == "219.60"
        assert finding.params["max_brl"] == "210.00"


class TestValidity:
    def test_missing_effective_date_blocks_publication(self):
        finding = find_one(
            run_rules(build_batch(build_plan(), effective_from=None)),
            "validity.missing_effective_date",
        )

        assert finding.severity == Severity.ERROR

    @pytest.mark.parametrize(
        ("current", "code"),
        [
            (EFFECTIVE_FROM, "validity.same_effective_date"),
            (date(2027, 1, 1), "validity.earlier_than_current"),
        ],
    )
    def test_effective_date_not_after_current_table_needs_confirmation(self, current, code):
        plan = build_plan(current_effective_from=current)

        assert find_one(run_rules(build_batch(plan)), code).severity == Severity.WARNING

    def test_late_capture_and_scheduled_start_are_informational(self):
        late = find_one(
            run_rules(build_batch(build_plan(), today=date(2026, 11, 20))), "validity.late_capture"
        )
        scheduled = find_one(
            run_rules(build_batch(build_plan(), today=date(2026, 10, 16))), "validity.scheduled"
        )

        assert late.params["days"] == 19
        assert scheduled.severity == Severity.INFO


class TestAiExtraction:
    def test_ai_values_must_appear_verbatim_in_the_document(self):
        plan = build_plan(with_history=False)
        anchored_text = " ".join(
            plan.raw_texts[band] for band in AgeBand if band != AgeBand.BAND_29_33
        )
        batch = build_batch(
            plan,
            extraction_method="llm",
            extraction_model="test-model",
            document_text=anchored_text,
        )

        findings = run_rules(batch)

        assert find_one(findings, "extraction.ai_extracted").params == {"model": "test-model"}
        assert find_one(findings, "extraction.value_not_anchored").age_band == AgeBand.BAND_29_33


def test_fingerprint_is_stable_and_specific():
    plan = with_values(build_plan(), {AgeBand.BAND_34_38: Decimal("300.00")})
    first = find_one(run_rules(build_batch(plan)), "rn63.negative_variation")
    second = find_one(run_rules(build_batch(plan)), "rn63.negative_variation")

    assert (
        first.fingerprint == second.fingerprint == "rn63.negative_variation|Essencial Enfermaria|5|"
    )
