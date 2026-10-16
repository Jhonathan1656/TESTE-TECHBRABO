from collections.abc import Iterator

from apps.core.domain.severity import Severity
from apps.quality.rules.snapshot import BatchSnapshot, Finding

LLM_EXTRACTION = "llm"


def check_ai_extraction(batch: BatchSnapshot) -> Iterator[Finding]:
    if batch.extraction_method == LLM_EXTRACTION:
        yield Finding(
            "extraction.ai_extracted", Severity.WARNING, params={"model": batch.extraction_model}
        )


def check_value_anchoring(batch: BatchSnapshot) -> Iterator[Finding]:
    """AI output is trusted only if every value can be found verbatim in the document text."""
    if batch.extraction_method != LLM_EXTRACTION:
        return
    document = compact_text(batch.document_text)
    for plan in batch.plans:
        for band, raw_text in sorted(plan.raw_texts.items()):
            if compact_text(raw_text) not in document:
                yield Finding(
                    "extraction.value_not_anchored",
                    Severity.ERROR,
                    plan.label,
                    band,
                    params={"plan": plan.display_name, "band": int(band), "raw": raw_text},
                )


def compact_text(text: str) -> str:
    return "".join(text.split()).lower()
