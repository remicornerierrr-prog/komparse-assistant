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
import re
import unicodedata
from typing import Any

try:
    from .location_rules import classify_location
except ImportError:  # pragma: no cover - script execution path
    from location_rules import classify_location


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
    # Champ age_range éventuel
    # --------------------------------------------------------

    if (
        age_min is None
        and age_max is None
    ):

        raw_range = role_or_offer.get(
            "age_range"
        )


        if raw_range:

            numbers = re.findall(
                r"\d{1,3}",
                str(raw_range)
            )


            if len(numbers) >= 2:

                age_min = int(
                    numbers[0]
                )

                age_max = int(
                    numbers[1]
                )


            elif len(numbers) == 1:

                age_min = int(
                    numbers[0]
                )

                age_max = int(
                    numbers[0]
                )


    # --------------------------------------------------------
    # Champ age simple éventuel
    # --------------------------------------------------------

    if (
        age_min is None
        and age_max is None
        and role_or_offer.get("age")
    ):

        raw_age = role_or_offer.get(
            "age"
        )


        numbers = re.findall(
            r"\d{1,3}",
            str(raw_age)
        )


        if len(numbers) >= 2:

            age_min = int(
                numbers[0]
            )

            age_max = int(
                numbers[1]
            )

        elif len(numbers) == 1:

            age_min = int(
                numbers[0]
            )

            age_max = int(
                numbers[0]
            )


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


    # Hors bassin V1
    if location_status == "outside":

        return False


    # Localisation ambiguë
    if location_status == "manual_review":

        return {

            "matched": False,

            "manual_review": True,

            "reason": {

                "location": False,

                "age": False,

                "gender": False,

            },

            "manual_review_reason":
                "localisation_ambigue"

        }


    # ========================================================
    # 2. ÂGE À LA DATE DU TOURNAGE
    # ========================================================

    # Plusieurs dates possibles (ex. « 7. oder 8. November ») sont
    # conservées comme alternatives. Aucune date n'est inventée.
    raw_shoot_dates = offer.get("shoot_dates")
    if isinstance(raw_shoot_dates, list) and raw_shoot_dates:
        shoot_dates = raw_shoot_dates
    else:
        single_date = _get_shoot_date(offer)
        shoot_dates = [single_date] if single_date is not None else []

    birth_date = profile.get("birth_date")
    ages = [calculate_age_at_date(birth_date, value) for value in shoot_dates]

    if not ages or any(value is None for value in ages):
        return {
            "matched": False,
            "manual_review": True,
            "reason": {
                "location": True,
                "age": False,
                "gender": False,
            },
            "manual_review_reason": "age_ou_date_absente",
        }

    # Si les dates alternatives chevauchent l'anniversaire du profil,
    # les âges diffèrent. Le choix automatique serait incertain.
    if len(set(ages)) > 1:
        age_values = ages
    else:
        age_values = [ages[0]]
    age = ages[0]


    # ========================================================
    # 3. SEXE DU PROFIL
    # ========================================================

    profile_gender = _profile_gender(
        profile
    )


    if not profile_gender:

        return {

            "matched": False,

            "manual_review": True,

            "reason": {

                "location": True,

                "age": False,

                "gender": False,

            },

            "manual_review_reason":
                "sexe_profil_absent"

        }


    # ========================================================
    # 4. RÔLES DE L'ANNONCE
    # ========================================================

    roles = _extract_offer_roles(
        offer
    )


    # ========================================================
    # 5. TESTER CHAQUE RÔLE
    # ========================================================

    review_reasons: list[str] = []

    for role_index, role in enumerate(roles):
        age_min, age_max = _extract_age_range(role)
        offer_genders = _extract_offer_genders(role)

        # Une mention explicite de "gemischtes Alter" signifie que
        # l'offre cherche délibérément des âges variés. Elle peut donc
        # correspondre à différents âges sans inventer une tranche.
        varied_age = _is_varied_age_role(role, offer)
        if age_min is None and age_max is None:
            if varied_age:
                age_match = True
            else:
                review_reasons.append("age_annonce_non_precis")
                continue
        else:
            # Bornes ouvertes autorisées, par ex. "ab 35 Jahren".
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

        # Une désignation générique comme "Komparsen" ne suffit pas
        # à conclure que l'offre est réservée aux hommes ou aux femmes.
        # On signale le cas pour revue au lieu d'exclure silencieusement.
        if not offer_genders:
            review_reasons.append("sexe_annonce_non_precise")
            continue

        if profile_gender in offer_genders:
            return {
                "matched": True,
                "manual_review": False,
                "reason": {
                    "location": True,
                    "age": True,
                    "gender": True,
                },
                "profile_index": role_index,
                "matched_age": age,
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