"""
Pipeline principal Komparse Assistant.

1. Récupère les annonces Komparse.
2. Parse les annonces.
3. Enregistre / met à jour les annonces dans Supabase.
4. Charge les profils.
5. Calcule les matches.
6. Crée les matches sans doublon.
7. Envoie une notification Web Push uniquement lorsqu'elle est nécessaire.

Les secrets sont uniquement lus depuis les variables
d'environnement GitHub Actions.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pywebpush import WebPushException, webpush
from supabase import Client, create_client

try:
    from .matching import match_offer_to_profile
    from .gender_flags import gender_flags_from_value
except ImportError:  # Support `python scraper/main.py` execution.
    from matching import match_offer_to_profile
    from gender_flags import gender_flags_from_value


# ============================================================
# CHEMINS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRAPER_DIR = PROJECT_ROOT / "scraper"
PARSED_OFFERS_FILE = PROJECT_ROOT / "komparse_parsed_offers.json"


# ============================================================
# VARIABLES D'ENVIRONNEMENT
# ============================================================

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY")
VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY")
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY")
VAPID_SUBJECT = os.environ.get("VAPID_SUBJECT")


# Diagnostic counters printed at the end of each GitHub Actions run.
NOTIFICATION_STATS = {
    "attempted": 0,
    "provider_accepted": 0,
    "failed": 0,
    "missing_subscription": 0,
    "invalid_subscription": 0,
    "already_marked_notified": 0,
    "manual_review": 0,
}


# ============================================================
# VALIDATION DE LA CONFIGURATION
# ============================================================

def validate_environment() -> None:
    required = {
        "SUPABASE_URL": SUPABASE_URL,
        "SUPABASE_SECRET_KEY": SUPABASE_SECRET_KEY,
        "VAPID_PUBLIC_KEY": VAPID_PUBLIC_KEY,
        "VAPID_PRIVATE_KEY": VAPID_PRIVATE_KEY,
        "VAPID_SUBJECT": VAPID_SUBJECT,
    }

    missing = [
        name
        for name, value in required.items()
        if not value
    ]

    if missing:
        raise RuntimeError(
            "Variables d'environnement manquantes : "
            + ", ".join(missing)
        )


# ============================================================
# CLIENT SUPABASE
# ============================================================

def create_supabase_client() -> Client:
    return create_client(
        SUPABASE_URL,
        SUPABASE_SECRET_KEY,
    )


# ============================================================
# LANCER LE SCRAPER EXISTANT
# ============================================================

def run_existing_scripts() -> None:
    print("=== 1. Récupération de Komparse ===")

    subprocess.run(
        [
            sys.executable,
            str(SCRAPER_DIR / "extract_offers.py"),
        ],
        cwd=str(PROJECT_ROOT),
        check=True,
    )

    print("=== 2. Parsing des offres ===")

    subprocess.run(
        [
            sys.executable,
            str(SCRAPER_DIR / "parser.py"),
        ],
        cwd=str(PROJECT_ROOT),
        check=True,
    )


# ============================================================
# CHARGER LES OFFRES PARSÉES
# ============================================================

def load_parsed_offers() -> list[dict[str, Any]]:
    if not PARSED_OFFERS_FILE.exists():
        raise FileNotFoundError(
            f"Fichier introuvable : {PARSED_OFFERS_FILE}"
        )

    with PARSED_OFFERS_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    if isinstance(data, list):
        return [
            item
            for item in data
            if isinstance(item, dict)
        ]

    if isinstance(data, dict):
        for key in (
            "offers",
            "results",
            "data",
        ):
            value = data.get(key)

            if isinstance(value, list):
                return [
                    item
                    for item in value
                    if isinstance(item, dict)
                ]

    raise ValueError(
        "Format inattendu dans "
        "komparse_parsed_offers.json"
    )


# ============================================================
# HELPERS
# ============================================================

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


# ============================================================
# GENRE DE L'OFFRE
# ============================================================

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


# ============================================================
# NORMALISER UNE OFFRE
# ============================================================

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


# ============================================================
# CHARGER LES PROFILS
# ============================================================

def load_profiles(
    supabase: Client,
) -> list[dict[str, Any]]:

    response = (
        supabase
        .table("profiles")
        .select(
            "id,first_name,last_name,email,phone,"
            "birth_date,gender,address,city,height_cm,"
            "shoe_size,clothing_size,profession"
        )
        .execute()
    )

    profiles = response.data or []

    print(
        f"{len(profiles)} profils chargés "
        "depuis Supabase."
    )

    return profiles


# ============================================================
# CHERCHER UNE OFFRE EXISTANTE
# ============================================================

def get_existing_offer(
    supabase: Client,
    komparse_id: str,
) -> dict[str, Any] | None:

    response = (
        supabase
        .table("offers")
        .select("*")
        .eq(
            "komparse_id",
            komparse_id,
        )
        .limit(1)
        .execute()
    )

    rows = response.data or []

    if not rows:
        return None

    return rows[0]


# ============================================================
# SAUVEGARDER / METTRE À JOUR UNE OFFRE
# ============================================================

def save_offer(
    supabase: Client,
    offer: dict[str, Any],
) -> tuple[int, bool]:

    existing = get_existing_offer(
        supabase,
        offer["komparse_id"],
    )

    payload = {
        "komparse_id": offer["komparse_id"],
        "title": offer["title"],
        "raw_text": offer["raw_text"],

        # Textes qui préservent les informations non normalisables
        # sans fabriquer une date exacte ou une tranche d'âge.
        "detail_text": offer["detail_text"],
        "shoot_date_text": offer["shoot_date_text"],
        "shoot_duration_text": offer["shoot_duration_text"],
        "age_description": offer["age_description"],
        "parser_needs_review": offer["parser_needs_review"],
        "parser_review_reason": offer["parser_review_reason"],

        "location_text": offer["location_text"],
        "location_status": offer["location_status"],
        "shoot_date": offer["shoot_date"],
        "age_min": offer["age_min"],
        "age_max": offer["age_max"],
        "gender_male": offer["gender_male"],
        "gender_female": offer["gender_female"],
        "email": offer["email"],
        "subject_keyword": offer["subject_keyword"],
        "application_method": offer["application_method"],
        "application_url": offer["application_url"],
        "source_url": offer["source_url"],
        "published_at": offer["published_at"],
        "updated_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }

    # --------------------------------------------------------
    # Offre existante
    # --------------------------------------------------------

    if existing:
        response = (
            supabase
            .table("offers")
            .update(payload)
            .eq(
                "id",
                existing["id"],
            )
            .execute()
        )

        rows = response.data or []

        if rows:
            return rows[0]["id"], False

        # Certains appels UPDATE peuvent ne pas retourner
        # de représentation de ligne. On recharge alors
        # l'offre pour obtenir son ID.
        refreshed = get_existing_offer(
            supabase,
            offer["komparse_id"],
        )

        if refreshed is None:
            raise RuntimeError(
                "La mise à jour de l'offre a échoué."
            )

        return refreshed["id"], False

    # --------------------------------------------------------
    # Nouvelle offre
    # --------------------------------------------------------

    response = (
        supabase
        .table("offers")
        .insert(payload)
        .execute()
    )

    rows = response.data or []

    if rows:
        return rows[0]["id"], True

    # Protection en cas de création concurrente.
    refreshed = get_existing_offer(
        supabase,
        offer["komparse_id"],
    )

    if refreshed is None:
        raise RuntimeError(
            "La création de l'offre a échoué."
        )

    return refreshed["id"], False


# ============================================================
# ADAPTER L'OFFRE POUR LE MATCHING
# ============================================================

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


# ============================================================
# CHERCHER UN MATCH EXISTANT
# ============================================================

def get_existing_match(
    supabase: Client,
    offer_id: int,
    user_id: str,
) -> dict[str, Any] | None:

    response = (
        supabase
        .table("matches")
        .select(
            "id,offer_id,user_id,reason,"
            "notified_at,application_status"
        )
        .eq("offer_id", offer_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )

    rows = response.data or []

    if not rows:
        return None

    return rows[0]


# ============================================================
# VÉRIFIER SI UN MATCH EXISTE
# ============================================================

def match_already_exists(
    supabase: Client,
    offer_id: int,
    user_id: str,
) -> bool:

    return (
        get_existing_match(
            supabase,
            offer_id,
            user_id,
        )
        is not None
    )


# ============================================================
# CRÉER UN MATCH
# ============================================================

def create_match(
    supabase: Client,
    offer_id: int,
    user_id: str,
    reason: dict[str, bool],
) -> tuple[int, bool]:

    existing = get_existing_match(
        supabase,
        offer_id,
        user_id,
    )

    if existing is not None:
        print(
            f"    Match déjà existant : "
            f"offer={offer_id} "
            f"user={user_id}"
        )

        return existing["id"], False

    response = (
        supabase
        .table("matches")
        .insert({
            "offer_id": offer_id,
            "user_id": user_id,
            "reason": reason,
            "application_status": "new",
        })
        .execute()
    )

    rows = response.data or []

    if not rows:
        raise RuntimeError(
            "Le match n'a pas pu être créé."
        )

    return rows[0]["id"], True


# ============================================================
# RÉCUPÉRER L'ABONNEMENT PUSH
# ============================================================

def get_push_subscription(
    supabase: Client,
    user_id: str,
) -> dict[str, Any] | None:

    response = (
        supabase
        .table("push_subscriptions")
        .select("id,subscription_json")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )

    rows = response.data or []

    if not rows:
        return None

    return rows[0]


# ============================================================
# ENVOYER UNE NOTIFICATION PUSH
# ============================================================

def send_push_notification(
    subscription: dict[str, Any],
    offer: dict[str, Any],
) -> bool:

    payload = {
        "title": "Nouvelle offre Komparse",
        "body": (
            offer["title"]
            or "Une offre correspond à votre profil."
        ),
        "url": offer["source_url"] or "/",
    }

    NOTIFICATION_STATS["attempted"] += 1

    try:
        response = webpush(
            subscription_info=subscription,
            data=json.dumps(
                payload,
                ensure_ascii=False,
            ),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims={
                "sub": VAPID_SUBJECT,
            },
        )
        NOTIFICATION_STATS["provider_accepted"] += 1
        status_code = getattr(response, "status_code", None)
        print(
            "    Passerelle push acceptée" +
            (f" (HTTP {status_code})" if status_code is not None else ".")
        )
        return True

    except WebPushException as error:
        NOTIFICATION_STATS["failed"] += 1
        response = getattr(error, "response", None)
        status_code = getattr(response, "status_code", None)
        print(
            "    Erreur Web Push : "
            + (f"HTTP {status_code} — " if status_code is not None else "")
            + str(error)
        )
        return False
    except Exception as error:
        NOTIFICATION_STATS["failed"] += 1
        print(f"    Erreur inattendue pendant l'envoi push : {error}")
        return False


# ============================================================
# NOTIFIER UN UTILISATEUR
# ============================================================

def notify_match_user(
    supabase: Client,
    user_id: str,
    offer: dict[str, Any],
) -> bool:

    subscription_row = get_push_subscription(
        supabase,
        user_id,
    )

    if not subscription_row:
        NOTIFICATION_STATS["missing_subscription"] += 1
        print(
            f"    Aucun abonnement push pour {user_id}"
        )

        return False

    subscription = subscription_row.get(
        "subscription_json"
    )

    if not isinstance(subscription, dict):
        NOTIFICATION_STATS["invalid_subscription"] += 1
        print(
            f"    subscription_json invalide pour {user_id}"
        )

        return False

    return send_push_notification(
        subscription,
        offer,
    )


# ============================================================
# MARQUER UN MATCH COMME NOTIFIÉ
# ============================================================

def mark_match_notified(
    supabase: Client,
    match_id: int,
) -> None:

    now = datetime.now(
        timezone.utc
    ).isoformat()

    (
        supabase
        .table("matches")
        .update({
            "notified_at": now,
        })
        .eq("id", match_id)
        .execute()
    )


# ============================================================
# TRAITER UNE OFFRE
# ============================================================

def process_offer(
    supabase: Client,
    raw_parsed_offer: dict[str, Any],
    profiles: list[dict[str, Any]],
) -> None:

    offer = normalize_offer(raw_parsed_offer)

    if not offer["komparse_id"]:
        print(
            "Offre ignorée : komparse_id absent."
        )

        return

    print()
    print(
        f"Offre {offer['komparse_id']} : "
        f"{offer['title']}"
    )

    print(
        f"  → Candidature : "
        f"{offer['application_method'] or 'unknown'}"
    )

    if offer["application_url"]:
        print(
            f"  → URL candidature : "
            f"{offer['application_url']}"
        )

    if offer["email"]:
        print(
            f"  → Email : "
            f"{offer['email']}"
        )

    if offer["subject_keyword"]:
        print(
            f"  → Mot-clé / objet : "
            f"{offer['subject_keyword']}"
        )

    offer_id, is_new = save_offer(
        supabase,
        offer,
    )

    print(
        f"  → Supabase offers.id = {offer_id}"
    )

    if is_new:
        print("  → Nouvelle offre")
    else:
        print("  → Offre existante mise à jour")

    # Traiter également les offres existantes pour
    # recréer les matches supprimés ou notifier les
    # matches existants dont notified_at est encore NULL.

    matching_offer = build_matching_offer(offer)

    for profile in profiles:
        try:
            result = match_offer_to_profile(
                matching_offer,
                profile,
            )

            if result is False:
                continue

            if result.get("matched") is not True:
                if result.get("manual_review"):
                    NOTIFICATION_STATS["manual_review"] += 1
                    print(
                        "    Revue manuelle requise pour ce profil : "
                        + str(result.get("manual_review_reason", "raison inconnue"))
                    )
                continue

            user_id = profile.get("id")

            if not user_id:
                continue

            reason = result.get(
                "reason",
                {
                    "location": True,
                    "age": True,
                    "gender": True,
                },
            )

            match_id, match_created = create_match(
                supabase,
                offer_id,
                user_id,
                reason,
            )

            if match_created:
                print(
                    f"  ✓ Match créé : "
                    f"match_id={match_id} "
                    f"user={user_id}"
                )

                match_row = {
                    "id": match_id,
                    "notified_at": None,
                }

            else:
                match_row = get_existing_match(
                    supabase,
                    offer_id,
                    user_id,
                )

                if match_row is None:
                    raise RuntimeError(
                        "Le match existe mais n'a pas pu "
                        "être relu."
                    )

            # `notified_at` signifie que la passerelle push avait accepté
            # l'envoi auparavant; cela ne garantit pas que le système
            # d'exploitation l'a effectivement affiché.
            if match_row.get("notified_at") is not None:
                NOTIFICATION_STATS["already_marked_notified"] += 1
                print(
                    f"    Notification ignorée : notified_at déjà renseigné "
                    f"({match_row.get('notified_at')})."
                )
                continue

            notified = notify_match_user(
                supabase,
                user_id,
                offer,
            )

            if notified:
                mark_match_notified(
                    supabase,
                    match_id,
                )

                print("    ✓ Notification push envoyée")
            else:
                print("    ! Notification non envoyée")

        except Exception as error:
            print(
                f"  ! Erreur pour le profil "
                f"{profile.get('id')} : {error}"
            )

            # Une erreur sur un profil ne bloque pas
            # le traitement des autres profils.


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    print("==========================================")
    print(" Komparse Assistant — pipeline principal")
    print("==========================================")

    validate_environment()

    supabase = create_supabase_client()

    # Scraper et parser.
    run_existing_scripts()

    # Charger les offres.
    parsed_offers = load_parsed_offers()

    print(
        f"\n{len(parsed_offers)} offres parsées."
    )

    # Charger les profils.
    profiles = load_profiles(supabase)

    # Traiter les offres.
    success_count = 0
    error_count = 0

    for raw_offer in parsed_offers:
        try:
            process_offer(
                supabase,
                raw_offer,
                profiles,
            )

            success_count += 1

        except Exception as error:
            error_count += 1

            print()
            print(
                "!!! Erreur traitement offre :",
                error,
            )

            # Une erreur sur une offre ne bloque pas
            # le traitement des suivantes.
            continue

    # Résumé.
    print()
    print("==========================================")
    print(f"Offres traitées : {success_count}")
    print(f"Offres en erreur : {error_count}")
    print("\nNotifications push — bilan :")
    print(f"  Tentatives d'envoi         : {NOTIFICATION_STATS['attempted']}")
    print(f"  Acceptées par la passerelle: {NOTIFICATION_STATS['provider_accepted']}")
    print(f"  Échecs d'envoi             : {NOTIFICATION_STATS['failed']}")
    print(f"  Sans abonnement enregistré: {NOTIFICATION_STATS['missing_subscription']}")
    print(f"  Abonnement invalide        : {NOTIFICATION_STATS['invalid_subscription']}")
    print(f"  Déjà marquées notifiées    : {NOTIFICATION_STATS['already_marked_notified']}")
    print(f"  Cas en revue manuelle      : {NOTIFICATION_STATS['manual_review']}")
    print("Pipeline terminé.")
    print("==========================================")

    # Le workflow GitHub Actions doit échouer si
    # certaines offres n'ont pas pu être traitées.
    if error_count > 0:
        raise RuntimeError(
            f"{error_count} offre(s) "
            "ont rencontré une erreur."
        )


# ============================================================
# POINT D'ENTRÉE
# ============================================================

if __name__ == "__main__":
    main()