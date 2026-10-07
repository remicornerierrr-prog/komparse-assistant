import re
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime


URL = "https://komparse.de/hauptframe.htm"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# Mois allemands utilisés par Komparse
GERMAN_MONTHS = {
    "Januar": 1,
    "Februar": 2,
    "März": 3,
    "April": 4,
    "Mai": 5,
    "Juni": 6,
    "Juli": 7,
    "August": 8,
    "September": 9,
    "Oktober": 10,
    "November": 11,
    "Dezember": 12,
}


def download_page():
    """Télécharge la page principale de Komparse et la décode correctement."""

    response = requests.get(
        URL,
        headers=HEADERS,
        timeout=20
    )

    response.raise_for_status()

    # Komparse indique Windows-1252 dans son HTML.
    html = response.content.decode(
        "cp1252",
        errors="replace"
    )

    return html


def extract_offer_id(text):
    """
    Cherche le numéro d'annonce dans le bloc.
    Exemple : 91.309
    """

    match = re.search(r"\b(\d{2}\.\d{3})\b", text)

    if match:
        return match.group(1)

    return None


def extract_publication_date(text):
    """
    Extrait une date de publication du type :
    7. Oktober 2026 15:52
    """

    pattern = (
        r"(\d{1,2})\.\s*"
        r"(Januar|Februar|März|April|Mai|Juni|Juli|August|"
        r"September|Oktober|November|Dezember)"
        r"\s+(\d{4})\s+"
        r"(\d{1,2}:\d{2})"
    )

    match = re.search(pattern, text)

    if not match:
        return None

    day = int(match.group(1))
    month_name = match.group(2)
    year = int(match.group(3))
    time = match.group(4)

    month = GERMAN_MONTHS[month_name]

    return f"{year:04d}-{month:02d}-{day:02d} {time}"


def extract_offers(html):
    """Extrait les annonces individuelles de la page Komparse."""

    soup = BeautifulSoup(html, "html.parser")

    offers = []
    seen_offer_ids = set()

    # Chaque annonce possède un lien du type Gesuch91309.htm
    for link in soup.find_all("a", href=re.compile(r"^Gesuch\d+\.htm$", re.I)):

        href = link.get("href")
        p = link.find_parent("p")

        if p is None:
            continue

        # On remonte jusqu'au bloc <td> qui contient l'annonce.
        container = p.find_parent("td")

        if container is None:
            continue

        full_text = container.get_text(" ", strip=True)

        # Numéro de l'annonce affiché sur la page.
        # Important : on ne prend PAS le numéro du href.
        # Une annonce "Aktualisierung" peut pointer vers une ancienne annonce.
        offer_id = extract_offer_id(full_text)

        if offer_id is None:
            continue

        # Évite les doublons éventuels.
        if offer_id in seen_offer_ids:
            continue

        seen_offer_ids.add(offer_id)

        # Le <b> contient le titre / résumé principal de l'offre.
        bold = p.find("b")

        if bold:
            title = bold.get_text(" ", strip=True)
        else:
            title = p.get_text(" ", strip=True)

        # Nettoyage léger
        title = re.sub(r"\s+", " ", title).strip()

        publication_date = extract_publication_date(full_text)

        # URL complète vers la fiche de l'offre
        detail_url = requests.compat.urljoin(
            URL,
            href
        )

        offer = {
            "offer_id": offer_id,
            "publication_date": publication_date,
            "title": title,
            "detail_url": detail_url,
            "source_href": href,
            "raw_text": full_text,
        }

        offers.append(offer)

    return offers


def main():

    print("Téléchargement de Komparse...")
    html = download_page()

    print("Page téléchargée.")
    print("Analyse des annonces...")

    offers = extract_offers(html)

    print(f"\nNombre d'annonces trouvées : {len(offers)}")

    # Affichage dans le terminal
    print("\n" + "=" * 80)

    for offer in offers[:20]:

        print(f"ANNONCE : {offer['offer_id']}")
        print(f"Date   : {offer['publication_date']}")
        print(f"Titre  : {offer['title']}")
        print(f"Lien   : {offer['detail_url']}")
        print("-" * 80)

    # Sauvegarde JSON
    output_file = "komparse_offers.json"

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            offers,
            f,
            ensure_ascii=False,
            indent=4
        )

    print(f"\nFichier créé : {output_file}")


if __name__ == "__main__":
    main()