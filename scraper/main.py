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
    from .matching import match_offer_to_profile, NOTIFY_WHEN_AGE_UNSPECIFIED
    from .location_rules import classify_location
    from .parser import is_varied_age_description
    from .offer_data import (
        as_bool,
        as_int,
        as_optional_string,
        build_matching_offer,
        extract_top_level_gender_flags,
        first_value,
        normalize_offer,
    )
    from . import notifications
    from .notification_eligibility import is_offer_recent, profile_allows_offer_scope
    from .supabase_store import (
        create_match,
        delete_push_subscription,
        get_existing_match,
        get_existing_offer,
        apply_admin_qualification,
        get_push_delivery,
        get_push_subscriptions,
        load_profiles,
        mark_match_notified,
        match_already_exists,
        save_offer,
        save_push_delivery,
    )
except ImportError:  # Support `python scraper/main.py` execution.
    from matching import match_offer_to_profile, NOTIFY_WHEN_AGE_UNSPECIFIED
    from location_rules import classify_location
    from parser import is_varied_age_description
    from offer_data import (
        as_bool,
        as_int,
        as_optional_string,
        build_matching_offer,
        extract_top_level_gender_flags,
        first_value,
        normalize_offer,
    )
    import notifications
    from notification_eligibility import is_offer_recent, profile_allows_offer_scope
    from supabase_store import (
        create_match,
        delete_push_subscription,
        get_existing_match,
        get_existing_offer,
        apply_admin_qualification,
        get_push_delivery,
        get_push_subscriptions,
        load_profiles,
        mark_match_notified,
        match_already_exists,
        save_offer,
        save_push_delivery,
    )


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
# Keep push messages queued for up to 72 hours when a browser/device is offline.
# pywebpush defaults to TTL=0, which discards messages immediately if the
# recipient is unavailable at delivery time.
PUSH_TTL_SECONDS = 72 * 60 * 60

NOTIFICATION_STATS = {
    "attempted": 0,
    "provider_accepted": 0,
    "failed": 0,
    "missing_subscription": 0,
    "invalid_subscription": 0,
    "expired_subscription": 0,
    "subscriptions_seen": 0,
    "device_deliveries_already_sent": 0,
    "partial_delivery": 0,
    "already_marked_notified": 0,
    "manual_review": 0,
}

# Run-level counters are per unique offer, not per profile or device.
# Their categories are exclusive: an offer is counted as outside, manual
# review, notified, matched-without-delivery, or no-profile-match.
OFFER_STATUS_STATS = {
    "processed": 0,
    "notified": 0,
    "manual_review": 0,
    "outside": 0,
    "matched_without_notification": 0,
    "no_profile_match": 0,
    "too_old_for_push": 0,
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

def prepare_offer_status(offer: dict[str, Any]) -> str:
    """Classify an offer once for this run and persist review reasons.

    Returns ``v1``, ``manual_review`` or ``outside``. Ambiguous locations
    remain in manual review; a missing exact shoot date alone does not block V1.
    """
    location_status = classify_location(offer.get("location_text"))
    offer["location_status"] = location_status

    # An irrelevant geographic offer remains outside even if its parser has
    # other missing fields: don't mix out-of-scope and manual-review totals.
    if location_status == "outside":
        return "outside"

    reasons = {
        part.strip()
        for part in str(offer.get("parser_review_reason") or "").split(",")
        if part.strip()
    }

    if location_status == "manual_review":
        reasons.add("localisation_ambigue")
    else:
        reasons.discard("localisation_ambigue")

    has_exact_date = offer.get("shoot_date") not in (None, "")

    # Une date de tournage absente ne bloque pas le matching V1 : le lieu,
    # l'âge et le sexe restent les critères de correspondance. On conserve
    # l'information dans les champs de date et le tableau de bord, mais on
    # n'en fait pas à elle seule un motif de blocage des notifications.
    reasons.discard("date_exacte_absente")

    # The top-level age bounds can be empty for multi-role offers even when
    # the individual roles have numerical ranges. In that case, the offer is
    # not age-unspecified as a whole.
    top_level_has_age = (
        offer.get("age_min") is not None
        or offer.get("age_max") is not None
    )
    parsed_roles = (offer.get("parsed") or {}).get("profiles") or []
    role_has_age = any(
        isinstance(role, dict)
        and (
            role.get("age_min") is not None
            or role.get("age_max") is not None
            or role.get("min_age") is not None
            or role.get("max_age") is not None
        )
        for role in parsed_roles
    )
    age_unbounded = not top_level_has_age and not role_has_age
    age_description = offer.get("age_description")
    explicit_varied_age = is_varied_age_description(age_description)
    open_age_policy = age_unbounded and (
        explicit_varied_age
        or (
            NOTIFY_WHEN_AGE_UNSPECIFIED
            and not age_description
        )
    )

    # Under the explicit open-age policy, absence of a numeric age is not
    # itself a reason to block matching. If gender is also unspecified, the
    # matcher may consider every profile gender. Missing exact dates are
    # handled separately above and do not, by themselves, block V1 matching.
    if open_age_policy:
        reasons.discard("age_non_numerique")
        if not offer.get("gender_male") and not offer.get("gender_female"):
            reasons.discard("sexe_annonce_non_precise")

    # Si la date est la seule information manquante, le drapeau général du
    # parseur ne doit pas réintroduire un blocage artificiel. Les autres
    # motifs de vérification restent bloquants.
    if as_bool(offer.get("parser_needs_review")) and not reasons and not open_age_policy and has_exact_date:
        if not offer.get("gender_male") and not offer.get("gender_female"):
            reasons.add("sexe_annonce_non_precise")
        elif age_unbounded and not offer.get("age_description"):
            reasons.add("age_non_numerique")
        else:
            reasons.add("verification_parser")

    requires_review = bool(reasons) or (
        as_bool(offer.get("parser_needs_review"))
        and not open_age_policy
        and has_exact_date
    )
    offer["parser_needs_review"] = requires_review
    offer["parser_review_reason"] = ", ".join(sorted(reasons)) or None

    return "manual_review" if requires_review else "v1"


# ============================================================
# GENRE DE L'OFFRE
# ============================================================

# ============================================================
# CHARGER LES PROFILS
# ============================================================

def send_push_notification(
    subscription: dict[str, Any],
    offer: dict[str, Any],
) -> tuple[bool, int | None, str | None]:
    """Keep the public pipeline hook while delegating delivery details."""
    return notifications.send_push_notification(
        subscription,
        offer,
        webpush_func=webpush,
        webpush_exception=WebPushException,
        vapid_private_key=VAPID_PRIVATE_KEY,
        vapid_subject=VAPID_SUBJECT,
        ttl_seconds=PUSH_TTL_SECONDS,
        stats=NOTIFICATION_STATS,
    )


def notify_match_user(
    supabase: Client,
    user_id: str,
    offer: dict[str, Any],
    match_id: int,
) -> bool:
    """Keep dependency injection points available to existing tests."""
    return notifications.notify_match_user(
        supabase,
        user_id,
        offer,
        match_id,
        stats=NOTIFICATION_STATS,
        get_push_subscriptions=get_push_subscriptions,
        get_push_delivery=get_push_delivery,
        save_push_delivery=save_push_delivery,
        delete_push_subscription=delete_push_subscription,
        send_push_notification=send_push_notification,
    )


def process_offer(
    supabase: Client,
    raw_parsed_offer: dict[str, Any],
    profiles: list[dict[str, Any]],
) -> None:

    offer = normalize_offer(raw_parsed_offer)

    if not offer["komparse_id"]:
        print("Offre ignorée : komparse_id absent.")
        return

    # A human qualification is authoritative over future automatic parses.
    existing_offer = get_existing_offer(supabase, offer["komparse_id"])
    apply_admin_qualification(offer, existing_offer)

    offer_status = prepare_offer_status(offer)
    OFFER_STATUS_STATS["processed"] += 1

    print()
    print(
        f"Offre {offer['komparse_id']} : "
        f"{offer['title']}"
    )
    print(f"  → Statut géographique : {offer_status} ({offer['location_text'] or 'localisation absente'})")

    if offer["application_method"]:
        print(f"  → Candidature : {offer['application_method']}")
    if offer["application_url"]:
        print(f"  → URL candidature : {offer['application_url']}")
    if offer["email"]:
        print(f"  → Email : {offer['email']}")
    if offer["subject_keyword"]:
        print(f"  → Mot-clé / objet : {offer['subject_keyword']}")

    # Save the decision before returning so the admin dashboard can show it.
    offer_id, is_new = save_offer(supabase, offer)
    print(f"  → Supabase offers.id = {offer_id}")
    print("  → Nouvelle offre" if is_new else "  → Offre existante mise à jour")

    if offer_status == "outside":
        OFFER_STATUS_STATS["outside"] += 1
        print(f"  STATUT FINAL: HORS ZONE — aucun matching ni notification (ID {offer['komparse_id']}).")
        return

    if offer_status == "manual_review":
        OFFER_STATUS_STATS["manual_review"] += 1
        print(
            f"  STATUT FINAL: MANUAL_REVIEW — "
            f"{offer.get('parser_review_reason') or 'données insuffisantes'} "
            f"(ID {offer['komparse_id']})."
        )
        return

    # Only offers published today or yesterday may create matches or push alerts.
    # Missing or unparsable publication dates fail closed to prevent stale alerts.
    if not is_offer_recent(offer.get("published_at")):
        OFFER_STATUS_STATS["too_old_for_push"] += 1
        print(
            f"  STATUT FINAL: TROP ANCIENNE / DATE DE PUBLICATION ABSENTE — "
            f"aucun match ni push (ID {offer['komparse_id']}, "
            f"publication={offer.get('published_at')!r})."
        )
        return

    matching_offer = build_matching_offer(offer)
    offer_was_notified = False
    any_profile_review = False
    matched_profile_count = 0
    review_reasons: set[str] = set()

    for profile in profiles:
        try:
            if not profile_allows_offer_scope(offer.get("location_text"), profile):
                print(
                    "    Offre ignorée pour le profil "
                    f"{profile.get('id')} : portée géographique non autorisée "
                    "ou ville non correspondante."
                )
                continue

            result = match_offer_to_profile(matching_offer, profile)

            if result is False:
                continue

            if result.get("matched") is not True:
                if result.get("manual_review"):
                    NOTIFICATION_STATS["manual_review"] += 1
                    any_profile_review = True
                    reason_text = str(result.get("manual_review_reason", "raison inconnue"))
                    review_reasons.update(
                        reason.strip()
                        for reason in reason_text.split(",")
                        if reason.strip()
                    )
                    print(
                        "    Profil en revue manuelle : "
                        + f"user={profile.get('id')} — {reason_text}"
                    )
                continue

            user_id = profile.get("id")
            if not user_id:
                print("    Match éligible mais ID utilisateur absent : notification impossible.")
                continue

            matched_profile_count += 1
            reason = result.get(
                "reason",
                {"location": True, "age": True, "gender": True},
            )

            match_id, match_created = create_match(
                supabase, offer_id, user_id, reason
            )

            if match_created:
                print(
                    f"  ✓ Match créé : match_id={match_id} user={user_id}"
                )
                match_row = {"id": match_id, "notified_at": None}
            else:
                match_row = get_existing_match(supabase, offer_id, user_id)
                if match_row is None:
                    raise RuntimeError(
                        "Le match existe mais n'a pas pu être relu."
                    )

            # A previously successful match is still counted as notified
            # for this offer, but we never send a duplicate.
            if match_row.get("notified_at") is not None:
                NOTIFICATION_STATS["already_marked_notified"] += 1
                offer_was_notified = True
                print(
                    "    Notification déjà enregistrée : "
                    f"notified_at={match_row.get('notified_at')}"
                )
                continue

            accepted_before = NOTIFICATION_STATS["provider_accepted"]
            all_devices_notified = notify_match_user(
                supabase, user_id, offer, match_id
            )
            newly_accepted = (
                NOTIFICATION_STATS["provider_accepted"] > accepted_before
            )

            if all_devices_notified:
                mark_match_notified(supabase, match_id)
                offer_was_notified = True
                print("    ✓ Notification envoyée à tous les appareils actifs")
            elif newly_accepted:
                # A partial delivery still means at least one device was served.
                offer_was_notified = True
                print("    ! Notification acceptée sur au moins un appareil ; d'autres restent à retenter")
            else:
                print("    ! Aucun appareil confirmé livré pour ce match")

        except Exception as error:
            print(
                f"  ! Erreur pour le profil {profile.get('id')} : {error}"
            )

    # Count each offer once, never once per profile/device.
    if offer_was_notified:
        OFFER_STATUS_STATS["notified"] += 1
        print(f"  STATUT FINAL: NOTIFIÉE (ID {offer['komparse_id']}).")
    elif matched_profile_count > 0:
        OFFER_STATUS_STATS["matched_without_notification"] += 1
        print(
            f"  STATUT FINAL: MATCH TROUVÉ MAIS LIVRAISON NON CONFIRMÉE "
            f"(ID {offer['komparse_id']})."
        )
    elif any_profile_review:
        OFFER_STATUS_STATS["manual_review"] += 1
        print(
            f"  STATUT FINAL: MANUAL_REVIEW — "
            f"{', '.join(sorted(review_reasons)) or 'cas de matching incertain'} "
            f"(ID {offer['komparse_id']})."
        )
    else:
        OFFER_STATUS_STATS["no_profile_match"] += 1
        print(
            f"  STATUT FINAL: AUCUN PROFIL COMPATIBLE — "
            f"aucune notification créée (ID {offer['komparse_id']})."
        )


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
    print("\nStatut des offres (comptées une fois par annonce) :")
    print(f"  Notifiées                 : {OFFER_STATUS_STATS['notified']}")
    print(f"  Manual review             : {OFFER_STATUS_STATS['manual_review']}")
    print(f"  Hors zone                 : {OFFER_STATUS_STATS['outside']}")
    print(f"  Match trouvé, sans livraison confirmée : {OFFER_STATUS_STATS['matched_without_notification']}")
    print(f"  Aucun profil compatible  : {OFFER_STATUS_STATS['no_profile_match']}")
    print(f"  Trop anciennes / date absente : {OFFER_STATUS_STATS['too_old_for_push']}")
    print("\nNotifications push — bilan par tentative/appareil :")
    print(f"  Tentatives d'envoi         : {NOTIFICATION_STATS['attempted']}")
    print(f"  Acceptées par la passerelle: {NOTIFICATION_STATS['provider_accepted']}")
    print(f"  Échecs d'envoi             : {NOTIFICATION_STATS['failed']}")
    print(f"  Sans abonnement enregistré: {NOTIFICATION_STATS['missing_subscription']}")
    print(f"  Abonnement invalide        : {NOTIFICATION_STATS['invalid_subscription']}")
    print(f"  Abonnement expiré supprimé : {NOTIFICATION_STATS['expired_subscription']}")
    print(f"  Appareils ciblés            : {NOTIFICATION_STATS['subscriptions_seen']}")
    print(f"  Appareils déjà servis       : {NOTIFICATION_STATS['device_deliveries_already_sent']}")
    print(f"  Livraisons partielles       : {NOTIFICATION_STATS['partial_delivery']}")
    print(f"  Déjà marquées notifiées    : {NOTIFICATION_STATS['already_marked_notified']}")
    print(f"  Revue manuelle par profil  : {NOTIFICATION_STATS['manual_review']}")
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