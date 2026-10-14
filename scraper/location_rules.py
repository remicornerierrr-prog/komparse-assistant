"""Shared location normalization and V1 eligibility rules."""
from __future__ import annotations

import re
import unicodedata
from typing import Any


TARGET_CITIES = ("koln", "bonn", "dusseldorf")

# Cities and municipalities in Nordrhein-Westfalen commonly used as offer locations.
# Keep normalized ASCII forms so Köln/Düsseldorf and their spelling variants match.
NRW_CITY_PATTERN = re.compile(r"(?<!\\w)(?:" + r"mulheim\s+an\s+der\s+ruhr|bergisch\s+gladbach|emmerich\s+am\s+rhein|halle\s+\(westfalen\)|monheim\s+am\s+rhein|porta\s+westfalica|monchengladbach|bad\s+oeynhausen|castrop-rauxel|haltern\s+am\s+see|recklinghausen|sankt\s+augustin|wermelskirchen|geilenkirchen|gelsenkirchen|kamp-lintfort|wetter\s+\(ruhr\)|grevenbroich|herzogenrath|konigswinter|huckelhoven|ludenscheid|petershagen|plettenberg|sprockhovel|bad\s+honnef|baesweiler|dusseldorf|eschweiler|euskirchen|gevelsberg|ibbenburen|langenfeld|lennestadt|leverkusen|oberhausen|bielefeld|dinslaken|emsdetten|ennepetal|erftstadt|gutersloh|hattingen|heinsberg|lippstadt|meerbusch|paderborn|remscheid|rheinbach|troisdorf|warendorf|wesseling|wuppertal|arnsberg|bergheim|bornheim|coesfeld|dormagen|dortmund|duisburg|erkelenz|gladbeck|iserlohn|kreuztal|nettetal|ratingen|rietberg|schwerte|siegburg|solingen|stolberg|warstein|wurselen|alsdorf|bocholt|bottrop|detmold|dorsten|frechen|geldern|herford|krefeld|munster|pulheim|schwelm|velbert|viersen|werdohl|aachen|beckum|bochum|borken|brilon|greven|gronau|hennef|herten|hilden|hoxter|julich|kaarst|kempen|kerpen|lohmar|menden|minden|rheine|siegen|voerde|witten|xanten|ahaus|ahlen|bruhl|bunde|duren|essen|hagen|herne|hurth|kamen|kleve|lunen|moers|neuss|oelde|soest|wesel|bonn|goch|hamm|koln|lage|marl|olpe|selm|unna" + r")(?!\\w)")


def is_nrw_location(value: Any) -> bool:
    """Recognize NRW-wide labels and common city names, even without 'NRW'."""
    text = normalize_location(value)
    if not text:
        return False
    if re.search(r"(?<!\\w)(?:nrw|nordrhein[- ]westfalen)(?!\\w)", text):
        return True
    return bool(NRW_CITY_PATTERN.search(text))


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

    # NRW-wide labels and known NRW cities are eligible for profile-level scope filtering.
    if is_nrw_location(text):
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
