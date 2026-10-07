import re
import json
import requests
from bs4 import BeautifulSoup


URL = "https://komparse.de/hauptframe.htm"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}


# ============================================================
# MOIS ALLEMANDS
# ============================================================

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


# ============================================================
# TÉLÉCHARGEMENT
# ============================================================

def download_page() -> str:
    """
    Télécharge la page principale de Komparse
    et la décode en Windows-1252.
    """

    response = requests.get(
        URL,
        headers=HEADERS,
        timeout=20,
    )

    response.raise_for_status()

    return response.content.decode(
        "cp1252",
        errors="replace",
    )


# ============================================================
# ID D'ANNONCE
# ============================================================

OFFER_ID_PATTERN = re.compile(
    r"\b\d{2}\.\d{3}\b"
)

HREF_PATTERN = re.compile(
    r"""href=["'](?:https?://(?:www\.)?komparse\.de/)?Gesuch(\d{5})\.htm["']""",
    re.I,
)


def extract_displayed_offer_id(
    html_segment: str,
) -> str | None:
    """
    Cherche l'ID affiché au début du bloc d'annonce.

    Exemple :
    91.300

    On cherche en priorité dans les premières
    parties du bloc, car l'ID visible est normalement
    placé avant la date, le statut et le titre.
    """

    soup = BeautifulSoup(
        html_segment,
        "html.parser",
    )

    text = soup.get_text(
        " ",
        strip=True,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    if not text:
        return None


    # --------------------------------------------------------
    # Priorité aux premiers caractères du bloc.
    # --------------------------------------------------------

    header_text = text[:2500]

    matches = OFFER_ID_PATTERN.findall(
        header_text
    )

    if matches:
        return matches[0]


    # --------------------------------------------------------
    # Fallback : n'importe où dans le bloc.
    # --------------------------------------------------------

    matches = OFFER_ID_PATTERN.findall(
        text
    )

    if matches:
        return matches[0]


    return None


# ============================================================
# ID CONTENU DANS LE HREF
# ============================================================

def extract_offer_id_from_href(
    href: str,
) -> str | None:

    match = re.search(
        r"Gesuch(\d{5})\.htm$",
        href,
        re.I,
    )

    if not match:
        return None

    digits = match.group(1)

    return (
        f"{digits[:2]}."
        f"{digits[2:]}"
    )


# ============================================================
# DATE DE PUBLICATION
# ============================================================

def extract_publication_date(
    text: str,
) -> str | None:
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

    match = re.search(
        pattern,
        text,
        re.I,
    )

    if not match:
        return None


    day = int(
        match.group(1)
    )

    month_name = match.group(2)

    year = int(
        match.group(3)
    )

    time = match.group(4)


    month_key = (
        month_name[0].upper()
        +
        month_name[1:].lower()
    )


    if month_key.lower() == "märz":
        month_key = "März"


    month = GERMAN_MONTHS.get(
        month_key
    )

    if month is None:
        return None


    return (
        f"{year:04d}-"
        f"{month:02d}-"
        f"{day:02d} "
        f"{time}"
    )


# ============================================================
# TEXTE / TITRE
# ============================================================

def clean_text(
    text: str,
) -> str:

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


def extract_title(
    html_segment: str,
) -> str:

    soup = BeautifulSoup(
        html_segment,
        "html.parser",
    )


    # --------------------------------------------------------
    # Le <b> correspond généralement au titre principal.
    # --------------------------------------------------------

    bold = soup.find("b")

    if bold is not None:

        title = bold.get_text(
            " ",
            strip=True,
        )

        title = clean_text(
            title
        )

        if title:
            return title


    # --------------------------------------------------------
    # Fallback : paragraphe principal.
    # --------------------------------------------------------

    p = soup.find("p")

    if p is not None:

        title = p.get_text(
            " ",
            strip=True,
        )

        title = clean_text(
            title
        )

        if title:
            return title


    # --------------------------------------------------------
    # Dernier fallback : tout le bloc.
    # --------------------------------------------------------

    return clean_text(
        soup.get_text(
            " ",
            strip=True,
        )
    )


# ============================================================
# EXTRACTION DES ANNONCES
# ============================================================

def extract_offers(
    html: str,
) -> list[dict]:

    """
    Extrait les annonces depuis le HTML brut.

    Stratégie :

    - repérer tous les liens GesuchXXXXX.htm ;
    - prendre le contenu situé entre deux liens successifs ;
    - ce bloc contient l'ID affiché, la date, le titre et
      le lien de l'annonce ;
    - ne dépend donc pas de la structure <tr>/<td> parfois
      mal formée sur l'ancien site Komparse.
    """

    offers = []

    seen_offer_ids = set()


    href_matches = list(
        HREF_PATTERN.finditer(
            html
        )
    )


    for index, match in enumerate(
        href_matches
    ):

        href = match.group(
            0
        )


        # ----------------------------------------------------
        # Début du segment :
        # après le lien précédent.
        # ----------------------------------------------------

        if index == 0:

            segment_start = 0

        else:

            segment_start = (
                href_matches[
                    index - 1
                ].end()
            )


        segment_end = (
            match.start()
        )


        segment_html = html[
            segment_start:
            segment_end
        ]


        # ----------------------------------------------------
        # Texte du segment.
        # ----------------------------------------------------

        soup = BeautifulSoup(
            segment_html,
            "html.parser",
        )

        full_text = clean_text(
            soup.get_text(
                " ",
                strip=True,
            )
        )


        if not full_text:
            continue


        # ----------------------------------------------------
        # ID visible.
        # ----------------------------------------------------

        offer_id = (
            extract_displayed_offer_id(
                segment_html
            )
        )


        # ----------------------------------------------------
        # Fallback sur le href.
        # ----------------------------------------------------

        if offer_id is None:

            offer_id = (
                extract_offer_id_from_href(
                    href
                )
            )


        if offer_id is None:
            continue


        # ----------------------------------------------------
        # Déduplication.
        # ----------------------------------------------------

        if offer_id in seen_offer_ids:
            continue

        seen_offer_ids.add(
            offer_id
        )


        # ----------------------------------------------------
        # Titre.
        # ----------------------------------------------------

        title = extract_title(
            segment_html
        )


        # ----------------------------------------------------
        # Date de publication.
        # ----------------------------------------------------

        publication_date = (
            extract_publication_date(
                full_text
            )
        )


        # ----------------------------------------------------
        # URL complète.
        # ----------------------------------------------------

        detail_url = (
            requests.compat.urljoin(
                URL,
                href.strip(
                    "\"'"
                ),
            )
        )


        # ----------------------------------------------------
        # Offre finale.
        # ----------------------------------------------------

        offer = {

            "offer_id":
                offer_id,

            "publication_date":
                publication_date,

            "title":
                title,

            "detail_url":
                detail_url,

            "source_href":
                href,

            "raw_text":
                full_text,

        }


        offers.append(
            offer
        )


    return offers


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "Téléchargement de Komparse..."
    )

    html = download_page()

    print(
        "Page téléchargée."
    )

    print(
        "Analyse des annonces..."
    )


    offers = extract_offers(
        html
    )


    print(
        f"\nNombre d'annonces trouvées : "
        f"{len(offers)}"
    )


    # --------------------------------------------------------
    # Affichage de toutes les annonces
    # --------------------------------------------------------

    print(
        "\n" + "=" * 80
    )


    for offer in offers:

        print(
            f"ANNONCE : "
            f"{offer['offer_id']}"
        )

        print(
            f"Date   : "
            f"{offer['publication_date']}"
        )

        print(
            f"Titre  : "
            f"{offer['title']}"
        )

        print(
            f"Lien   : "
            f"{offer['detail_url']}"
        )

        print(
            "-" * 80
        )


    # --------------------------------------------------------
    # Sauvegarde
    # --------------------------------------------------------

    output_file = (
        "komparse_offers.json"
    )


    with open(
        output_file,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            offers,
            f,
            ensure_ascii=False,
            indent=4,
        )


    print(
        f"\nFichier créé : "
        f"{output_file}"
    )


# ============================================================
# POINT D'ENTRÉE
# ============================================================

if __name__ == "__main__":
    main()