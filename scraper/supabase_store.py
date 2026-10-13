"""Supabase persistence operations for Komparse Assistant."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from supabase import Client


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




def _preserve_existing_age_bounds(
    existing: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    """Keep manually corrected age bounds when a later parse finds no age."""
    if payload.get("age_min") is None and existing.get("age_min") is not None:
        payload["age_min"] = existing["age_min"]

    if (
        payload.get("age_min") is None
        and payload.get("age_max") is None
        and existing.get("age_max") is not None
    ):
        payload["age_max"] = existing["age_max"]

    if payload.get("age_min") is not None or payload.get("age_max") is not None:
        reasons = [
            item.strip()
            for item in str(payload.get("parser_review_reason") or "").split(",")
            if item.strip() and item.strip() != "age_non_numerique"
        ]
        payload["parser_review_reason"] = ", ".join(reasons) or None
        payload["parser_needs_review"] = bool(reasons)


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
        # Ne pas effacer une correction manuelle d'âge si le parseur
        # ne retrouve pas de tranche d'âge lors d'un scraping ultérieur.
        _preserve_existing_age_bounds(existing, payload)

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




def get_push_subscriptions(
    supabase: Client,
    user_id: str,
) -> list[dict[str, Any]]:
    """Retourne tous les navigateurs/appareils enregistrés pour cet utilisateur."""
    response = (
        supabase
        .table("push_subscriptions")
        .select("id,subscription_json,endpoint,device_id,device_label")
        .eq("user_id", user_id)
        .execute()
    )

    return response.data or []


def get_push_delivery(
    supabase: Client,
    match_id: int,
    subscription_id: int,
) -> dict[str, Any] | None:
    response = (
        supabase
        .table("match_push_deliveries")
        .select("id,match_id,push_subscription_id,status,attempts,sent_at,last_error")
        .eq("match_id", match_id)
        .eq("push_subscription_id", subscription_id)
        .limit(1)
        .execute()
    )

    rows = response.data or []
    return rows[0] if rows else None


def save_push_delivery(
    supabase: Client,
    match_id: int,
    subscription_id: int,
    status: str,
    attempts: int,
    last_error: str | None = None,
    sent_at: str | None = None,
) -> None:
    now = datetime.now(timezone.utc).isoformat()

    payload = {
        "match_id": match_id,
        "push_subscription_id": subscription_id,
        "status": status,
        "attempts": attempts,
        "last_attempt_at": now,
        "sent_at": sent_at,
        "last_error": last_error,
        "updated_at": now,
    }

    supabase.table("match_push_deliveries").upsert(
        payload,
        on_conflict="match_id,push_subscription_id",
    ).execute()


def delete_push_subscription(
    supabase: Client,
    subscription_id: int,
) -> None:
    supabase.table("push_subscriptions").delete().eq(
        "id", subscription_id
    ).execute()


# ============================================================
# ENVOYER UNE NOTIFICATION PUSH À UN APPAREIL
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
