"""
Moteur de matching V1 — Komparse Assistant

Règles V1 :
- Géographie :
    * Großraum Köln
    * Großraum Bonn
    * Großraum Düsseldorf
    * Großraum Köln/Bonn/Düsseldorf
    * Großraum Köln/Düsseldorf
    * Raum Köln
    * Köln & Umgebung
    * Köln und Umgebung
    * Köln +100 km
    * Köln +150 km
    * quelques variantes explicites Köln/Bonn
- NRW, Deutschlandweit, Bundesweit, etc. => manual_review
- Âge calculé à la date de tournage
- Sexe :
    * m = homme
    * w = femme
    * m/w = homme + femme
    * m/w/d = homme + femme
- Une offre peut contenir plusieurs rôles dans `profiles`
- Un seul match par couple (offer_id, user_id)
"""

from __future__ import annotations

from datetime import date, datetime
import os
import re
import unicodedata
from typing import Any

try:
    from .location_rules import classify_location
    from .notification_eligibility import profile_allows_offer_scope
    from .parser import extract_age_ranges
except ImportError:  # pragma: no cover - script execution path
    from location_rules import classify_location
    from notification_eligibility import profile_allows_offer_scope
    from parser import extract_age_ranges


def _env_bool(name: str, default: bool) -> bool:
    """Read a boolean environment variable without surprising truthiness."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().casefold() in {"1", "true", "yes", "on", "oui"}


# If an offer specifies no numeric age bounds, its age range is open by
# default. When gender is also unspecified, eligible-area profiles of any
# gender can match. Set NOTIFY_WHEN_AGE_UNSPECIFIED=false to restore manual
# review for offers with no numeric age information. Location eligibility
# and the pipeline's missing-exact-date review policy remain in force.
NOTIFY_WHEN_AGE_UNSPECIFIED = _env_bool(
    "NOTIFY_WHEN_AGE_UNSPECIFIED",
    True,
)


# ============================================================
# NORMALISATION
# ============================================================

def _normalize_text(value: Any) -> str:
    """
    Normalise un texte pour faciliter les comparaisons :
    - minuscules
    - suppression des accents
    - espaces normalisés
    - ß -> ss
    """

    if value is None:
        return ""

    text = str(value).strip().lower()

    text = text.replace("ß", "ss")

    text = unicodedata.normalize(
        "NFKD",
        text
    )

    text = "".join(
        char
        for char in text
        if not unicodedata.combining(char)
    )

    text = text.replace(
        "–",
        "-"
    ).replace(
        "—",
        "-"
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# GÉOGRAPHIE
# ============================================================

# Shared location classification lives in location_rules.py.
# Keeping the imported function name here preserves the public API used by tests.


# ============================================================
# DATES
# ============================================================

def _parse_date(
    value: Any
) -> date | None:
    """
    Accepte :
    - date
    - datetime
    - chaîne ISO YYYY-MM-DD
    - chaîne ISO datetime
    """

    if value is None:
        return None


    if isinstance(
        value,
        datetime
    ):

        return value.date()


    if isinstance(
        value,
        date
    ):

        return value


    text = str(
        value
    ).strip()


    if not text:
        return None


    # ISO datetime
    try:

        return datetime.fromisoformat(
            text.replace(
                "Z",
                "+00:00"
            )
        ).date()

    except ValueError:
        pass


    # ISO date
    try:

        return date.fromisoformat(
            text[:10]
        )

    except ValueError:
        return None


def calculate_age_at_date(
    birth_date: Any,
    reference_date: Any
) -> int | None:
    """
    Calcule l'âge exact du profil à une date donnée.
    """

    birth = _parse_date(
        birth_date
    )

    reference = _parse_date(
        reference_date
    )


    if (
        birth is None
        or reference is None
        or reference < birth
    ):

        return None


    age = (
        reference.year
        - birth.year
    )


    if (
        reference.month,
        reference.day
    ) < (
        birth.month,
        birth.day
    ):

        age -= 1


    return age


# ============================================================
# NOMBRES / ÂGES
# ============================================================

def _as_int(
    value: Any
) -> int | None:

    if value is None:
        return None


    if value == "":
        return None


    if isinstance(
        value,
        bool
    ):

        return None


    try:

        return int(
            value
        )

    except (
        TypeError,
        ValueError
    ):

        match = re.search(
            r"\d{1,3}",
            str(value)
        )


        if match:

            return int(
                match.group()
            )


    return None


def _parse_age_spec(value: Any) -> tuple[int | None, int | None]:
    """Parse bounded, open-ended, or exact age text without closing open bounds.

    Examples: ``25+`` and ``ab 25`` -> (25, None); ``bis 55`` -> (None, 55);
    ``25-55`` -> (25, 55); a bare ``35 Jahre`` -> (35, 35).
    """
    if value is None:
        return None, None

    text = _normalize_text(value)
    numbers = re.findall(r"\d{1,3}", text)
    if not numbers:
        return None, None

    if len(numbers) >= 2:
        return int(numbers[0]), int(numbers[1])

    number = int(numbers[0])

    if (
        "+" in text
        or re.search(r"\b(?:ab|mindestens|minimal|minimum|at least|from)\b", text)
    ):
        return number, None

    if re.search(r"\b(?:bis|maximal|hoechstens|maximal|maximum|at most|up to)\b", text):
        return None, number

    return number, number


def _extract_age_range(
    role_or_offer: dict[str, Any]
) -> tuple[int | None, int | None]:
    """
    Cherche la fourchette d'âge dans plusieurs noms de champs possibles.
    """

    min_keys = [

        "age_min",

        "min_age",

        "age_from",

        "minimum_age",

    ]


    max_keys = [

        "age_max",

        "max_age",

        "age_to",

        "maximum_age",

    ]


    age_min = None

    age_max = None


    # --------------------------------------------------------
    # Âge minimum
    # --------------------------------------------------------

    for key in min_keys:

        if (
            key in role_or_offer
            and role_or_offer.get(key)
            is not None
        ):

            age_min = _as_int(
                role_or_offer.get(key)
            )

            if age_min is not None:
                break


    # --------------------------------------------------------
    # Âge maximum
    # --------------------------------------------------------

    for key in max_keys:

        if (
            key in role_or_offer
            and role_or_offer.get(key)
            is not None
        ):

            age_max = _as_int(
                role_or_offer.get(key)
            )

            if age_max is not None:
                break


    # --------------------------------------------------------
    # Textual age fields, including open bounds such as "25+"
    # --------------------------------------------------------

    if age_min is None and age_max is None:
        raw_range = role_or_offer.get("age_range")
        if raw_range not in (None, ""):
            age_min, age_max = _parse_age_spec(raw_range)

    if (
        age_min is None
        and age_max is None
        and role_or_offer.get("age") not in (None, "")
    ):
        age_min, age_max = _parse_age_spec(role_or_offer.get("age"))

    return (
        age_min,
        age_max
    )


# ============================================================
# SEXE
# ============================================================

def _normalize_gender(
    value: Any
) -> set[str]:
    """
    Convertit les différentes formes rencontrées dans les annonces
    vers :

        male
        female

    m/w/d = homme + femme
    """

    if value is None:
        return set()


    # --------------------------------------------------------
    # Liste / tuple / set
    # --------------------------------------------------------

    if isinstance(
        value,
        (
            list,
            tuple,
            set
        )
    ):

        values = list(
            value
        )

    else:

        # On conserve les séparateurs classiques.
        values = re.split(
            r"[,;/+|]\s*|\s+",
            str(value)
        )


    normalized = set()


    for raw in values:

        text = _normalize_text(
            raw
        )


        if text in {
            "m",
            "male",
            "mann",
            "maennlich",
            "männlich",
        }:

            normalized.add(
                "male"
            )


        elif text in {
            "w",
            "female",
            "frau",
            "weiblich",
        }:

            normalized.add(
                "female"
            )


        elif text in {
            "d",
            "m/w",
            "w/m",
            "m/w/d",
            "w/m/d",
        }:

            normalized.update({
                "male",
                "female"
            })


    # --------------------------------------------------------
    # Détection directe d'une chaîne complète
    # --------------------------------------------------------

    whole = _normalize_text(
        value
    )


    if (
        "m/w/d" in whole
        or "w/m/d" in whole
    ):

        normalized.update({
            "male",
            "female"
        })


    elif (
        "m/w" in whole
        or "w/m" in whole
    ):

        normalized.update({
            "male",
            "female"
        })


    return normalized


def _extract_offer_genders(
    role_or_offer: dict[str, Any]
) -> set[str]:
    """
    Cherche le sexe dans plusieurs champs possibles.
    """

    possible_keys = [

        "genders",

        "gender",

        "sexes",

        "sex",

        "gender_requirements",

    ]


    for key in possible_keys:

        if (
            key in role_or_offer
            and role_or_offer.get(key)
            not in (
                None,
                ""
            )
        ):

            return _normalize_gender(
                role_or_offer.get(key)
            )


    return set()


def _profile_gender(
    profile: dict[str, Any]
) -> str:
    """
    Récupère le sexe du figurant.
    """

    value = (
        profile.get("gender")
        or profile.get("sex")
    )


    normalized = _normalize_gender(
        value
    )


    if "male" in normalized:
        return "male"


    if "female" in normalized:
        return "female"


    return ""


# ============================================================
# RÔLES D'UNE OFFRE
# ============================================================

def _extract_offer_roles(
    offer: dict[str, Any]
) -> list[dict[str, Any]]:
    """
    Une annonce peut contenir plusieurs rôles.

    Exemple :

    profiles = [
        {
            "role": "männlicher Patient",
            "age_min": 45,
            "age_max": 65,
            "genders": ["male"]
        },
        {
            "role": "weibliche Sprechstundenhilfe",
            "age_min": 25,
            "age_max": 35,
            "genders": ["female"]
        }
    ]
    """

    roles = offer.get(
        "profiles"
    )


    if (
        isinstance(
            roles,
            list
        )
        and roles
    ):

        valid_roles = [

            role

            for role in roles

            if isinstance(
                role,
                dict
            )

        ]


        if valid_roles:

            return valid_roles


    # Offre à rôle unique
    return [
        offer
    ]


# ============================================================
# DATE DE TOURNAGE
# ============================================================

def _get_shoot_date(
    offer: dict[str, Any]
) -> date | None:

    possible_keys = [

        "shoot_date",

        "shooting_date",

        "date",

        "shootingDate",

    ]


    for key in possible_keys:

        if offer.get(key):

            parsed = _parse_date(
                offer.get(key)
            )


            if parsed:

                return parsed


    return None


# ============================================================
# MATCH PRINCIPAL
# ============================================================

def _is_varied_age_role(role: dict[str, Any], offer: dict[str, Any]) -> bool:
    text = " ".join(
        str(value or "")
        for value in (
            role.get("age_description"),
            role.get("title"),
            role.get("role"),
            role.get("context"),
            offer.get("age_description"),
            offer.get("title"),
            offer.get("detail_text"),
            offer.get("raw_text"),
        )
    )
    text = _normalize_text(text)
    return bool(re.search(
        r"\b(?:gemischtes alter|altersgemischt|verschiedene altersgruppen|"
        r"alle altersgruppen|menschen jeden alters)\b",
        text,
    ))


def match_offer_to_profile(
    offer: dict[str, Any],
    profile: dict[str, Any]
) -> dict[str, Any] | bool:
    """
    Compare une annonce et un profil.

    Retourne :

    False
        lorsque l'offre est hors V1 ou qu'aucun rôle ne correspond.

    {
        "matched": False,
        "manual_review": True,
        ...
    }
        lorsqu'une décision automatique n'est pas suffisamment sûre.

    {
        "matched": True,
        "manual_review": False,
        "reason": {
            "location": True,
            "age": True,
            "gender": True
        }
    }
        lorsqu'il existe un match automatique.
    """

    # ========================================================
    # 1. GÉOGRAPHIE
    # ========================================================

    location = offer.get(
        "location",
        ""
    )


    location_status = classify_location(
        location
    )


    # Out-of-scope offers are rejected. Broad national/regional labels are
    # eligible only when the user explicitly enabled the corresponding scope.
    if location_status == "outside":
        return False

    if not profile_allows_offer_scope(location, profile):
        return False

    # Other ambiguous labels remain review-only unless the profile's explicit
    # regional preference and city compatibility make the scope actionable.
    if location_status == "manual_review":
        return {
            "matched": False,
            "manual_review": True,
            "reason": {"location": False, "age": False, "gender": False},
            "manual_review_reason": "localisation_ambigue",
        }


    # ========================================================
    # 2. DONNÉES D'ÂGE : CALCULER UNIQUEMENT SI NÉCESSAIRE
    # ========================================================

    # Plusieurs dates possibles (ex. « 7. oder 8. November ») restent des
    # alternatives. Une date n'est requise que pour un rôle avec une borne
    # numérique d'âge ; une annonce sans restriction d'âge n'a pas besoin
    # d'un âge calculé pour comparer le profil.
    raw_shoot_dates = offer.get("shoot_dates")
    if isinstance(raw_shoot_dates, list) and raw_shoot_dates:
        shoot_dates = raw_shoot_dates
    else:
        single_date = _get_shoot_date(offer)
        shoot_dates = [single_date] if single_date is not None else []

    birth_date = profile.get("birth_date")
    if shoot_dates:
        ages = [calculate_age_at_date(birth_date, value) for value in shoot_dates]
    else:
        # Sans date de tournage publiée, comparer avec l'âge actuel du profil.
        # C'est une approximation, mais la date manquante ne doit pas annuler
        # un match dont le lieu, l'âge et le sexe sont compatibles.
        ages = [calculate_age_at_date(birth_date, date.today())]
    age_values = ages if ages and all(value is not None for value in ages) else []
    age_for_result = age_values[0] if age_values else None

    # ========================================================
    # 3. SEXE DU PROFIL
    # ========================================================

    profile_gender = _profile_gender(profile)

    # ========================================================
    # 4. RÔLES DE L'ANNONCE
    # ========================================================

    roles = _extract_offer_roles(offer)

    # ========================================================
    # 5. TESTER CHAQUE RÔLE
    # ========================================================

    review_reasons: list[str] = []

    for role_index, role in enumerate(roles):
        age_min, age_max = _extract_age_range(role)
        if age_min is None and age_max is None:
            # Recover approximate age bands from descriptions like "Mitte 40"
            # when the role parser did not propagate numeric bounds.
            age_description_text = str(
                role.get("age_description")
                or role.get("context")
                or offer.get("age_description")
                or ""
            ).strip()
            if re.search(
                r"\b(?:Anfang|Mitte|Ende)\s+\d{2}\b",
                age_description_text,
                re.IGNORECASE,
            ):
                described_ranges = extract_age_ranges(age_description_text)
                if described_ranges:
                    age_min = described_ranges[0].get("min")
                    age_max = described_ranges[0].get("max")
        offer_genders = _extract_offer_genders(role)

        # Aucune borne numérique signifie une plage d'âge ouverte quand
        # NOTIFY_WHEN_AGE_UNSPECIFIED est activé. Une mention explicite
        # comme "gemischtes Alter" reste également une plage ouverte.
        varied_age = _is_varied_age_role(role, offer)
        age_unspecified = age_min is None and age_max is None

        if age_unspecified:
            age_description = str(
                role.get("age_description")
                or offer.get("age_description")
                or ""
            ).strip()
            if varied_age or not age_description:
                age_match = True
            else:
                # A descriptive label that cannot be mapped to a numeric
                # range remains uncertain; recognizable decade descriptions
                # have already been converted to bounds above.
                review_reasons.append("age_annonce_non_precis")
                continue
        else:
            # Toute borne numérique nécessite de connaître l'âge du profil
            # à la date du tournage. Une borne manquante reste ouverte.
            if not age_values:
                review_reasons.append("age_ou_date_absente")
                continue

            age_match_values = [
                (age_min is None or candidate_age >= age_min)
                and (age_max is None or candidate_age <= age_max)
                for candidate_age in age_values
            ]
            if any(age_match_values) and not all(age_match_values):
                review_reasons.append("date_ambigue_et_anniversaire")
                continue

            age_match = all(age_match_values)
            if not age_match:
                continue

        # If the notice does not specify gender, match profiles of every
        # gender; any explicit age bounds are still enforced above.
        if not offer_genders:
            gender_match = True
        else:
            if not profile_gender:
                review_reasons.append("sexe_profil_absent")
                continue
            gender_match = profile_gender in offer_genders
            if not gender_match:
                continue

        if age_match and gender_match:
            return {
                "matched": True,
                "manual_review": False,
                "reason": {
                    "location": True,
                    "age": True,
                    "gender": True,
                },
                "profile_index": role_index,
                "matched_age": age_for_result,
            }

    if review_reasons:
        unique_reasons = sorted(set(review_reasons))
        return {
            "matched": False,
            "manual_review": True,
            "reason": {
                "location": True,
                "age": "age_annonce_non_precis" not in unique_reasons,
                "gender": "sexe_annonce_non_precise" not in unique_reasons,
            },
            "manual_review_reason": ",".join(unique_reasons),
        }

    # Aucun rôle compatible.
    return False


# ============================================================
# MATCH D'UNE OFFRE CONTRE PLUSIEURS PROFILS
# ============================================================

def match_offer_to_profiles(
    offer: dict[str, Any],
    profiles: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """
    Compare une offre à plusieurs profils.

    Les cas manual_review sont volontairement exclus :
    ils ne doivent pas déclencher de notification automatique.
    """

    matches = []


    for profile in profiles:

        result = match_offer_to_profile(
            offer,
            profile
        )


        if (
            result is not False
            and result.get("matched") is True
        ):

            offer_id = (
                offer.get("id")
                or offer.get("offer_id")
            )


            user_id = (
                profile.get("id")
                or profile.get("user_id")
            )


            matches.append({

                "offer_id":
                    offer_id,

                "user_id":
                    user_id,

                "reason":
                    result["reason"],

                "profile_index":
                    result.get(
                        "profile_index"
                    ),

            })


    # Protection supplémentaire contre les doublons
    return deduplicate_matches(
        matches
    )


# ============================================================
# DÉDUPLICATION
# ============================================================

def deduplicate_matches(
    matches: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """
    Déduplique les résultats sur :

        (offer_id, user_id)

    La contrainte UNIQUE de Supabase reste la protection finale
    dans la base de données.
    """

    seen = set()

    unique_matches = []


    for match in matches:

        key = (
            match.get("offer_id"),
            match.get("user_id"),
        )


        if key in seen:

            continue


        seen.add(
            key
        )


        unique_matches.append(
            match
        )


    return unique_matches