import re
from enum import IntEnum

from apps.core.domain.text import normalize_text


class AgeBand(IntEnum):
    # The ten age bands mandated by ANS RN 63/2003, art. 2.
    BAND_00_18 = 1
    BAND_19_23 = 2
    BAND_24_28 = 3
    BAND_29_33 = 4
    BAND_34_38 = 5
    BAND_39_43 = 6
    BAND_44_48 = 7
    BAND_49_53 = 8
    BAND_54_58 = 9
    BAND_59_PLUS = 10

    @property
    def min_age(self) -> int:
        return AGE_BAND_BOUNDS[self][0]

    @property
    def max_age(self) -> int | None:
        return AGE_BAND_BOUNDS[self][1]

    @property
    def label(self) -> str:
        if self.max_age is None:
            return f"{self.min_age}+"
        return f"{self.min_age}–{self.max_age}"


AGE_BAND_BOUNDS: dict[AgeBand, tuple[int, int | None]] = {
    AgeBand.BAND_00_18: (0, 18),
    AgeBand.BAND_19_23: (19, 23),
    AgeBand.BAND_24_28: (24, 28),
    AgeBand.BAND_29_33: (29, 33),
    AgeBand.BAND_34_38: (34, 38),
    AgeBand.BAND_39_43: (39, 43),
    AgeBand.BAND_44_48: (44, 48),
    AgeBand.BAND_49_53: (49, 53),
    AgeBand.BAND_54_58: (54, 58),
    AgeBand.BAND_59_PLUS: (59, None),
}

AGE_BAND_CHOICES = [(band.value, band.label) for band in AgeBand]

_MONEY_LIKE = re.compile(r"\d[.,]\d{2}(?!\d)")
_NUMBER = re.compile(r"\d+")
# Document vocabulary (pt-BR) that marks "up to 18" and "59 or older" labels.
_UP_TO_MARKERS = {"ate"}
_OPEN_ENDED_MARKERS = ("mais", "acima", "partir", "diante", "superior")
_OPEN_ENDED_SYMBOLS = ("+", ">", "≥")
_MAX_LABEL_LENGTH = 40


def find_band_for_age(age: int) -> AgeBand:
    if age < 0:
        raise ValueError(f"Age must be non-negative, got {age}")
    for band, (lower, upper) in AGE_BAND_BOUNDS.items():
        if age >= lower and (upper is None or age <= upper):
            return band
    raise ValueError(f"No age band for age {age}")


def parse_age_band(text: str | None) -> AgeBand | None:
    if not text or _MONEY_LIKE.search(text):
        return None
    normalized = normalize_text(text)
    if not normalized or len(normalized) > _MAX_LABEL_LENGTH:
        return None
    numbers = [int(number) for number in _NUMBER.findall(normalized)]
    if len(numbers) == 2:
        return find_band_by_bounds(numbers[0], numbers[1])
    if numbers == [18] and _UP_TO_MARKERS & set(normalized.split()):
        return AgeBand.BAND_00_18
    if numbers == [59] and _has_open_ended_marker(text, normalized):
        return AgeBand.BAND_59_PLUS
    return None


def find_band_by_bounds(lower: int, upper: int) -> AgeBand | None:
    for band, bounds in AGE_BAND_BOUNDS.items():
        if bounds == (lower, upper):
            return band
    return None


def _has_open_ended_marker(raw_text: str, normalized: str) -> bool:
    return any(marker in normalized for marker in _OPEN_ENDED_MARKERS) or any(
        symbol in raw_text for symbol in _OPEN_ENDED_SYMBOLS
    )
