import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from enum import StrEnum

from apps.catalog.models import AliasOrigin, Operator, Plan, PlanAlias
from apps.core.domain.text import normalize_text

# Market vocabulary seen in operator tables (pt-BR): QC/QP = quarto coletivo/privativo, etc.
_PHRASE_SYNONYMS = (
    ("quarto coletivo", "enfermaria"),
    ("quarto privativo", "apartamento"),
    ("quarto individual", "apartamento"),
)
_TOKEN_SYNONYMS = {
    "enf": "enfermaria",
    "apto": "apartamento",
    "apt": "apartamento",
    "ap": "apartamento",
    "qc": "enfermaria",
    "qp": "apartamento",
    "coparticipacao": "copart",
    "coparticipativo": "copart",
    "c": "com",
    "s": "sem",
    "nac": "nacional",
}
# Labels that disagree on any of these groups never refer to the same plan.
_EXCLUSIVE_TOKEN_GROUPS = ({"enfermaria", "apartamento"},)
_NUMBER = re.compile(r"\d+")

SIMILARITY_THRESHOLD = 0.85
SIMILARITY_MARGIN = 0.05
SUGGESTION_THRESHOLD = 0.5
CONFLICT_SCORE_CAP = 0.5
MAX_SUGGESTIONS = 3


class MatchMethod(StrEnum):
    ALIAS = "alias"
    SIMILARITY = "similarity"
    UNMATCHED = "unmatched"


@dataclass(frozen=True)
class PlanCandidate:
    plan_id: int
    name: str
    normalized_keys: tuple[str, ...]


@dataclass(frozen=True)
class PlanMatch:
    plan_id: int | None
    method: MatchMethod
    score: float | None
    suggestions: tuple[str, ...] = field(default_factory=tuple)


def normalize_plan_label(label: str) -> str:
    normalized = normalize_text(label)
    for phrase, replacement in _PHRASE_SYNONYMS:
        normalized = normalized.replace(phrase, replacement)
    return " ".join(_TOKEN_SYNONYMS.get(token, token) for token in normalized.split())


def match_plan_label(label: str, candidates: Sequence[PlanCandidate]) -> PlanMatch:
    key = normalize_plan_label(label)
    for candidate in candidates:
        if key in candidate.normalized_keys:
            return PlanMatch(candidate.plan_id, MatchMethod.ALIAS, 1.0)

    ranked = rank_candidates(key, candidates)
    suggestions = tuple(
        candidate.name
        for score, candidate in ranked[:MAX_SUGGESTIONS]
        if score >= SUGGESTION_THRESHOLD
    )
    if not ranked:
        return PlanMatch(None, MatchMethod.UNMATCHED, None, suggestions)

    best_score, best = ranked[0]
    runner_up_score = ranked[1][0] if len(ranked) > 1 else 0.0
    if best_score >= SIMILARITY_THRESHOLD and best_score - runner_up_score >= SIMILARITY_MARGIN:
        return PlanMatch(best.plan_id, MatchMethod.SIMILARITY, round(best_score, 3), suggestions)
    return PlanMatch(None, MatchMethod.UNMATCHED, round(best_score, 3), suggestions)


def rank_candidates(
    key: str, candidates: Sequence[PlanCandidate]
) -> list[tuple[float, PlanCandidate]]:
    scored = [
        (max(score_label_similarity(key, other) for other in candidate.normalized_keys), candidate)
        for candidate in candidates
        if candidate.normalized_keys
    ]
    return sorted(scored, key=lambda item: item[0], reverse=True)


def score_label_similarity(left: str, right: str) -> float:
    left_tokens, right_tokens = set(left.split()), set(right.split())
    if _have_conflicting_tokens(left_tokens, right_tokens):
        return min(_blend_scores(left_tokens, right_tokens), CONFLICT_SCORE_CAP)
    return _blend_scores(left_tokens, right_tokens)


def load_plan_candidates(operator: Operator) -> list[PlanCandidate]:
    plans = operator.plans.filter(is_active=True).prefetch_related("aliases").order_by("id")
    return [
        PlanCandidate(
            plan_id=plan.id,
            name=plan.name,
            normalized_keys=(
                normalize_plan_label(plan.name),
                *(alias.normalized_label for alias in sorted(plan.aliases.all(), key=_by_id)),
            ),
        )
        for plan in plans
    ]


def learn_plan_alias(operator: Operator, plan: Plan, label: str, actor) -> PlanAlias:
    alias, _ = PlanAlias.objects.update_or_create(
        operator=operator,
        normalized_label=normalize_plan_label(label),
        defaults={"plan": plan, "origin": AliasOrigin.REVIEW, "created_by": actor},
    )
    return alias


def _blend_scores(left_tokens: set[str], right_tokens: set[str]) -> float:
    return (
        _token_set_ratio(left_tokens, right_tokens) + _token_sort_ratio(left_tokens, right_tokens)
    ) / 2


def _token_sort_ratio(left_tokens: set[str], right_tokens: set[str]) -> float:
    return SequenceMatcher(
        None, " ".join(sorted(left_tokens)), " ".join(sorted(right_tokens))
    ).ratio()


def _token_set_ratio(left_tokens: set[str], right_tokens: set[str]) -> float:
    shared = " ".join(sorted(left_tokens & right_tokens))
    left_full = f"{shared} {' '.join(sorted(left_tokens - right_tokens))}".strip()
    right_full = f"{shared} {' '.join(sorted(right_tokens - left_tokens))}".strip()
    return max(
        SequenceMatcher(None, shared, left_full).ratio(),
        SequenceMatcher(None, shared, right_full).ratio(),
        SequenceMatcher(None, left_full, right_full).ratio(),
    )


def _have_conflicting_tokens(left_tokens: set[str], right_tokens: set[str]) -> bool:
    if _numbers_in(left_tokens) != _numbers_in(right_tokens):
        return True
    return any(
        (left_tokens & group)
        and (right_tokens & group)
        and (left_tokens & group) != (right_tokens & group)
        for group in _EXCLUSIVE_TOKEN_GROUPS
    )


def _numbers_in(tokens: set[str]) -> set[str]:
    return {token for token in tokens if _NUMBER.fullmatch(token)}


def _by_id(alias: PlanAlias) -> int:
    return alias.id
