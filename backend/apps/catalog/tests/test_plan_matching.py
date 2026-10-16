import pytest

from apps.catalog.models import AliasOrigin, PlanAlias
from apps.catalog.services.plan_matching_service import (
    MatchMethod,
    PlanCandidate,
    learn_plan_alias,
    load_plan_candidates,
    match_plan_label,
    normalize_plan_label,
)
from apps.catalog.tests.factories import create_operator, create_plan

CANDIDATES = [
    PlanCandidate(1, "Horizonte 100 Enfermaria", ("horizonte 100 enfermaria",)),
    PlanCandidate(2, "Horizonte 200 Apartamento", ("horizonte 200 apartamento",)),
    PlanCandidate(3, "Horizonte 300 Apartamento", ("horizonte 300 apartamento",)),
    PlanCandidate(4, "Essencial Enfermaria", ("essencial enfermaria com copart",)),
]


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("Premium Apto.", "premium apartamento"),
        ("Superior Enf", "superior enfermaria"),
        ("Essencial QC c/ Copart.", "essencial enfermaria com copart"),
        ("Linha Ouro - Quarto Privativo", "linha ouro apartamento"),
        ("Plano Coparticipativo", "plano copart"),
    ],
)
def test_normalize_plan_label_expands_market_abbreviations(label, expected):
    assert normalize_plan_label(label) == expected


def test_match_plan_label_finds_exact_alias():
    match = match_plan_label("Essencial Enf. c/ Coparticipação", CANDIDATES)

    assert match.plan_id == 4
    assert match.method == MatchMethod.ALIAS
    assert match.score == 1.0


def test_match_plan_label_uses_similarity_when_label_has_extra_words():
    match = match_plan_label("Horizonte 300 Apto Nacional", CANDIDATES)

    assert match.plan_id == 3
    assert match.method == MatchMethod.SIMILARITY
    assert match.score >= 0.85


def test_match_plan_label_never_crosses_plan_tiers_with_different_numbers():
    match = match_plan_label("Horizonte 400 Apartamento", CANDIDATES)

    assert match.plan_id is None
    assert match.method == MatchMethod.UNMATCHED


def test_match_plan_label_suggests_closest_names_when_unmatched():
    match = match_plan_label("Plano Ouro Max", CANDIDATES)

    assert match.method == MatchMethod.UNMATCHED
    assert len(match.suggestions) <= 3


@pytest.mark.django_db
def test_load_plan_candidates_includes_learned_aliases(reviewer_user):
    operator = create_operator()
    plan = create_plan(operator, name="Superior Apartamento")
    learn_plan_alias(operator, plan, "Sup. Apto Top", reviewer_user)

    candidates = load_plan_candidates(operator)

    assert candidates[0].normalized_keys == ("superior apartamento", "sup apartamento top")
    alias = PlanAlias.objects.get()
    assert alias.origin == AliasOrigin.REVIEW
    assert alias.created_by == reviewer_user


@pytest.mark.django_db
def test_learn_plan_alias_repoints_existing_alias(reviewer_user):
    operator = create_operator()
    wrong_plan = create_plan(operator, name="Superior Enfermaria")
    right_plan = create_plan(operator, name="Superior Apartamento")
    learn_plan_alias(operator, wrong_plan, "Superior QP", reviewer_user)

    learn_plan_alias(operator, right_plan, "Superior QP", reviewer_user)

    assert PlanAlias.objects.get().plan == right_plan
