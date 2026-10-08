"""
Rapport QA du parsing Komparse.

Lecture de komparse_parsed_offers.json et génération
d'un rapport synthétique sur la qualité des données.

Ce script ne modifie aucune donnée.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent

INPUT_FILE = PROJECT_ROOT / "komparse_parsed_offers.json"


def load_offers() -> list[dict[str, Any]]:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Fichier introuvable : {INPUT_FILE}"
        )

    with INPUT_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(
            "komparse_parsed_offers.json doit contenir une liste."
        )

    return [
        item
        for item in data
        if isinstance(item, dict)
    ]


def is_present(value: Any) -> bool:
    if value is None:
        return False

    if isinstance(value, str):
        return bool(value.strip())

    if isinstance(value, list):
        return len(value) > 0

    return True


def percentage(
    value: int,
    total: int,
) -> float:
    if total == 0:
        return 0.0

    return round(
        (value / total) * 100,
        1,
    )


def print_metric(
    label: str,
    count: int,
    total: int,
) -> None:
    print(
        f"{label:<24} "
        f"{count:>3}/{total:<3} "
        f"({percentage(count, total):>5.1f} %)"
    )


def main() -> None:
    offers = load_offers()

    total = len(offers)

    print("=" * 80)
    print("KOMPARSE ASSISTANT — PARSER QA REPORT")
    print("=" * 80)
    print()

    print(f"Nombre total d'offres : {total}")
    print()

    # --------------------------------------------------------
    # COUVERTURE DES CHAMPS
    # --------------------------------------------------------

    fields = {
        "offer_id": lambda o: o.get("komparse_id"),
        "title": lambda o: o.get("title"),
        "publication_date": lambda o: o.get("publication_date"),
        "location_text": lambda o: o.get("location_text"),
        "shoot_date": lambda o: o.get("shoot_date"),
        "shoot_dates": lambda o: o.get("shoot_dates"),
        "age_min": lambda o: o.get("age_min"),
        "age_max": lambda o: o.get("age_max"),
        "gender": lambda o: o.get("gender"),
        "email": lambda o: o.get("email"),
        "subject_keyword": lambda o: o.get("subject_keyword"),
        "detail_url": lambda o: o.get("detail_url"),
    }

    print("COUVERTURE DES CHAMPS")
    print("-" * 80)

    for label, getter in fields.items():
        count = sum(
            1
            for offer in offers
            if is_present(getter(offer))
        )

        print_metric(
            label,
            count,
            total,
        )

    print()

    # --------------------------------------------------------
    # REVIEW
    # --------------------------------------------------------

    needs_review = [
        offer
        for offer in offers
        if offer.get("needs_review") is True
    ]

    print("ÉTAT DU PARSER")
    print("-" * 80)

    print_metric(
        "needs_review = true",
        len(needs_review),
        total,
    )

    location_ok = sum(
        1
        for offer in offers
        if offer.get("matches_mvp_location") is True
    )

    print_metric(
        "zone MVP reconnue",
        location_ok,
        total,
    )

    print()

    # --------------------------------------------------------
    # OFFRES SANS DATE DE TOURNAGE
    # --------------------------------------------------------

    missing_shoot_date = [
        offer
        for offer in offers
        if not is_present(
            offer.get("shoot_date")
        )
    ]

    print("OFFRES SANS DATE DE TOURNAGE")
    print("-" * 80)

    print(
        f"Nombre : {len(missing_shoot_date)}"
    )

    for offer in missing_shoot_date:
        print(
            f"- {offer.get('komparse_id')} | "
            f"{offer.get('title', '')}"
        )

    print()

    # --------------------------------------------------------
    # OFFRES SANS ÂGE
    # --------------------------------------------------------

    missing_age = [
        offer
        for offer in offers
        if (
            not is_present(offer.get("age_min"))
            or
            not is_present(offer.get("age_max"))
        )
    ]

    print("OFFRES SANS ÂGE COMPLET")
    print("-" * 80)

    print(
        f"Nombre : {len(missing_age)}"
    )

    for offer in missing_age:
        print(
            f"- {offer.get('komparse_id')} | "
            f"{offer.get('title', '')}"
        )

    print()

    # --------------------------------------------------------
    # OFFRES SANS SEXE
    # --------------------------------------------------------

    missing_gender = [
        offer
        for offer in offers
        if not is_present(
            offer.get("gender")
        )
    ]

    print("OFFRES SANS SEXE")
    print("-" * 80)

    print(
        f"Nombre : {len(missing_gender)}"
    )

    for offer in missing_gender:
        print(
            f"- {offer.get('komparse_id')} | "
            f"{offer.get('title', '')}"
        )

    print()

    # --------------------------------------------------------
    # OFFRES SANS EMAIL
    # --------------------------------------------------------

    missing_email = [
        offer
        for offer in offers
        if not is_present(
            offer.get("email")
        )
    ]

    print("OFFRES SANS EMAIL")
    print("-" * 80)

    print(
        f"Nombre : {len(missing_email)}"
    )

    for offer in missing_email:
        print(
            f"- {offer.get('komparse_id')} | "
            f"{offer.get('title', '')}"
        )

    print()

    # --------------------------------------------------------
    # OFFRES SANS SUJET
    # --------------------------------------------------------

    missing_subject = [
        offer
        for offer in offers
        if not is_present(
            offer.get("subject_keyword")
        )
    ]

    print("OFFRES SANS SUJET / MOT-CLE")
    print("-" * 80)

    print(
        f"Nombre : {len(missing_subject)}"
    )

    for offer in missing_subject:
        print(
            f"- {offer.get('komparse_id')} | "
            f"{offer.get('title', '')}"
        )

    print()

    # --------------------------------------------------------
    # SYNTHÈSE
    # --------------------------------------------------------

    print("=" * 80)
    print("SYNTHÈSE")
    print("=" * 80)

    print(
        f"Total offres analysées : {total}"
    )

    print(
        f"Besoin de revue parser : "
        f"{len(needs_review)}"
    )

    print(
        f"Sans date de tournage : "
        f"{len(missing_shoot_date)}"
    )

    print(
        f"Sans âge complet : "
        f"{len(missing_age)}"
    )

    print(
        f"Sans sexe : "
        f"{len(missing_gender)}"
    )

    print(
        f"Sans email : "
        f"{len(missing_email)}"
    )

    print(
        f"Sans sujet : "
        f"{len(missing_subject)}"
    )

    print("=" * 80)


if __name__ == "__main__":
    main()