"""Normalize parsed gender labels without substring false positives."""
from __future__ import annotations

import re
from typing import Any


MALE_LABELS = {
    "male", "man", "mann", "männer", "maenner",
    "männlich", "männliche", "männlicher", "männlichen", "männlichem",
    "maennlich", "maennliche", "maennlicher", "maennlichen", "maennlichem",
    "m", "h", "herr", "herren", "vater", "sohn", "junge", "jungen",
}

FEMALE_LABELS = {
    "female", "woman", "frau", "frauen", "weiblich", "weibliche",
    "weiblicher", "weiblichen", "weiblichem", "weibl", "weiblich.",
    "f", "w", "dame", "damen", "komparsin", "komparsinnen",
    "darstellerin", "kleindarstellerin", "testerin", "testerinnen",
}


def gender_flags_from_value(value: Any) -> tuple[bool, bool]:
    """Return (male, female), matching complete labels, never substrings.

    Canonical parser values are typically lists such as ["female"] or
    ["male", "female"]. Text abbreviations like M/W/D are also accepted.
    Unknown or generic wording remains unspecified (False, False).
    """
    if value is None:
        return False, False

    if isinstance(value, (list, tuple, set)):
        raw_values = [str(item) for item in value if item is not None]
    else:
        raw_values = [str(value)]

    raw_text = " ".join(raw_values).casefold()
    if re.search(r"\b(?:m\s*/\s*w\s*/\s*d|w\s*/\s*m\s*/\s*d|m\s*/\s*w|w\s*/\s*m)\b", raw_text):
        return True, True

    tokens: set[str] = set()
    for raw in raw_values:
        for token in re.split(r"[\s,;/+|&]+", raw.casefold()):
            token = token.strip(" \t\r\n\"'[]{}()")
            token = token.rstrip(".")
            if token:
                tokens.add(token)

    male = bool(tokens & MALE_LABELS)
    female = bool(tokens & FEMALE_LABELS)
    return male, female
