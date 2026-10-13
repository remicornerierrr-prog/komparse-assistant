"""Web Push delivery and multi-device retry orchestration."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from supabase import Client


def send_push_notification(
    subscription: dict[str, Any],
    offer: dict[str, Any],
    *,
    webpush_func,
    webpush_exception,
    vapid_private_key: str | None,
    vapid_subject: str | None,
    ttl_seconds: int,
    stats: dict[str, int],
) -> tuple[bool, int | None, str | None]:
    payload = {
        "title": "Nouvelle offre Komparse",
        "body": (
            offer["title"]
            or "Une offre correspond à votre profil."
        ),
        "url": offer["source_url"] or "/",
    }

    stats["attempted"] += 1

    try:
        response = webpush_func(
            subscription_info=subscription,
            data=json.dumps(payload, ensure_ascii=False),
            vapid_private_key=vapid_private_key,
            vapid_claims={"sub": vapid_subject},
            ttl=ttl_seconds,
        )
        stats["provider_accepted"] += 1
        status_code = getattr(response, "status_code", None)
        print(
            "    Passerelle push acceptée"
            + (f" (HTTP {status_code})" if status_code is not None else ".")
        )
        return True, status_code, None

    except webpush_exception as error:
        stats["failed"] += 1
        response = getattr(error, "response", None)
        status_code = getattr(response, "status_code", None)
        message = str(error)
        print(
            "    Erreur Web Push : "
            + (f"HTTP {status_code} — " if status_code is not None else "")
            + message
        )
        return False, status_code, message

    except Exception as error:
        stats["failed"] += 1
        message = str(error)
        print(f"    Erreur inattendue pendant l'envoi push : {message}")
        return False, None, message


def notify_match_user(
    supabase: Client,
    user_id: str,
    offer: dict[str, Any],
    match_id: int,
    *,
    stats: dict[str, int],
    get_push_subscriptions,
    get_push_delivery,
    save_push_delivery,
    delete_push_subscription,
    send_push_notification,
) -> bool:
    """Envoie la notification à chaque abonnement sans dupliquer les envois réussis.

    `matches.notified_at` n'est marqué que lorsque tous les abonnements actifs
    connus ont une livraison réussie. Les échecs sont retentés aux exécutions
    suivantes, sans renvoyer aux appareils déjà servis.
    """
    subscriptions = get_push_subscriptions(supabase, user_id)

    if not subscriptions:
        stats["missing_subscription"] += 1
        print(f"    Aucun abonnement push pour {user_id}")
        return False

    stats["subscriptions_seen"] += len(subscriptions)

    for row in subscriptions:
        subscription_id = row.get("id")
        subscription = row.get("subscription_json")

        if not subscription_id or not isinstance(subscription, dict) or not subscription.get("endpoint"):
            stats["invalid_subscription"] += 1
            print(f"    Abonnement invalide (id={subscription_id}) ; suppression de la ligne invalide.")
            if subscription_id:
                delete_push_subscription(supabase, subscription_id)
            continue

        delivery = get_push_delivery(
            supabase,
            match_id,
            subscription_id,
        )

        if delivery and delivery.get("status") == "sent":
            stats["device_deliveries_already_sent"] += 1
            print(
                "    Livraison déjà réussie pour "
                + str(row.get("device_label") or f"abonnement {subscription_id}")
                + " ; aucun doublon envoyé."
            )
            continue

        attempts = int((delivery or {}).get("attempts") or 0) + 1
        save_push_delivery(
            supabase,
            match_id,
            subscription_id,
            status="pending",
            attempts=attempts,
        )

        success, status_code, error_message = send_push_notification(
            subscription,
            offer,
        )

        if success:
            save_push_delivery(
                supabase,
                match_id,
                subscription_id,
                status="sent",
                attempts=attempts,
                sent_at=datetime.now(timezone.utc).isoformat(),
            )
            print(
                "    ✓ Notification envoyée à "
                + str(row.get("device_label") or f"abonnement {subscription_id}")
            )
            continue

        if status_code in (404, 410):
            # Le service push confirme que cet endpoint n'existe plus.
            stats["expired_subscription"] += 1
            print(
                f"    Abonnement expiré (HTTP {status_code}) ; suppression de l'appareil {subscription_id}."
            )
            delete_push_subscription(supabase, subscription_id)
            continue

        save_push_delivery(
            supabase,
            match_id,
            subscription_id,
            status="failed",
            attempts=attempts,
            last_error=(error_message or f"Erreur HTTP {status_code}"),
        )

    # Recharger les abonnements actifs : certains endpoints ont pu expirer
    # et être supprimés pendant cette tentative.
    active_subscriptions = get_push_subscriptions(supabase, user_id)

    if not active_subscriptions:
        stats["missing_subscription"] += 1
        print("    Aucun abonnement push actif après nettoyage.")
        return False

    all_delivered = True
    for row in active_subscriptions:
        subscription_id = row.get("id")
        delivery = get_push_delivery(supabase, match_id, subscription_id)
        if not delivery or delivery.get("status") != "sent":
            all_delivered = False
            break

    if not all_delivered:
        stats["partial_delivery"] = stats.get("partial_delivery", 0) + 1
        print(
            "    Livraison partielle : les appareils non servis seront retentés "
            "lors d'une prochaine exécution."
        )

    return all_delivered
