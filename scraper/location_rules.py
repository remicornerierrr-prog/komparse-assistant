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
    """Return v1, manual_review or outside.

    V1 includes only the configured Köln/Bonn/Düsseldorf city-area labels.
    NRW-wide, nationwide, radius-based and ambiguous regional labels require
    manual review; unrelated locations are outside the V1 area.
    """
    text = normalize_location(location)
    if not text:
        return "manual_review"

    # Hürth borders Cologne and is part of the immediate Cologne casting area.
    # Casting listings use slash, "und", or ampersand interchangeably.
    if re.fullmatch(r"(?:hurth|koln)\s*(?:/|und|&)\s*(?:hurth|koln)", text) and (
        "hurth" in text and "koln" in text
    ):
        return "v1"

    # Nationwide and NRW-wide labels are valid scopes. The matching
    # layer applies each profile's explicit national/regional preferences.
    if re.fullmatch(r"(?:nrw|nordrhein[- ]westfalen)(?:\s*\+.*)?", text):
        return "v1"

    nationwide_patterns = (
        r"^bundesweit$",
        r"^deutschlandweit$",
        r"^ganz deutschland$",
        r"^deutschland$",
        r"^germany$",
    )
    if any(re.fullmatch(pattern, text) for pattern in nationwide_patterns):
        return "v1"

    # Only supported city labels and combinations are automatically eligible.
    # Radius/Umgebung labels need explicit configuration or manual review.
    city_list = r"(?:koln|bonn|dusseldorf)(?:/(?:koln|bonn|dusseldorf))*"
    prefix = r"(?:(?:grossraum|raum|region)\s+)?"
    accepted_pattern = re.compile(r"^" + prefix + city_list + r"$")

    if accepted_pattern.fullmatch(text):
        return "v1"

    # Compound regional labels can overlap the target area without naming
    # a supported city explicitly. Keep these for manual review.
    if re.search(r"\b(?:ruhrgebiet|rheinland|reinland)\b", text) and "/" in text:
        return "manual_review"

    # If the label mentions one of the V1 cities but does not follow an
    # explicit supported format (e.g. "Köln und Ruhrgebiet"), review it.
    target_city_mention = re.compile(r"\b(?:koln|bonn|dusseldorf)\b")
    if target_city_mention.search(text):
        return "manual_review"

    return "outside"
