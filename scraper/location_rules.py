"""Shared location normalization and V1 eligibility rules."""
from __future__ import annotations

import re
import unicodedata
from typing import Any


def normalize_location(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().casefold().replace("ß", "ss")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"^\s*aktuelle\s*gesuche(?:\s*[:|,–-]\s*|\s*)", "", text, flags=re.IGNORECASE)
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"\s*/\s*", "/", text)
    text = re.sub(r"\s*\+\s*", "+", text)
    text = re.sub(r"\s*&\s*", " & ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" \t\r\n|,;:")


def classify_location(location: Any) -> str:
    """Return ``v1``, ``manual_review`` or ``outside``.

    A nationwide/large-region label is never narrowed automatically just
    because a description later mentions a shooting city.
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

    allowed_patterns = (
        r"^koln(?:-[a-z0-9]+)*$",
        r"^bonn(?:-[a-z0-9]+)*$",
        r"^dusseldorf(?:-[a-z0-9]+)*$",
        r"^grossraum koln$",
        r"^grossraum bonn$",
        r"^grossraum dusseldorf$",
        r"^grossraum koln/bonn/dusseldorf$",
        r"^grossraum koln/dusseldorf$",
        r"^grossraum bonn/dusseldorf$",
        r"^raum koln$",
        r"^raum bonn$",
        r"^raum dusseldorf$",
        r"^koln\s*&\s*umgebung$",
        r"^koln\s+und\s+umgebung$",
        r"^koln\+100\s*km$",
        r"^koln\+150\s*km$",
        r"^koln/bonn$",
        r"^bonn/koln$",
    )
    if any(re.fullmatch(pattern, text) for pattern in allowed_patterns):
        return "v1"

    return "outside"
