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

def classify_location(location: Any) -> str:
    """
    Classe une localisation :

    - v1
        Localisation explicitement compatible avec le MVP.

    - manual_review
        Localisation potentiellement pertinente mais trop large
        ou ambiguë pour une notification automatique.

    - outside
        Localisation hors bassin V1 ou non reconnue.
    """

    text = _normalize_text(
        location
    )

    if not text:
        return "manual_review"


    # --------------------------------------------------------
    # Localisations ambiguës
    # --------------------------------------------------------

    manual_patterns = [

        r"^nrw\b",

        r"^nordrhein[- ]westfalen\b",

        r"^deutschlandweit\b",

        r"^bundesweit\b",

        r"^ganz deutschland\b",

        r"^deutschland$",

        r"^germany\b",

        r"^europaweit\b",

    ]


    for pattern in manual_patterns:

        if re.search(
            pattern,
            text
        ):

            return "manual_review"


    # --------------------------------------------------------
    # Localisations explicitement autorisées pour V1
    # --------------------------------------------------------

    allowed_patterns = [

        r"^grossraum koln$",

        r"^grossraum bonn$",

        r"^grossraum dusseldorf$",

        r"^grossraum koln/bonn/dusseldorf$",

        r"^grossraum koln/dusseldorf$",

        r"^grossraum bonn/dusseldorf$",

        r"^raum koln$",

        r"^koln\s*&\s*umgebung$",

        r"^koln\s+und\s+umgebung$",

        r"^koln\s*\+\s*100\s*km$",

        r"^koln\s*\+\s*150\s*km$",

        r"^koln/bonn$",

        r"^bonn/koln$",

    ]


    for pattern in allowed_patterns:

        if re.fullmatch(
            pattern,
            text
        ):

            return "v1"


    # --------------------------------------------------------
    # Tout le reste est considéré hors V1
    # --------------------------------------------------------

    return "outside"


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

    shoot_date = _get_shoot_date(
        offer
    )


    birth_date = profile.get(
        "birth_date"
    )


    age = calculate_age_at_date(
        birth_date,
        shoot_date
    )


    if age is None:

        return {

            "matched": False,

            "manual_review": True,

            "reason": {

                "location": True,

                "age": False,

                "gender": False,

            },

            "manual_review_reason":
                "age_ou_date_absente"

        }


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

    for role_index, role in enumerate(
        roles
    ):

        age_min, age_max = _extract_age_range(
            role
        )


        offer_genders = _extract_offer_genders(
            role
        )


        # ----------------------------------------------------
        # Impossible de valider automatiquement ce rôle
        # ----------------------------------------------------

        if (
            age_min is None
            or age_max is None
            or not offer_genders
        ):

            continue


        # ----------------------------------------------------
        # Âge
        # ----------------------------------------------------

        age_match = (
            age_min
            <= age
            <= age_max
        )


        # ----------------------------------------------------
        # Sexe
        # ----------------------------------------------------

        gender_match = (
            profile_gender
            in offer_genders
        )


        # ----------------------------------------------------
        # Match complet
        # ----------------------------------------------------

        if (
            age_match
            and gender_match
        ):

            return {

                "matched": True,

                "manual_review": False,

                "reason": {

                    "location": True,

                    "age": True,

                    "gender": True,

                },

                "profile_index":
                    role_index,

                "matched_age":
                    age,

            }


    # Aucun rôle compatible
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