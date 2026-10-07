"""
Générateur de candidature email — Komparse Assistant

Le générateur :
- utilise le destinataire fourni par l'offre ;
- utilise le mot-clé / Betreff extrait de l'offre lorsqu'il existe ;
- utilise la date de tournage ;
- utilise les informations du profil ;
- conserve les chemins des 4 photos pour la préparation de la candidature.

Aucune information n'est inventée.
"""

from __future__ import annotations

from typing import Any


# ============================================================
# HELPERS
# ============================================================

def _value(
    data: dict[str, Any],
    *keys: str,
    default: str = ""
) -> str:
    """
    Retourne la première valeur non vide trouvée.
    """

    for key in keys:

        value = data.get(key)

        if value is not None and str(value).strip():

            return str(value).strip()

    return default


# ============================================================
# GÉNÉRATION DE LA CANDIDATURE
# ============================================================

def build_application(
    offer: dict[str, Any],
    profile: dict[str, Any],
    photo_paths: list[str]
) -> dict[str, Any]:
    """
    Construit une candidature prête à prévisualiser.

    Retourne :

    {
        "to": "...",
        "subject": "...",
        "body": "...",
        "attachments": [...]
    }
    """

    # --------------------------------------------------------
    # DESTINATAIRE
    # --------------------------------------------------------

    recipient = _value(
        offer,
        "email",
        "recipient_email"
    )


    # --------------------------------------------------------
    # DATE DE TOURNAGE
    # --------------------------------------------------------

    shoot_date = _value(
        offer,
        "shoot_date",
        "shooting_date",
        "date"
    )


    # --------------------------------------------------------
    # OBJET / BETREFF
    # --------------------------------------------------------

    subject_keyword = _value(
        offer,
        "subject_keyword",
        "subject",
        "betreff",
        "kennwort"
    )


    if subject_keyword:

        subject = subject_keyword

    else:

        subject = (
            f"Bewerbung Komparse {shoot_date}"
            if shoot_date
            else "Bewerbung Komparse"
        )


    # --------------------------------------------------------
    # INFORMATIONS DU PROFIL
    # --------------------------------------------------------

    first_name = _value(
        profile,
        "first_name"
    )


    last_name = _value(
        profile,
        "last_name"
    )


    full_name = (
        f"{first_name} {last_name}"
    ).strip()


    city = _value(
        profile,
        "city"
    )


    phone = _value(
        profile,
        "phone"
    )


    birth_date = _value(
        profile,
        "birth_date"
    )


    clothing_size = _value(
        profile,
        "clothing_size"
    )


    height_cm = _value(
        profile,
        "height_cm"
    )


    shoe_size = _value(
        profile,
        "shoe_size"
    )


    # --------------------------------------------------------
    # RÔLE ÉVENTUEL
    # --------------------------------------------------------

    role = _value(
        offer,
        "role",
        "requested_role"
    )


    # --------------------------------------------------------
    # MESSAGE
    # --------------------------------------------------------

    introduction = (
        "ich möchte mich gerne für den Einsatz "
        "als Komparse"
    )


    if role:

        introduction += (
            f" als {role}"
        )


    if shoot_date:

        introduction += (
            f" am {shoot_date}"
        )


    introduction += (
        " bewerben."
    )


    body = (
        "Hallo,\n"
        "\n"
        f"{introduction}\n"
        "\n"
        "Nachfolgend finden Sie meine vollständigen Angaben:\n"
        "\n"
        f"Vollständiger Name: {full_name}\n"
        f"Wohnort: {city}\n"
        f"Telefon: {phone}\n"
        f"Geburtsdatum: {birth_date}\n"
        f"Kleidergröße: {clothing_size}\n"
        f"Größe: {height_cm} cm\n"
        f"Schuhgröße: {shoe_size}\n"
        "\n"
        "Vielen Dank.\n"
        "\n"
        "Mit freundlichen Grüßen,\n"
        f"{full_name}\n"
    )


    # --------------------------------------------------------
    # RÉSULTAT
    # --------------------------------------------------------

    return {

        "to":
            recipient,

        "subject":
            subject,

        "body":
            body,

        "attachments":
            list(photo_paths),

    }