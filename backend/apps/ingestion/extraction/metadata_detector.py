import re
import unicodedata
from datetime import date, datetime

from apps.ingestion.extraction.results import DocumentMetadata

_DATE = r"(\d{2}/\d{2}/\d{4})"
# Document vocabulary (pt-BR): "Vigência: 01/11/2026 a 31/10/2027", "a partir de 01/12/2026".
_EFFECTIVE_PERIOD = re.compile(
    r"vigencia\D{0,40}?" + _DATE + r"(?:\s*(?:a|ate|-|–)\s*" + _DATE + r")?"
)
_EFFECTIVE_START = re.compile(
    r"(?:a partir de|valid[oa]s?\s+(?:a partir\s+)?de|vigentes?\s+(?:a partir\s+)?de)\s*" + _DATE
)
_REGION_PREFIX = re.compile(r"^\s*regiao(?:\s+de\s+comercializacao)?\s*[:\-–]")
_REGION_SEPARATOR = re.compile(r"\s*[:\-–]\s*")
_REGION_TERMINATORS = ("|", "  ")
_ANS_REGISTRATION = re.compile(r"(?:registro|reg\.?)\s*(?:na\s+)?ans\D{0,12}(\d{6})\b")


def detect_metadata(text: str) -> DocumentMetadata:
    folded = fold_text(text)
    effective_from, effective_until = detect_effective_period(folded)
    return DocumentMetadata(
        effective_from=effective_from,
        effective_until=effective_until,
        region=detect_region(text),
    )


def detect_effective_period(folded_text: str) -> tuple[date | None, date | None]:
    period = _EFFECTIVE_PERIOD.search(folded_text)
    if period:
        return parse_brazilian_date(period.group(1)), parse_brazilian_date(period.group(2))
    start = _EFFECTIVE_START.search(folded_text)
    if start:
        return parse_brazilian_date(start.group(1)), None
    return None, None


def detect_region(text: str) -> str | None:
    for line in text.splitlines():
        if not _REGION_PREFIX.match(fold_text(line)):
            continue
        region = _REGION_SEPARATOR.split(line, maxsplit=1)[1]
        for terminator in _REGION_TERMINATORS:
            region = region.split(terminator)[0]
        return region.strip() or None
    return None


def detect_operator_registrations(text: str) -> set[str]:
    return set(_ANS_REGISTRATION.findall(fold_text(text)))


def fold_text(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text or "")
    return "".join(char for char in decomposed if not unicodedata.combining(char)).lower()


def parse_brazilian_date(text: str | None) -> date | None:
    if not text:
        return None
    try:
        return datetime.strptime(text, "%d/%m/%Y").date()
    except ValueError:
        return None
