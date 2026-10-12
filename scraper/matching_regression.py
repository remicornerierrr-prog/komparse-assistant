"""Dry-run regression on komparse_parsed_offers.json; does not access Supabase or send push."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from scraper.main import normalize_offer, prepare_offer_status, build_matching_offer
from scraper.matching import match_offer_to_profile, NOTIFY_WHEN_AGE_UNSPECIFIED

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "scraper" / "fixtures" / "komparse_parsed_offers.json"

# Deterministic sample profile matching existing test fixtures.
SAMPLE_PROFILE = {
    "id": "sample-female-30",
    "birth_date": "1996-06-15",
    "gender": "female",
    "city": "Köln",
}


def main() -> None:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Parsed offers file not found: {DATA_FILE}")

    records = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("Expected a JSON list in komparse_parsed_offers.json")

    counts = Counter()
    matched_ids: list[str] = []
    review_ids: list[tuple[str, str]] = []

    for raw in records:
        if not isinstance(raw, dict):
            continue

        offer = normalize_offer(raw)
        status = prepare_offer_status(offer)
        counts["offers_total"] += 1
        counts[f"status_{status}"] += 1

        if status == "outside":
            continue
        if status == "manual_review":
            continue

        result = match_offer_to_profile(build_matching_offer(offer), SAMPLE_PROFILE)
        if result is False:
            counts["eligible_but_no_match"] += 1
        elif result.get("matched") is True:
            counts["potential_match_offers"] += 1
            matched_ids.append(str(offer.get("komparse_id") or offer.get("title")))
        elif result.get("manual_review"):
            counts["profile_specific_manual_review"] += 1
            review_ids.append((
                str(offer.get("komparse_id") or "unknown"),
                str(result.get("manual_review_reason") or "unknown"),
            ))

    print("MATCHING REGRESSION — DRY RUN (aucun push envoyé)")
    print("Profil type : femme, née le 15/06/1996")
    print("Note : le matching actuel classe la zone de l’offre ; la ville du profil n’est pas utilisée dans cette simulation.")
    print(f"NOTIFY_WHEN_AGE_UNSPECIFIED={NOTIFY_WHEN_AGE_UNSPECIFIED}")
    print(f"Fichier analysé : {DATA_FILE.name}")
    for key in (
        "offers_total",
        "status_v1",
        "status_manual_review",
        "status_outside",
        "potential_match_offers",
        "eligible_but_no_match",
        "profile_specific_manual_review",
    ):
        print(f"{key}: {counts.get(key, 0)}")

    print("Potential match IDs: " + (", ".join(matched_ids) if matched_ids else "none"))
    if review_ids:
        print("Profile-specific manual-review cases:")
        for offer_id, reason in review_ids:
            print(f"  {offer_id}: {reason}")
    print("Note: these are potential match offers, not actual push deliveries; existing matches, notified_at, and device subscriptions are not queried.")


if __name__ == "__main__":
    main()
