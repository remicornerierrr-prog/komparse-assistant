"""Parse Komparse casting offers, including external application methods."""

from __future__ import annotations

import json
import re
from datetime import datetime
from urllib.parse import parse_qs, unquote, urljoin

import requests
from bs4 import BeautifulSoup


INPUT_FILE = "komparse_offers.json"
OUTPUT_FILE = "komparse_parsed_offers.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}


# ============================================================
# TEXT HELPERS
# ============================================================


def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\xa0", " ")
    text = text.replace("\r", " ")
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ============================================================
# LOCATION
# ============================================================


def detect_location(text: str) -> dict:
    text = normalize_text(text)
    location_text = text.split("|")[0].strip()
    t = location_text.casefold()

    patterns = [
        r"\bköln\b",
        r"\bkoeln\b",
        r"\bgroßraum\s+köln\b",
        r"\bgrossraum\s+köln\b",
        r"\bgrossraum\s+koeln\b",
        r"\bgroßraum\s+bonn\b",
        r"\bgrossraum\s+bonn\b",
        r"\bgroßraum\s+düsseldorf\b",
        r"\bgrossraum\s+düsseldorf\b",
        r"\bgrossraum\s+duesseldorf\b",
        r"\bgroßraum\s+köln\s*/\s*bonn\s*/\s*düsseldorf\b",
        r"\bgrossraum\s+köln\s*/\s*bonn\s*/\s*düsseldorf\b",
        r"\bgrossraum\s+koeln\s*/\s*bonn\s*/\s*duesseldorf\b",
        r"\bgroßraum\s+köln\s*/\s*düsseldorf\b",
        r"\bgrossraum\s+köln\s*/\s*düsseldorf\b",
        r"\bgrossraum\s+koeln\s*/\s*duesseldorf\b",
        r"\braum\s+köln\b",
        r"\braum\s+koeln\b",
        r"\bköln\s*&\s*umgebung\b",
        r"\bkoeln\s*&\s*umgebung\b",
        r"\bköln\s*\+\s*\d+\s*km\b",
        r"\bkoeln\s*\+\s*\d+\s*km\b",
        r"\bköln\s*\+\s*\d+\s*km\s+umkreis\b",
        r"\bkoeln\s*\+\s*\d+\s*km\s+umkreis\b",
    ]

    for pattern in patterns:
        if re.search(pattern, t, re.IGNORECASE):
            return {
                "matches_mvp": True,
                "location_text": location_text,
            }

    return {
        "matches_mvp": False,
        "location_text": location_text,
    }


# ============================================================
# GENDER
# ============================================================


def detect_gender(text: str) -> set[str]:
    """Detect explicit male/female indicators; return both when mixed."""
    t = normalize_text(text).casefold()

    # Explicit inclusive/gender-neutral casting abbreviations.
    mixed_patterns = [
        r"\bkompars\*innen\b",
        r"\bm\s*/\s*w\s*/\s*d\b",
        r"\bw\s*/\s*m\s*/\s*d\b",
        r"\bm\s*/\s*w\b",
        r"\bw\s*/\s*m\b",
    ]
    if any(re.search(pattern, t, re.IGNORECASE) for pattern in mixed_patterns):
        return {"male", "female"}

    male_patterns = [
        r"\bmännlich\b",
        r"\bmännliche\b",
        r"\bmännlicher\b",
        r"\bmännl\.",
        r"\bmänner\b",
        r"\bmann\b",
        r"\bherren\b",
        r"\bherr\b",
        r"\bkleindarsteller\b",
        r"\bdarsteller\b",
        r"\bkomparse\b",
        r"\bkomparsen\b",
        r"\bkompars\*e\b",
        r"(^|[\s(,/|\-])m(?=[\s),;./|\-]|$)",
    ]

    female_patterns = [
        r"\bweiblich\b",
        r"\bweibliche\b",
        r"\bweiblicher\b",
        r"\bweibl\.",
        r"\bfrauen\b",
        r"\bfrau\b",
        r"\bdamen\b",
        r"\bdame\b",
        r"\bkomparsin\b",
        r"\bkomparsinnen\b",
        r"\bdarstellerin\b",
        r"\bkleindarstellerin\b",
        r"\bseniorinnen\b",
        r"\bmädchen\b",
        r"(^|[\s(,/|\-])w(?=[\s),;./|\-]|$)",
    ]

    genders: set[str] = set()

    if any(re.search(pattern, t, re.IGNORECASE) for pattern in male_patterns):
        genders.add("male")

    if any(re.search(pattern, t, re.IGNORECASE) for pattern in female_patterns):
        genders.add("female")

    return genders


# ============================================================
# AGE RANGES AND PROFILES
# ============================================================


def extract_age_ranges(text: str) -> list[dict]:
    t = normalize_text(text)
    ranges: list[dict] = []

    pattern_bis = (
        r"(?:ca\.\s*)?"
        r"(\d{1,2})"
        r"\s*bis\s*"
        r"(?:ca\.\s*)?"
        r"(\d{1,2})"
        r"\s*(?:J\.?|Jahre|Jahren)"
    )
    for match in re.finditer(pattern_bis, t, re.IGNORECASE):
        ranges.append({
            "min": int(match.group(1)),
            "max": int(match.group(2)),
            "start": match.start(),
            "end": match.end(),
        })

    pattern_dash = (
        r"(\d{1,2})"
        r"\s*[-–]"
        r"\s*(\d{1,2})"
        r"\s*(?:J\.?|Jahre|Jahren)"
    )
    for match in re.finditer(pattern_dash, t, re.IGNORECASE):
        ranges.append({
            "min": int(match.group(1)),
            "max": int(match.group(2)),
            "start": match.start(),
            "end": match.end(),
        })

    pattern_between = (
        r"\b(?:im\s+Alter\s+von\s+)?"
        r"(\d{1,2})\s*(?:bis|[-–])\s*(\d{1,2})"
        r"\s*(?:J\.?|Jahre|Jahren)"
    )
    for match in re.finditer(pattern_between, t, re.IGNORECASE):
        if not any(
            match.start() >= item["start"] and match.end() <= item["end"]
            for item in ranges
        ):
            ranges.append({
                "min": int(match.group(1)),
                "max": int(match.group(2)),
                "start": match.start(),
                "end": match.end(),
            })

    pattern_single = r"(?:ca\.\s*)?(\d{1,2})\s*(?:J\.?|Jahre|Jahren)"
    for match in re.finditer(pattern_single, t, re.IGNORECASE):
        inside_existing_range = any(
            match.start() >= item["start"] and match.end() <= item["end"]
            for item in ranges
        )
        if not inside_existing_range:
            age = int(match.group(1))
            ranges.append({
                "min": age,
                "max": age,
                "start": match.start(),
                "end": match.end(),
            })

    unique: list[dict] = []
    seen: set[tuple[int, int, int]] = set()
    for item in sorted(ranges, key=lambda value: value["start"]):
        key = (item["min"], item["max"], item["start"])
        if key not in seen:
            seen.add(key)
            unique.append(item)

    return unique


def extract_profiles(text: str) -> list[dict]:
    t = normalize_text(text)
    age_ranges = extract_age_ranges(t)

    plus_match = re.search(
        r"\b(\d{1,2})\s*(?:J\.?|Jahre|Jahren)\s*\+",
        t,
        re.IGNORECASE,
    )
    if plus_match:
        return [{
            "gender": sorted(detect_gender(t)),
            "age_min": int(plus_match.group(1)),
            "age_max": None,
            "context": t,
        }]

    if not age_ranges:
        genders = detect_gender(t)
        if genders:
            return [{
                "gender": sorted(genders),
                "age_min": None,
                "age_max": None,
                "context": t,
            }]
        return []

    profiles: list[dict] = []
    for age in age_ranges:
        start = max(0, age["start"] - 160)
        end = min(len(t), age["end"] + 40)
        context = t[start:end]
        profiles.append({
            "gender": sorted(detect_gender(context)),
            "age_min": age["min"],
            "age_max": age["max"],
            "context": context,
        })

    return profiles


# ============================================================
# SHOOT DATES
# ============================================================

GERMAN_MONTHS = {
    "januar": 1,
    "februar": 2,
    "märz": 3,
    "maerz": 3,
    "april": 4,
    "mai": 5,
    "juni": 6,
    "juli": 7,
    "august": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "dezember": 12,
}


def extract_shoot_dates(
    text: str,
    default_year: int | None = None,
) -> list[str]:
    t = normalize_text(text)
    if default_year is None:
        default_year = datetime.now().year

    dates: list[str] = []
    numeric_pattern = r"\b(\d{1,2})\.(\d{1,2})(?:\.(\d{2,4}))?"
    for match in re.finditer(numeric_pattern, t):
        day = int(match.group(1))
        month = int(match.group(2))
        if match.group(3):
            year = int(match.group(3))
            if year < 100:
                year += 2000
        else:
            year = default_year
        try:
            value = datetime(year, month, day)
        except ValueError:
            continue
        iso = value.strftime("%Y-%m-%d")
        if iso not in dates:
            dates.append(iso)

    written_pattern = (
        r"\b(\d{1,2})\.\s*"
        r"(Januar|Februar|März|Maerz|April|Mai|Juni|"
        r"Juli|August|September|Oktober|November|Dezember)\b"
    )
    for match in re.finditer(written_pattern, t, re.IGNORECASE):
        day = int(match.group(1))
        month = GERMAN_MONTHS.get(match.group(2).casefold())
        if not month:
            continue
        try:
            value = datetime(default_year, month, day)
        except ValueError:
            continue
        iso = value.strftime("%Y-%m-%d")
        if iso not in dates:
            dates.append(iso)

    return dates


# ============================================================
# EMAIL AND SUBJECT KEYWORD
# ============================================================


def extract_email(text: str) -> str | None:
    pattern = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    match = re.search(pattern, text)
    return match.group(0) if match else None


def clean_subject(subject: str) -> str:
    subject = normalize_text(subject)
    subject = subject.strip(' "\'„“”‚‘’»«')
    return subject.strip()


def extract_subject_keyword(
    text: str,
    mailto_subject: str | None = None,
) -> str | None:
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

    keyword_quote_patterns = [
        r'(?:Stichwort|Suchwort|Keyword)\s*[:\-]?\s*[„“”"](.+?)[„“”"]',
        r'(?:Projekt(?:auswahl)?|Auswahl)\s*:\s*'
        r'(?:Stichwort|Suchwort|Keyword)\s*[:\-]?\s*[„“”"](.+?)[„“”"]',
    ]
    for pattern in keyword_quote_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            subject = clean_subject(match.group(1))
            if subject and len(subject) <= 150:
                return subject

    return None


# ============================================================
# EXTERNAL APPLICATION URL
# ============================================================


def extract_application_url(
    html: str,
    base_url: str | None = None,
) -> str | None:
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")
    candidates: list[tuple[int, str, str]] = []

    application_keywords = [
        "bewerb", "bewerben", "bewerbung", "apply", "application",
        "casting", "anmeldung", "registrieren", "formular", "form", "projekt",
    ]
    context_keywords = [
        "bewerbung", "bewerbungen", "bewerben", "homepage", "online",
        "formular", "website", "internet", "apply",
    ]
    excluded_domains = [
        "komparse.de", "facebook.com", "instagram.com", "youtube.com",
        "linkedin.com", "tiktok.com",
    ]

    for link in soup.find_all("a", href=True):
        href = link.get("href", "").strip()
        if not href:
            continue

        lower_href = href.casefold()
        if lower_href.startswith(("mailto:", "tel:", "javascript:")):
            continue

        if lower_href.startswith("//"):
            href = "https:" + href
        elif base_url:
            href = urljoin(base_url, href)

        if not re.match(r"^https?://", href, re.IGNORECASE):
            continue

        href_lower = href.casefold()
        if any(domain in href_lower for domain in excluded_domains):
            continue

        anchor_text = normalize_text(link.get_text(" ", strip=True)).casefold()
        score = 0
        for keyword in application_keywords:
            if keyword in href_lower:
                score += 10
            if keyword in anchor_text:
                score += 15

        parent_text = normalize_text(
            link.parent.get_text(" ", strip=True) if link.parent else ""
        ).casefold()
        nearby_text = parent_text
        if len(nearby_text) < 25 and link.parent:
            grandparent = link.parent.parent
            if grandparent:
                nearby_text = normalize_text(
                    grandparent.get_text(" ", strip=True)
                ).casefold()

        for keyword in context_keywords:
            if keyword in nearby_text:
                score += 5

        if score > 0:
            candidates.append((score, href, anchor_text))

    if candidates:
        candidates.sort(key=lambda item: (item[0], len(item[1])), reverse=True)
        return candidates[0][1]

    text = normalize_text(soup.get_text(" ", strip=True))
    url_pattern = (
        r"(https?://[^\s<>\]]+)"
        r"|"
        r"\b(?:www\.)[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?:/[^\s<>\]]*)?"
    )
    urls = re.findall(url_pattern, text, re.IGNORECASE)
    flat_urls: list[str] = []
    for item in urls:
        if isinstance(item, tuple):
            flat_urls.extend(value for value in item if value)
        elif item:
            flat_urls.append(item)

    for raw_url in flat_urls:
        candidate = raw_url.strip(".,;:()[]{}<>\"'")
        candidate_lower = candidate.casefold()
        if any(domain in candidate_lower for domain in excluded_domains):
            continue
        if any(keyword in candidate_lower for keyword in application_keywords):
            if candidate_lower.startswith("www."):
                return "https://" + candidate
            return candidate

    return None


def determine_application_method(
    email: str | None,
    application_url: str | None,
) -> str:
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


def parse_detail_page(
    html: str | None,
    base_url: str | None = None,
) -> dict:
    if not html:
        return {
            "detail_text": "",
            "email": None,
            "subject_keyword": None,
            "shoot_dates": [],
            "application_url": None,
            "application_method": "unknown",
        }

    soup = BeautifulSoup(html, "html.parser")
    detail_text = normalize_text(soup.get_text(" ", strip=True))
    email = None
    mailto_subject = None

    for link in soup.find_all("a", href=True):
        href = link["href"]
        if href.lower().startswith("mailto:"):
            mailto_data = href[7:]
            if "?" in mailto_data:
                address, query = mailto_data.split("?", 1)
                params = parse_qs(query)
                if "subject" in params:
                    mailto_subject = unquote(params["subject"][0])
                if not email:
                    email = address.strip()
            elif not email:
                email = mailto_data.strip()

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
            date_text = re.sub(
                r"^Termin\s*:\s*", "", clean_line, flags=re.IGNORECASE
            )
            shoot_dates = extract_shoot_dates(date_text)
            break

    return {
        "detail_text": detail_text,
        "email": email,
        "subject_keyword": subject_keyword,
        "shoot_dates": shoot_dates,
        "application_url": application_url,
        "application_method": application_method,
    }


# ============================================================
# PARSE ONE OFFER
# ============================================================


def parse_offer(offer: dict) -> dict:
    title = normalize_text(offer.get("title", ""))
    raw_text = normalize_text(offer.get("raw_text", ""))
    location_info = detect_location(title)

    publication_date = offer.get("publication_date")
    publication_year = None
    if publication_date:
        match = re.search(r"(\d{4})", str(publication_date))
        if match:
            publication_year = int(match.group(1))

    title_shoot_dates = extract_shoot_dates(
        title,
        default_year=publication_year,
    )
    profiles = extract_profiles(title)

    if len(profiles) == 1:
        age_min = profiles[0]["age_min"]
        age_max = profiles[0]["age_max"]
        gender = profiles[0]["gender"]
    else:
        age_min = None
        age_max = None
        all_genders = {
            gender_value
            for profile in profiles
            for gender_value in profile["gender"]
        }
        gender = sorted(all_genders)

    needs_review = not profiles or any(not profile["gender"] for profile in profiles)

    return {
        "komparse_id": offer.get("offer_id"),
        "title": title,
        "raw_text": raw_text,
        "publication_date": publication_date,
        "location_text": location_info["location_text"],
        "matches_mvp_location": location_info["matches_mvp"],
        "shoot_date": title_shoot_dates[0] if title_shoot_dates else None,
        "shoot_dates": title_shoot_dates,
        "age_min": age_min,
        "age_max": age_max,
        "gender": gender,
        "profiles": profiles,
        "email": None,
        "subject_keyword": None,
        "application_method": "unknown",
        "application_url": None,
        "detail_url": offer.get("detail_url"),
        "detail_text": "",
        "needs_review": needs_review,
    }


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
            parsed["detail_text"] = detail_data["detail_text"]
            parsed["email"] = detail_data["email"]
            parsed["subject_keyword"] = detail_data["subject_keyword"]
            parsed["application_url"] = detail_data["application_url"]
            parsed["application_method"] = detail_data["application_method"]

            if detail_data["shoot_dates"]:
                parsed["shoot_dates"] = detail_data["shoot_dates"]
                parsed["shoot_date"] = detail_data["shoot_dates"][0]

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
        print(f"Annonce : {offer['komparse_id']}")
        print(f"Publication : {offer['publication_date']}")
        print(f"Localisation : {offer['location_text']}")
        print(f"Dans zone MVP : {offer['matches_mvp_location']}")
        print(f"Date : {offer['shoot_date']}")
        print(f"Dates : {offer['shoot_dates']}")
        print(f"Âge : {offer['age_min']} - {offer['age_max']}")
        print(f"Sexe : {offer['gender']}")
        print(f"Profils : {offer['profiles']}")
        print(f"Email : {offer['email']}")
        print(f"Objet : {offer['subject_keyword']}")
        print(f"Méthode candidature : {offer['application_method']}")
        print(f"URL candidature : {offer['application_url']}")
        print(f"À vérifier : {offer['needs_review']}")
        print(f"Lien : {offer['detail_url']}")
        print("-" * 80)


if __name__ == "__main__":
    main()
