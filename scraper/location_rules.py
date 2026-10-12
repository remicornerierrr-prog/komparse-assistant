"""Shared location normalization and V1 eligibility rules."""
from __future__ import annotations

import re
import unicodedata
from typing import Any


TARGET_CITIES = ("koln", "bonn", "dusseldorf")


def normalize_location(value: Any) -> str:
    """Normalize German location labels for reliable classification."""
    if value is None:
        return ""

    text = str(value).strip().casefold().replace("ß", "ss")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(
        char for char in text
        if not unicodedata.combining(char)
    )

    # Komparse sometimes concatenates this page heading directly
    # with the first offer's location (e.g. "Aktuelle GesucheKöln").
    text = re.sub(
        r"^\s*aktuelle\s*gesuche(?:\s*[:|,–-]\s*|\s*)",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"\s*/\s*", "/", text)
    text = re.sub(r"\s*\+\s*", "+", text)
    text = re.sub(r"\s*&\s*", " & ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" \t\r\n|,;:")


def classify_location(location: Any) -> str:
    """Return ``v1``, ``manual_review`` or ``outside``.

    Labels in the configured Köln/Bonn/Düsseldorf area are eligible for
    automatic V1 matching when they match an explicit supported format.
    Mentions of any target city in an unrecognized or compound label are
    ambiguous and must be reviewed; they must never be silently excluded.
    """
    text = normalize_location(location)
    if not text:
        return "manual_review"

    manual_patterns = (
        r"^nrw\b",
        r"^nordrhein[- ]westfalen\b",
        r"^deutschlandweit\b",
        r"^bundesweit\b",
        r"^ganz deutschland\b",
        r"^deutschland$",
        r"^germany\b",
        r"^europaweit\b",
        r"^deutschland/\w+",
    )
    if any(re.search(pattern, text) for pattern in manual_patterns):
        return "manual_review"

    # Optional geographic prefix, one supported city or a slash-separated
    # list of supported cities, then an optional radius/surrounding suffix.
    city_list = r"(?:koln|bonn|dusseldorf)(?:/(?:koln|bonn|dusseldorf))*"
    prefix = r"(?:(?:grossraum|raum|region)\s+)?"
    suffix = (
        r"(?:"
        r"\+(?:umgebung|\d+\s*km(?:\s+umkreis)?)"
        r"|\s+(?:und|&)\s+umgebung"
        r")?"
    )
    accepted_pattern = re.compile(
        r"^" + prefix + city_list + suffix + r"$"
    )

    if accepted_pattern.fullmatch(text):
        return "v1"

    # Compound regional labels can overlap the target area without naming
    # a supported city explicitly. In particular, "Ruhrgebiet/Reinland"
    # may include the Cologne/Rhineland area, so don't silently exclude it.
    if re.search(r"\b(?:ruhrgebiet|rheinland|reinland)\b", text) and "/" in text:
        return "manual_review"

    # If the label mentions one of the V1 cities but does not follow an
    # explicit supported format (e.g. "Köln und Ruhrgebiet"), don't silently
    # reject it. Send it for manual review instead.
    target_city_mention = re.compile(
        r"\b(?:koln|bonn|dusseldorf)\b"
    )
    if target_city_mention.search(text):
        return "manual_review"

    return "outside"
