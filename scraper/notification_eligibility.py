"""Eligibility rules for recent push notifications and profile geography."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

try:
    from .location_rules import normalize_location, is_nrw_location
except ImportError:
    from location_rules import normalize_location, is_nrw_location

BERLIN = ZoneInfo("Europe/Berlin")


def _published_date(value: Any) -> date | None:
    """Parse ISO publication dates/timestamps; unknown dates fail closed."""
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        return value
    else:
        text = str(value).strip()
        if not text:
            return None
        try:
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
                return date.fromisoformat(text)
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            match = re.fullmatch(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", text)
            if not match:
                return None
            try:
                return date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
            except ValueError:
                return None
    if isinstance(parsed, datetime):
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(BERLIN).date()
    return parsed


def is_offer_recent(published_at: Any, *, today: date | None = None) -> bool:
    """Only accept offers published today or yesterday in German local time."""
    publication_date = _published_date(published_at)
    current_date = today or datetime.now(BERLIN).date()
    return publication_date is not None and current_date - timedelta(days=1) <= publication_date <= current_date


def profile_allows_offer_scope(location: Any, profile: dict[str, Any]) -> bool:
    """Apply scope preferences and require the profile city to be covered.

    Nationwide announcements cover any city when the national option is enabled.
    NRW-wide announcements cover the currently supported MVP cities.
    Other regional/local labels must explicitly mention the profile city.
    """
    text = normalize_location(location)
    city = normalize_location(profile.get("city"))
    if not text or not city:
        return False

    national_labels = {"bundesweit", "deutschlandweit", "ganz deutschland", "deutschland", "germany"}
    if text in national_labels:
        return profile.get("notify_national", True) is not False

    # Une préférence NRW active couvre toutes les annonces identifiées comme NRW
    # ainsi que les annonces indiquant directement une ville du Land.
    if str(profile.get("notify_region") or "").strip().casefold() == "nrw":
        if is_nrw_location(text):
            return True

    # Sans préférence NRW, conserver le comportement géographique historique.
    is_nrw_scope = text in {"nrw", "nordrhein-westfalen", "nordrhein westfalen"}
    if is_nrw_scope:
        aliases = {"koln", "cologne", "koeln", "bonn", "dusseldorf", "duesseldorf"}
        city_key = {"cologne": "koln", "koeln": "koln", "duesseldorf": "dusseldorf"}.get(city, city)
        return profile.get("notify_regional", True) is not False and city_key in aliases

    if profile.get("notify_regional", True) is False:
        return False

    aliases = {
        "cologne": "koln",
        "koeln": "koln",
        "duesseldorf": "dusseldorf",
        "dusseldorf": "dusseldorf",
    }
    city = aliases.get(city, city)
    return bool(re.search(r"(?<!\w)" + re.escape(city) + r"(?!\w)", text))
