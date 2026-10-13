"""Pure offer normalization and matching-adapter helpers.

Database writes, matching decisions and notification delivery remain in main.py.
"""

from __future__ import annotations

from typing import Any

try:
    from .gender_flags import gender_flags_from_value
except ImportError:  # Support direct execution from scraper/main.py.
    from gender_flags import gender_flags_from_value


def first_value(
    data: dict[str, Any],
    *keys: str,
    default: Any = None,
) -> Any:
    for key in keys:
        value = data.get(key)

        if value is not None:
            return value

    return default


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    if value is None:
        return False

    if isinstance(value, str):
        normalized = value.strip().lower()

        if normalized in {
            "true",
            "1",
            "yes",
            "oui",
        }:
            return True

        if normalized in {
            "false",
            "0",
            "no",
            "non",
            "",
        }:
            return False

    return bool(value)


def as_int(value: Any) -> int | None:
    if value is None:
        return None

    if isinstance(value, bool):
        return None

    if isinstance(value, int):
        return value

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def as_optional_string(value: Any) -> str | None:
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    return value

def extract_top_level_gender_flags(
    parsed: dict[str, Any],
) -> tuple[bool, bool]:
    """Read canonical labels accurately (especially female != male)."""
    gender_male = parsed.get("gender_male")
    gender_female = parsed.get("gender_female")

    if gender_male is not None or gender_female is not None:
        return as_bool(gender_male), as_bool(gender_female)

    gender_value = first_value(
        parsed,
        "gender",
        "genders",
        "sex",
        "sexes",
    )
    return gender_flags_from_value(gender_value)

def normalize_offer(
    parsed: dict[str, Any],
) -> dict[str, Any]:

    komparse_id = first_value(
        parsed,
        "komparse_id",
        "offer_id",
        "id",
    )

    title = first_value(
        parsed,
        "title",
        "name",
        default="",
    )

    raw_text = first_value(
        parsed,
        "raw_text",
        "text",
        default="",
    )

    # Nouveau : conserver le texte détaillé de l'annonce.
    # Il permet notamment de reconnaître les formulations
    # comme "gemischtes Alter" dans le tableau de bord.
    detail_text = first_value(
        parsed,
        "detail_text",
        default="",
    )

    shoot_date_text = as_optional_string(
        first_value(parsed, "shoot_date_text", default=None)
    )
    shoot_duration_text = as_optional_string(
        first_value(parsed, "shoot_duration_text", default=None)
    )
    age_description = as_optional_string(
        first_value(parsed, "age_description", default=None)
    )
    if not age_description:
        # Fail-safe in case the parser omitted a descriptive age label while
        # the source text still contains one, e.g. "gemischtes Alter".
        try:
            from .parser import extract_age_description
        except ImportError:
            from parser import extract_age_description
        age_source = " ".join((
            str(title or ""),
            str(raw_text or ""),
            str(detail_text or ""),
        ))
        age_description = as_optional_string(extract_age_description(age_source))
    parser_review_reason = as_optional_string(
        first_value(parsed, "parser_review_reason", default=None)
    )
    parser_needs_review = as_bool(
        first_value(parsed, "needs_review", "parser_needs_review", default=False)
    )

    location = first_value(
        parsed,
        "location",
        "location_text",
        "mvp_location",
        default="",
    )
    location_status = as_optional_string(
        first_value(parsed, "location_status", default=None)
    )

    shoot_date = first_value(
        parsed,
        "shoot_date",
        "shooting_date",
        "date",
    )

    age_min = as_int(
        first_value(
            parsed,
            "age_min",
            "min_age",
            "age_from",
        )
    )

    age_max = as_int(
        first_value(
            parsed,
            "age_max",
            "max_age",
            "age_to",
        )
    )

    # Fail safe: if neither numerical bounds nor an age description were
    # extracted, keep the offer visible for review instead of silently
    # treating it as complete.
    if age_min is None and age_max is None and not age_description:
        parser_needs_review = True
        reasons = [
            part.strip()
            for part in (parser_review_reason or "").split(",")
            if part.strip()
        ]
        if "age_non_numerique" not in reasons:
            reasons.append("age_non_numerique")
        parser_review_reason = ", ".join(reasons)

    (
        gender_male,
        gender_female,
    ) = extract_top_level_gender_flags(parsed)

    email = as_optional_string(
        first_value(
            parsed,
            "email",
            "recipient_email",
            default=None,
        )
    )

    subject_keyword = as_optional_string(
        first_value(
            parsed,
            "subject_keyword",
            "subject",
            "betreff",
            "kennwort",
            default=None,
        )
    )

    application_method = as_optional_string(
        first_value(
            parsed,
            "application_method",
            default=None,
        )
    )

    application_url = as_optional_string(
        first_value(
            parsed,
            "application_url",
            default=None,
        )
    )

    source_url = first_value(
        parsed,
        "source_url",
        "detail_url",
        "url",
        default="",
    )

    published_at = first_value(
        parsed,
        "published_at",
        "publication_date",
        "created_at",
    )

    return {
        "komparse_id": (
            str(komparse_id)
            if komparse_id is not None
            else ""
        ),
        "title": str(title or ""),
        "raw_text": str(raw_text or ""),

        # Nouveau champ transmis à Supabase.
        "detail_text": str(detail_text or ""),
        "shoot_date_text": shoot_date_text,
        "shoot_duration_text": shoot_duration_text,
        "age_description": age_description,
        "parser_needs_review": parser_needs_review,
        "parser_review_reason": parser_review_reason,

        "location_text": str(location or ""),
        "location_status": location_status,
        "shoot_date": shoot_date,
        "age_min": age_min,
        "age_max": age_max,
        "gender_male": gender_male,
        "gender_female": gender_female,
        "email": email,
        "subject_keyword": subject_keyword,
        "application_method": application_method,
        "application_url": application_url,
        "source_url": str(source_url or ""),
        "published_at": published_at,

        # On conserve les données originales du parser
        # pour gérer notamment plusieurs rôles.
        "parsed": parsed,
    }

def build_matching_offer(
    offer: dict[str, Any],
) -> dict[str, Any]:

    if offer["gender_male"] and offer["gender_female"]:
        genders = ["male", "female"]
    elif offer["gender_male"]:
        genders = ["male"]
    elif offer["gender_female"]:
        genders = ["female"]
    else:
        genders = []

    matching_offer = {
        "id": offer["komparse_id"],
        "offer_id": offer["komparse_id"],
        "title": offer["title"],
        "raw_text": offer["raw_text"],
        "detail_text": offer["detail_text"],
        "location": offer["location_text"],
        "location_text": offer["location_text"],
        "shoot_date": offer["shoot_date"],
        "shoot_dates": offer.get("parsed", {}).get("shoot_dates") or [],
        "shoot_date_text": offer["shoot_date_text"],
        "shoot_duration_text": offer["shoot_duration_text"],
        "age_min": offer["age_min"],
        "age_max": offer["age_max"],
        "age_description": offer["age_description"],
        "genders": genders,
        "email": offer["email"],
        "subject_keyword": offer["subject_keyword"],
        "application_method": offer["application_method"],
        "application_url": offer["application_url"],
        "source_url": offer["source_url"],
    }

    # --------------------------------------------------------
    # Préserver les rôles multiples du parser
    # --------------------------------------------------------

    original_profiles = (
        offer
        .get("parsed", {})
        .get("profiles")
    )

    if (
        isinstance(original_profiles, list)
        and original_profiles
    ):
        matching_profiles = []

        for role in original_profiles:
            if not isinstance(role, dict):
                continue

            role_copy = dict(role)
            if (
                role_copy.get("age_min") is None
                and role_copy.get("age_max") is None
                and offer.get("age_description")
            ):
                role_copy["age_description"] = offer["age_description"]

            # Le parser fournit actuellement `gender`.
            # Le matching accepte également `genders`.
            role_gender = role_copy.get("gender")

            if role_gender is not None:
                role_copy["genders"] = role_gender

            matching_profiles.append(role_copy)

        if matching_profiles:
            matching_offer["profiles"] = matching_profiles

    return matching_offer
