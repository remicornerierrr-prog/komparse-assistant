"""Parse Komparse casting offers and preserve uncertain information explicitly."""
from __future__ import annotations

import json
import re
from datetime import datetime
from urllib.parse import parse_qs, unquote, urljoin

import requests
from bs4 import BeautifulSoup

try:  # Works both as `python scraper/parser.py` and `import scraper.parser`.
    from .location_rules import classify_location, normalize_location
except ImportError:  # pragma: no cover - script execution path
    from location_rules import classify_location, normalize_location


INPUT_FILE = "komparse_offers.json"
OUTPUT_FILE = "komparse_parsed_offers.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

GERMAN_MONTHS = {
    "januar": 1, "februar": 2, "märz": 3, "maerz": 3, "april": 4,
    "mai": 5, "juni": 6, "juli": 7, "august": 8, "september": 9,
    "oktober": 10, "november": 11, "dezember": 12,
}
MONTH_PATTERN = (
    r"Januar|Februar|März|Maerz|April|Mai|Juni|Juli|August|"
    r"September|Oktober|November|Dezember"
)


def normalize_text(text: str | None) -> str:
    if not text:
        return ""
    text = str(text).replace("\xa0", " ").replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_offer_title(text: str | None) -> str:
    """Remove the page heading that legacy HTML sometimes prepends to title."""
    text = normalize_text(text)
    text = re.sub(r"^\s*Aktuelle\s*Gesuche(?:\s*[:|,–-]\s*|\s*)", "", text, flags=re.IGNORECASE)
    return text.strip()


# ============================================================
# LOCATION
# ============================================================

def detect_location(text: str) -> dict:
    title = clean_offer_title(text)
    location_text = title.split("|")[0].strip()
    location_text = re.sub(
        r"^\s*Aktuelle\s*Gesuche(?:\s*[:|,–-]\s*|\s*)", "", location_text, flags=re.IGNORECASE
    ).strip()
    status = classify_location(location_text)
    return {
        "matches_mvp": status == "v1",
        "location_status": status,
        "location_text": location_text,
    }


# ============================================================
# GENDER
# ============================================================

def detect_gender(text: str) -> set[str]:
    """Return explicit gender constraints only.

    Inclusive forms and explicit mixed wording return both genders. A generic
    plural such as 'Komparsen'/'Darsteller' is intentionally *not* treated as
    male-only: without explicit evidence it returns an empty set so that the
    offer can be reviewed instead of silently excluding women.
    """
    t = normalize_text(text).casefold()

    mixed_patterns = [
        r"\bm\s*/\s*w\s*/\s*d\b",
        r"\bw\s*/\s*m\s*/\s*d\b",
        r"\bm\s*/\s*w\b",
        r"\bw\s*/\s*m\b",
        r"\b[\wäöüß-]+[*:_]innen\b",  # Darsteller*innen, Kompars*innen, Tester:innen
        r"\b(?:damen\s+(?:und|oder|/)\s+herren|herren\s+(?:und|oder|/)\s+damen)\b",
        r"\b(?:frauen\s+(?:und|oder|/)\s+männer|männer\s+(?:und|oder|/)\s+frauen)\b",
    ]
    if any(re.search(pattern, t, re.IGNORECASE) for pattern in mixed_patterns):
        return {"male", "female"}

    male_patterns = [
        r"\bmännlich(?:e|er|en)?\b",
        r"\bmännl\.",
        r"\bmaennlich(?:e|er|en)?\b",
        r"\bmänner\b",
        r"\bmann\b",
        r"\bherren\b",
        r"\bherr\b",
        r"\bvater\b",
        r"\bsohn\b",
        r"\bjunge(?:n)?\b",
        r"\bmale\b",
        r"(^|[\s(,/|\-])m(?=[\s),;./|\-]|$)",
    ]

    female_patterns = [
        r"\bweiblich(?:e|er|en)?\b",
        r"\bweibl\.",
        r"\bfrau(?:en)?\b",
        r"\bdamen?\b",
        r"\bkomparsin(?:nen)?\b",
        r"\bkleindarstellerin(?:nen)?\b",
        r"\bdarstellerin(?:nen)?\b",
        r"\bseniorin(?:nen)?\b",
        r"\bmädchen\b",
        r"\btesterin(?:nen)?\b",
        r"\bmoderatorin(?:nen)?\b",
        r"\bjournalistin(?:nen)?\b",
        r"\bredakteurin(?:nen)?\b",
        r"\bschauspielerin(?:nen)?\b",
        r"\bpatientin(?:nen)?\b",
        r"\bbeamtin(?:nen)?\b",
        r"\bfahrerin(?:nen)?\b",
        r"\bsportlerin(?:nen)?\b",
        r"\bweiblich\b",
        r"\bfemale\b",
        r"(^|[\s(,/|\-])w(?=[\s),;./|\-]|$)",
    ]

    genders: set[str] = set()
    if any(re.search(pattern, t, re.IGNORECASE) for pattern in male_patterns):
        genders.add("male")
    if any(re.search(pattern, t, re.IGNORECASE) for pattern in female_patterns):
        genders.add("female")
    return genders


# ============================================================
# AGE RANGES AND DESCRIPTIONS
# ============================================================

def extract_age_ranges(text: str) -> list[dict]:
    """Extract explicit age bounds without turning 'ab 30' into exactly 30."""
    t = normalize_text(text)
    ranges: list[dict] = []
    occupied: list[tuple[int, int]] = []

    def add(match: re.Match, age_min: int | None, age_max: int | None) -> None:
        if any(match.start() < end and match.end() > start for start, end in occupied):
            return
        ranges.append({
            "min": age_min,
            "max": age_max,
            "start": match.start(),
            "end": match.end(),
        })
        occupied.append((match.start(), match.end()))

    # Closed ranges: 25 bis 55 Jahre, 9-17 J., 30–60 Jahren.
    closed_pattern = (
        r"\b(?:im\s+Alter\s+von\s+|zwischen\s+)?"
        r"(\d{1,2})\s*(?:bis|[-–])\s*(\d{1,2})"
        r"\s*(?:J\.?|Jahre|Jahren)\b"
    )
    for match in re.finditer(closed_pattern, t, re.IGNORECASE):
        add(match, int(match.group(1)), int(match.group(2)))

    # Lower bound: ab 30 Jahre(n), über 35, mindestens 18, 30+.
    lower_patterns = [
        r"\b(?:ab|über|ueber|mindestens)\s*(\d{1,2})\s*(?:J\.?|Jahre|Jahren)?\b",
        r"\b(\d{1,2})\s*(?:J\.?|Jahre|Jahren)\s*\+",
        r"\b(\d{1,2})\s*\+(?!\w)",
    ]
    for pattern in lower_patterns:
        for match in re.finditer(pattern, t, re.IGNORECASE):
            add(match, int(match.group(1)), None)

    # Upper bound: bis/unter/höchstens 60 Jahre. Closed ranges are already occupied.
    upper_patterns = [
        r"\b(?:bis|unter|höchstens|hoechstens)\s*(\d{1,2})\s*(?:J\.?|Jahre|Jahren)?\b",
    ]
    for pattern in upper_patterns:
        for match in re.finditer(pattern, t, re.IGNORECASE):
            add(match, None, int(match.group(1)))

    # Single stated age such as 'ca. 30 Jahre', excluding range phrases.
    single_pattern = r"\b(?:ca\.?\s*)?(\d{1,2})\s*(?:J\.?|Jahre|Jahren)\b"
    for match in re.finditer(single_pattern, t, re.IGNORECASE):
        if any(match.start() < end and match.end() > start for start, end in occupied):
            continue
        before = t[max(0, match.start() - 25):match.start()]
        if re.search(r"\b(?:ab|über|ueber|mindestens|unter|bis|höchstens|hoechstens)\s*$", before):
            continue
        add(match, int(match.group(1)), int(match.group(1)))

    return sorted(ranges, key=lambda item: item["start"])


def extract_age_description(text: str) -> str | None:
    """Extract a readable age note without pretending vague text is numeric."""
    t = normalize_text(text)
    if not t:
        return None

    mixed = re.search(
        r"\b(?:gemischtes\s+alter|altersgemischt|verschiedene\s+altersgruppen|"
        r"alle\s+altersgruppen|menschen\s+jeden\s+alters)\b",
        t,
        re.IGNORECASE,
    )
    if mixed:
        return normalize_text(mixed.group(0))

    ranges = extract_age_ranges(t)
    if ranges:
        item = ranges[0]
        return normalize_text(t[item["start"]:item["end"]])

    approximate = re.search(
        r"\b(?:Anfang|Mitte|Ende)\s+\d{2}\b|"
        r"\b(?:jugendlich|junge\s+Erwachsene|Senior(?:en|innen)?)\b",
        t,
        re.IGNORECASE,
    )
    if approximate:
        return normalize_text(approximate.group(0))

    return None


def extract_profiles(text: str) -> list[dict]:
    """Extract role-specific age/gender contexts without mixing adjacent roles."""
    t = clean_offer_title(text)
    age_ranges = extract_age_ranges(t)

    if not age_ranges:
        genders = detect_gender(t)
        if genders or t:
            return [{
                "gender": sorted(genders),
                "age_min": None,
                "age_max": None,
                "context": t,
            }]
        return []

    profiles = []
    for index, age in enumerate(age_ranges):
        # Restrict context to the current pipe-delimited role area.
        segment_start = t.rfind("|", 0, age["start"]) + 1
        previous_ranges = [
            previous for previous in age_ranges[:index]
            if t.rfind("|", 0, previous["start"]) == t.rfind("|", 0, age["start"])
        ]

        # In listings such as 91.306, every age range follows its role.
        # Starting after the previous age keeps the next role's gender
        # from contaminating the previous role's profile.
        context_start = previous_ranges[-1]["end"] if previous_ranges else segment_start
        context = t[context_start:age["end"]].strip(" ,;|:.")
        genders = detect_gender(context)
        profiles.append({
            "gender": sorted(genders),
            "age_min": age["min"],
            "age_max": age["max"],
            "context": context,
        })
    return profiles


# ============================================================
# SHOOTING DATES, PERIODS AND DURATION
# ============================================================

def _resolve_year(year_text: str | None, default_year: int) -> int:
    if not year_text:
        return default_year
    year = int(year_text)
    return year + 2000 if year < 100 else year


def extract_shoot_dates(
    text: str,
    default_year: int | None = None,
) -> list[str]:
    t = normalize_text(text)
    if default_year is None:
        default_year = datetime.now().year
    dates: list[str] = []
    covered: list[tuple[int, int]] = []

    # Alternative exact days: 7. o. 8. November / 7. oder 8. November.
    alternative_pattern = (
        rf"\b(\d{{1,2}})\.\s*(?:o\.|oder|/)\s*(\d{{1,2}})\.\s*"
        rf"({MONTH_PATTERN})(?:\s+(\d{{4}}))?\b"
    )
    for match in re.finditer(alternative_pattern, t, re.IGNORECASE):
        month = GERMAN_MONTHS.get(match.group(3).casefold())
        year = _resolve_year(match.group(4), default_year)
        if month:
            for day_text in (match.group(1), match.group(2)):
                try:
                    iso = datetime(year, month, int(day_text)).strftime("%Y-%m-%d")
                except ValueError:
                    continue
                if iso not in dates:
                    dates.append(iso)
            covered.append((match.start(), match.end()))

    numeric_pattern = r"\b(\d{1,2})\.(\d{1,2})(?:\.(\d{2,4}))?\b"
    for match in re.finditer(numeric_pattern, t):
        if any(match.start() < end and match.end() > start for start, end in covered):
            continue
        day = int(match.group(1))
        month = int(match.group(2))
        year = _resolve_year(match.group(3), default_year)
        try:
            iso = datetime(year, month, day).strftime("%Y-%m-%d")
        except ValueError:
            continue
        if iso not in dates:
            dates.append(iso)

    written_pattern = rf"\b(\d{{1,2}})\.\s*({MONTH_PATTERN})(?:\s+(\d{{4}}))?\b"
    for match in re.finditer(written_pattern, t, re.IGNORECASE):
        if any(match.start() < end and match.end() > start for start, end in covered):
            continue
        day = int(match.group(1))
        month = GERMAN_MONTHS.get(match.group(2).casefold())
        year = _resolve_year(match.group(3), default_year)
        if not month:
            continue
        try:
            iso = datetime(year, month, day).strftime("%Y-%m-%d")
        except ValueError:
            continue
        if iso not in dates:
            dates.append(iso)

    return dates


def extract_shoot_date_text(
    title: str,
    detail_text: str = "",
    default_year: int | None = None,
    shoot_dates: list[str] | None = None,
) -> str | None:
    """Preserve a human-readable period or flexible schedule.

    A period such as "Ende November" is deliberately stored as text, not
    converted to a fictitious exact date. Exact dates remain in `shoot_date`.
    """
    if default_year is None:
        default_year = datetime.now().year

    shoot_dates = shoot_dates or []
    title = normalize_text(title)
    detail_text = normalize_text(detail_text)
    combined = f"{title} {detail_text}".strip()

    # Exact alternatives: 7. o. 8. November / 7. oder 8. November.
    alternative_pattern = (
        rf"\b(\d{{1,2}})\.\s*(?:o\.|oder|/)\s*"
        rf"(\d{{1,2}})\.\s*({MONTH_PATTERN})(?:\s+(\d{{4}}))?\b"
    )
    alternative = re.search(alternative_pattern, combined, re.IGNORECASE)
    if alternative:
        year = _resolve_year(alternative.group(4), default_year)
        return (
            f"{alternative.group(1)}. oder {alternative.group(2)}. "
            f"{alternative.group(3)} {year}"
        )

    # Approximate periods with an explicit phase of the month.
    phase_pattern = (
        rf"\b((?:Anfang|Mitte|Ende)\s+"
        rf"(?:(?:des|vom)\s+Monats\s+)?(?:{MONTH_PATTERN}))"
        rf"(?:\s+(\d{{4}}))?\b"
    )
    phase = re.search(phase_pattern, combined, re.IGNORECASE)
    if phase:
        value = normalize_text(phase.group(1))
        year = phase.group(2) or str(default_year)
        return f"{value} {year}"

    # Weeks/month halves, e.g. "erste Woche im November".
    week_pattern = (
        rf"\b((?:erste|ersten|zweite|zweiten|letzte|letzten)\s+"
        rf"Woche(?:\s+des\s+Monats)?\s+(?:im\s+)?(?:{MONTH_PATTERN}))"
        rf"(?:\s+(\d{{4}}))?\b"
    )
    week = re.search(week_pattern, combined, re.IGNORECASE)
    if week:
        value = normalize_text(week.group(1))
        year = week.group(2) or str(default_year)
        return f"{value} {year}"

    # Seasons and broad periods such as "im Sommer 2027".
    season = re.search(
        r"\b(?:(im|am)\s+)?(Frühjahr|Fruehjahr|Sommer|Herbst|Winter)(?:\s+(\d{4}))?\b",
        combined,
        re.IGNORECASE,
    )
    if season:
        value = normalize_text(season.group(2))
        year = season.group(3) or str(default_year)
        return f"{value} {year}"

    # Calendar week, e.g. KW 48 or KW 48/2026.
    calendar_week = re.search(r"\b(KW\s*\d{1,2}(?:\s*/\s*\d{2,4})?)\b", combined, re.IGNORECASE)
    if calendar_week:
        return normalize_text(calendar_week.group(1))

    # Month-only timing such as "im November 2026". Prefer wording with
    # "im" when present; keep the value approximate.
    month_pattern = rf"\b((?:im\s+)?(?:{MONTH_PATTERN}))(?:\s+(\d{{4}}))\b"
    month = re.search(month_pattern, combined, re.IGNORECASE)
    if month:
        value = normalize_text(month.group(1))
        return f"{value} {month.group(2)}"

    # Flexible timing. This remains separate from the duration field.
    flexible_patterns = (
        r"\bnach\s+Absprache\b",
        r"\bnach\s+Vereinbarung\b",
        r"\bnach\s+Ruecksprache\b",
        r"\bnach\s+Rücksprache\b",
        r"\bTermin\s+nach\s+(?:Absprache|Vereinbarung)\b",
        r"\bflexib(?:el|le|ler|len)\s+(?:Dreh)?termine?\b",
    )
    if any(re.search(pattern, combined, re.IGNORECASE) for pattern in flexible_patterns):
        return "Nach Absprache"

    if len(shoot_dates) == 1:
        return None  # The exact ISO date is stored separately in `shoot_date`.
    if len(shoot_dates) > 1:
        return "Mehrere mögliche Termine"
    return None


def extract_shoot_duration_text(title: str, detail_text: str = "") -> str | None:
    """Keep duration/conditions such as '2x 0,5 Drehtage + Videotagebuch'."""
    title = normalize_text(title)
    detail_text = normalize_text(detail_text)
    segments = [part.strip() for part in title.split("|")]
    candidates = [
        part for part in segments
        if re.search(r"\bDreh(?:tag|tage|tagen)\b", part, re.IGNORECASE)
    ]

    candidate = candidates[0] if candidates else ""
    if not candidate and detail_text:
        match = re.search(
            r"([^.!?]{0,80}\b\d+\s*(?:x|×)?\s*\d*[,\.]?\d*\s*Dreh(?:tag|tage|tagen)[^.!?]{0,100})",
            detail_text,
            re.IGNORECASE,
        )
        candidate = normalize_text(match.group(1)) if match else ""

    if not candidate:
        return None

    # Remove date/period wording, keeping duration and logistical conditions.
    candidate = re.sub(
        rf",?\s*\b(?:Anfang|Mitte|Ende)\s+(?:des\s+Monats\s+)?(?:{MONTH_PATTERN})(?:\s+\d{{4}})?\b.*$",
        "",
        candidate,
        flags=re.IGNORECASE,
    )
    candidate = re.sub(
        rf",?\s*\b\d{{1,2}}\.\s*(?:o\.|oder|/)\s*\d{{1,2}}\.\s*(?:{MONTH_PATTERN})(?:\s+\d{{4}})?\b.*$",
        "",
        candidate,
        flags=re.IGNORECASE,
    )
    # Multiple written dates must be removed before the single-date rule.
    candidate = re.sub(
        rf",?\s*\b\d{{1,2}}\.\s*(?:und|&)\s*\d{{1,2}}\.\s*(?:{MONTH_PATTERN})(?:\s+\d{{4}})?\b.*$",
        "",
        candidate,
        flags=re.IGNORECASE,
    )
    candidate = re.sub(
        rf",?\s*\b\d{{1,2}}\.\s*(?:{MONTH_PATTERN})(?:\s+\d{{4}})?\b.*$",
        "",
        candidate,
        flags=re.IGNORECASE,
    )
    candidate = re.sub(
        r",?\s*\b\d{1,2}\.\d{1,2}(?:\.\d{2,4})?\b.*$",
        "",
        candidate,
        flags=re.IGNORECASE,
    )
    # A broad season belongs to the date field, not the duration field.
    candidate = re.sub(
        r"\bDrehzeitraum\s+(?:im\s+)?(?:Frühjahr|Fruehjahr|Sommer|Herbst|Winter)(?:\s+\d{4})?\s*,?\s*",
        "",
        candidate,
        flags=re.IGNORECASE,
    )
    candidate = re.sub(
        r"\b(?:nach\s+Absprache|nach\s+Vereinbarung|Termin\s+nach\s+Absprache)\b",
        "",
        candidate,
        flags=re.IGNORECASE,
    )
    candidate = re.sub(r"\s+", " ", candidate).strip(" ,;|:+-")
    candidate = re.sub(r"\s*\+\s*", " + ", candidate)
    return candidate or None


# ============================================================
# EMAIL AND APPLICATION INSTRUCTIONS
# ============================================================

def extract_email(text: str) -> str | None:
    match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text or "")
    return match.group(0) if match else None


def clean_subject(subject: str) -> str:
    return normalize_text(subject).strip(' "\'„“”‚‘’»«').strip()


def extract_subject_keyword(text: str, mailto_subject: str | None = None) -> str | None:
    if mailto_subject:
        subject = clean_subject(mailto_subject)
        if subject:
            return subject

    quote_patterns = [
        r'Betreff\s*:\s*[„“”"](.+?)[„“”"]',
        r'mit\s+(?:dem\s+)?Betreff\s+[„“”"](.+?)[„“”"]',
        r'mit\s+[„“”"](.+?)[„“”"]\s+im\s+Betreff',
        r'mit\s+"(.+?)"\s+im\s+Betreff',
    ]
    for pattern in quote_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            subject = clean_subject(match.group(1))
            if subject and len(subject) <= 150:
                return subject

    match = re.search(
        r'Betreff\s*:\s*(.+?)(?:\s+Datenschutz|\s+\*\s*\*\s*\*|$)',
        text,
        re.IGNORECASE,
    )
    if match:
        subject = clean_subject(match.group(1))
        if subject:
            return subject

    keyword_patterns = [
        r'(?:Stichwort|Suchwort|Keyword)\s*[:\-]?\s*[„“”"](.+?)[„“”"]',
        r'(?:Projekt(?:auswahl)?|Auswahl)\s*:\s*'
        r'(?:Stichwort|Suchwort|Keyword)\s*[:\-]?\s*[„“”"](.+?)[„“”"]',
    ]
    for pattern in keyword_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            subject = clean_subject(match.group(1))
            if subject and len(subject) <= 150:
                return subject
    return None


def extract_application_url(html: str, base_url: str | None = None) -> str | None:
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    candidates: list[tuple[int, str]] = []
    application_keywords = (
        "bewerb", "bewerben", "bewerbung", "apply", "application", "casting",
        "anmeldung", "registrieren", "formular", "form", "projekt",
    )
    context_keywords = (
        "bewerbung", "bewerbungen", "bewerben", "homepage", "online",
        "formular", "website", "internet", "apply",
    )
    excluded_domains = (
        "komparse.de", "facebook.com", "instagram.com", "youtube.com",
        "linkedin.com", "tiktok.com",
    )

    for link in soup.find_all("a", href=True):
        href = link.get("href", "").strip()
        if not href or href.casefold().startswith(("mailto:", "tel:", "javascript:")):
            continue
        if href.startswith("//"):
            href = "https:" + href
        elif base_url:
            href = urljoin(base_url, href)
        if not re.match(r"^https?://", href, re.IGNORECASE):
            continue
        lower_href = href.casefold()
        if any(domain in lower_href for domain in excluded_domains):
            continue
        anchor = normalize_text(link.get_text(" ", strip=True)).casefold()
        parent = normalize_text(link.parent.get_text(" ", strip=True) if link.parent else "").casefold()
        nearby = parent
        if len(nearby) < 25 and link.parent and link.parent.parent:
            nearby = normalize_text(link.parent.parent.get_text(" ", strip=True)).casefold()
        score = sum(10 for word in application_keywords if word in lower_href)
        score += sum(15 for word in application_keywords if word in anchor)
        score += sum(5 for word in context_keywords if word in nearby)
        if score:
            candidates.append((score, href))

    if candidates:
        candidates.sort(key=lambda item: (item[0], len(item[1])), reverse=True)
        return candidates[0][1]

    text = normalize_text(soup.get_text(" ", strip=True))
    url_pattern = r"(https?://[^\s<>\]]+)|\b(?:www\.)[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?:/[^\s<>\]]*)?"
    for match in re.finditer(url_pattern, text, re.IGNORECASE):
        candidate = match.group(0).strip(".,;:()[]{}<>\"'")
        lower = candidate.casefold()
        if any(domain in lower for domain in excluded_domains):
            continue
        if any(word in lower for word in application_keywords):
            return "https://" + candidate if lower.startswith("www.") else candidate
    return None


def determine_application_method(email: str | None, application_url: str | None) -> str:
    if email and application_url:
        return "multiple"
    if email:
        return "email"
    if application_url:
        return "website"
    return "unknown"


# ============================================================
# DETAIL PAGE
# ============================================================

def download_detail_page(url: str) -> str | None:
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        return response.content.decode("cp1252", errors="replace")
    except requests.RequestException as error:
        print(f"Erreur téléchargement {url} : {error}")
        return None


def parse_detail_page(html: str | None, base_url: str | None = None) -> dict:
    if not html:
        return {
            "detail_text": "", "email": None, "subject_keyword": None,
            "shoot_dates": [], "shoot_date_text": None,
            "shoot_duration_text": None, "age_description": None,
            "application_url": None, "application_method": "unknown",
        }

    soup = BeautifulSoup(html, "html.parser")
    detail_text = normalize_text(soup.get_text(" ", strip=True))
    email = None
    mailto_subject = None
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if href.casefold().startswith("mailto:"):
            address_and_query = href[7:]
            if "?" in address_and_query:
                address, query = address_and_query.split("?", 1)
                params = parse_qs(query)
                if params.get("subject"):
                    mailto_subject = unquote(params["subject"][0])
                if not email:
                    email = address.strip()
            elif not email:
                email = address_and_query.strip()

    if not email:
        email = extract_email(detail_text)

    subject_keyword = extract_subject_keyword(detail_text, mailto_subject)
    application_url = extract_application_url(html, base_url=base_url)
    application_method = determine_application_method(email, application_url)

    shoot_dates: list[str] = []
    lines = soup.get_text("\n", strip=True).splitlines()
    for line in lines:
        clean_line = normalize_text(line)
        if re.match(r"^Termin\s*:", clean_line, re.IGNORECASE):
            date_text = re.sub(r"^Termin\s*:\s*", "", clean_line, flags=re.IGNORECASE)
            shoot_dates = extract_shoot_dates(date_text)
            break

    return {
        "detail_text": detail_text,
        "email": email,
        "subject_keyword": subject_keyword,
        "shoot_dates": shoot_dates,
        "shoot_date_text": extract_shoot_date_text("", detail_text, shoot_dates=shoot_dates),
        "shoot_duration_text": extract_shoot_duration_text("", detail_text),
        "age_description": extract_age_description(detail_text),
        "application_url": application_url,
        "application_method": application_method,
    }


# ============================================================
# PARSE ONE OFFER
# ============================================================

def is_varied_age_description(value: str | None) -> bool:
    if not value:
        return False
    return bool(re.search(
        r"\b(?:gemischtes\s+alter|altersgemischt|verschiedene\s+altersgruppen|"
        r"alle\s+altersgruppen|menschen\s+jeden\s+alters)\b",
        normalize_text(value),
        re.IGNORECASE,
    ))


def _all_profiles_have_age_bounds(profiles: list[dict]) -> bool:
    if not profiles:
        return False
    return all(
        isinstance(profile, dict)
        and (profile.get("age_min") is not None or profile.get("age_max") is not None)
        for profile in profiles
    )


def _multi_role_age_description(profiles: list[dict]) -> str | None:
    if len(profiles) < 2 or not _all_profiles_have_age_bounds(profiles):
        return None

    labels = []
    for profile in profiles:
        age_min = profile.get("age_min")
        age_max = profile.get("age_max")
        if age_min is not None and age_max is not None:
            label = f"{age_min}–{age_max} ans"
        elif age_min is not None:
            label = f"{age_min}+ ans"
        else:
            label = f"jusqu'à {age_max} ans"
        labels.append(label)

    return "Plusieurs rôles : " + "; ".join(labels)


def parse_offer(offer: dict) -> dict:
    title = clean_offer_title(offer.get("title", ""))
    raw_text = normalize_text(offer.get("raw_text", ""))
    location_info = detect_location(title)

    publication_date = offer.get("publication_date")
    publication_year = None
    if publication_date:
        match = re.search(r"(\d{4})", str(publication_date))
        if match:
            publication_year = int(match.group(1))
    if publication_year is None:
        publication_year = datetime.now().year

    title_shoot_dates = extract_shoot_dates(title, default_year=publication_year)
    # Never assign an arbitrary date when several alternatives are given.
    shoot_date = title_shoot_dates[0] if len(title_shoot_dates) == 1 else None
    profiles = extract_profiles(title)
    all_genders = {gender for profile in profiles for gender in profile.get("gender", [])}

    if len(profiles) == 1:
        age_min = profiles[0]["age_min"]
        age_max = profiles[0]["age_max"]
    else:
        age_min = None
        age_max = None

    age_description = (
        _multi_role_age_description(profiles)
        or extract_age_description(title)
    )
    review_reasons: list[str] = []
    if location_info["location_status"] == "manual_review":
        review_reasons.append("localisation_ambigue")
    if shoot_date is None:
        review_reasons.append("date_exacte_absente")
    if not profiles or any(not profile.get("gender") for profile in profiles):
        review_reasons.append("sexe_annonce_non_precise")
    if (
        age_min is None
        and age_max is None
        and not is_varied_age_description(age_description)
        and not _all_profiles_have_age_bounds(profiles)
    ):
        review_reasons.append("age_non_numerique")
    needs_review = bool(review_reasons)

    return {
        "komparse_id": offer.get("offer_id"),
        "title": title,
        "raw_text": raw_text,
        "publication_date": publication_date,
        "location_text": location_info["location_text"],
        "location_status": location_info["location_status"],
        "matches_mvp_location": location_info["matches_mvp"],
        "shoot_date": shoot_date,
        "shoot_dates": title_shoot_dates,
        "shoot_date_text": extract_shoot_date_text(
            title, default_year=publication_year, shoot_dates=title_shoot_dates
        ),
        "shoot_duration_text": extract_shoot_duration_text(title),
        "age_min": age_min,
        "age_max": age_max,
        "age_description": age_description,
        "gender": sorted(all_genders),
        "profiles": profiles,
        "parser_review_reasons": review_reasons,
        "parser_review_reason": ", ".join(review_reasons) if review_reasons else None,
        "email": None,
        "subject_keyword": None,
        "application_method": "unknown",
        "application_url": None,
        "detail_url": offer.get("detail_url"),
        "detail_text": "",
        "needs_review": needs_review,
    }


def enrich_offer_from_detail(parsed: dict, detail_data: dict) -> dict:
    """Merge useful detail-page hints while keeping exact dates separate."""
    parsed["detail_text"] = detail_data.get("detail_text") or ""
    parsed["email"] = detail_data.get("email")
    parsed["subject_keyword"] = detail_data.get("subject_keyword")
    parsed["application_url"] = detail_data.get("application_url")
    parsed["application_method"] = detail_data.get("application_method", "unknown")

    detail_dates = detail_data.get("shoot_dates") or []
    if detail_dates:
        parsed["shoot_dates"] = detail_dates
        parsed["shoot_date"] = detail_dates[0] if len(detail_dates) == 1 else None

    # Exact date remains authoritative; otherwise show the extracted period
    # or a flexible arrangement note, never a fabricated ISO date.
    if parsed.get("shoot_date") is None:
        parsed["shoot_date_text"] = (
            extract_shoot_date_text(
                parsed.get("title", ""),
                parsed.get("detail_text", ""),
                default_year=_publication_year(parsed.get("publication_date")),
                shoot_dates=parsed.get("shoot_dates", []),
            )
            or detail_data.get("shoot_date_text")
            or parsed.get("shoot_date_text")
        )

    parsed["shoot_duration_text"] = (
        extract_shoot_duration_text(parsed.get("title", ""), parsed.get("detail_text", ""))
        or detail_data.get("shoot_duration_text")
        or parsed.get("shoot_duration_text")
    )

    profiles = parsed.get("profiles") or []
    if (
        parsed.get("age_min") is None
        and parsed.get("age_max") is None
        and not _all_profiles_have_age_bounds(profiles)
    ):
        parsed["age_description"] = (
            extract_age_description(parsed.get("detail_text", ""))
            or parsed.get("age_description")
        )

    review_reasons = []
    if parsed.get("location_status") == "manual_review":
        review_reasons.append("localisation_ambigue")
    if not parsed.get("shoot_date"):
        review_reasons.append("date_exacte_absente")
    profiles = parsed.get("profiles") or []
    if not profiles or any(
        not role.get("gender") for role in profiles if isinstance(role, dict)
    ):
        review_reasons.append("sexe_annonce_non_precise")
    if (
        parsed.get("age_min") is None
        and parsed.get("age_max") is None
        and not is_varied_age_description(parsed.get("age_description"))
        and not _all_profiles_have_age_bounds(profiles)
    ):
        review_reasons.append("age_non_numerique")

    parsed["parser_review_reasons"] = review_reasons
    parsed["parser_review_reason"] = ", ".join(review_reasons) if review_reasons else None
    parsed["needs_review"] = bool(review_reasons)
    return parsed


def _publication_year(value: str | None) -> int:
    match = re.search(r"\b(20\d{2})\b", str(value or ""))
    return int(match.group(1)) if match else datetime.now().year


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    print("Lecture de komparse_offers.json...")
    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        offers = json.load(file)
    print(f"{len(offers)} annonces chargées.")

    parsed_offers = []
    for index, offer in enumerate(offers, start=1):
        offer_id = offer.get("offer_id")
        print(f"[{index}/{len(offers)}] Analyse annonce {offer_id}...")
        parsed = parse_offer(offer)
        detail_url = parsed.get("detail_url")
        if detail_url:
            detail_html = download_detail_page(detail_url)
            detail_data = parse_detail_page(detail_html, base_url=detail_url)
            parsed = enrich_offer_from_detail(parsed, detail_data)
        parsed_offers.append(parsed)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(parsed_offers, file, ensure_ascii=False, indent=4)

    print()
    print("=" * 80)
    print(f"Fichier créé : {OUTPUT_FILE}")
    print(f"Annonces analysées : {len(parsed_offers)}")
    print("=" * 80)
    print("\nEXEMPLES :\n")
    for offer in parsed_offers[:10]:
        print(f"Annonce : {offer.get('komparse_id')}")
        print(f"Publication : {offer.get('publication_date')}")
        print(f"Localisation : {offer.get('location_text')} ({offer.get('location_status')})")
        print(f"Date : {offer.get('shoot_date') or offer.get('shoot_date_text')}")
        print(f"Durée/modalités : {offer.get('shoot_duration_text')}")
        print(f"Âge : {offer.get('age_min')} - {offer.get('age_max')} ({offer.get('age_description')})")
        print(f"Sexe : {offer.get('gender')}")
        print(f"Email : {offer.get('email')}")
        print(f"Objet : {offer.get('subject_keyword')}")
        print(f"Méthode candidature : {offer.get('application_method')}")
        print(f"URL candidature : {offer.get('application_url')}")
        print(f"À vérifier : {offer.get('needs_review')}")
        print(f"Lien : {offer.get('detail_url')}")
        print("-" * 80)


if __name__ == "__main__":
    main()
