import re
import json
import requests
from bs4 import BeautifulSoup


URL = "https://komparse.de/hauptframe.htm"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}


GERMAN_MONTHS = {
    "Januar": 1,
    "Februar": 2,
    "März": 3,
    "MÃ¤rz": 3,
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


def extract_offer_id(text):
    """
    Extract a visible Komparse offer ID such as 91.319.
    """
    if not text:
        return None

    match = re.search(
        r"\b(\d{2}\.\d{3})\b",
        text,
    )

    if match:
        return match.group(1)

    return None


def extract_offer_id_from_href(href):
    """
    Extract the offer number from a detail filename such as:

        Gesuch91319.htm

    Result:

        91.319
    """
    if not href:
        return None

    match = re.search(
        r"Gesuch(\d+)\.htm",
        href,
        re.IGNORECASE,
    )

    if not match:
        return None

    number = match.group(1)

    if len(number) < 5:
        return None

    return f"{number[:-3]}.{number[-3:]}"


def extract_source_href(href):
    """
    Normalize any Komparse href to the detail filename.
    """
    if not href:
        return None

    match = re.search(
        r"Gesuch\d+\.htm",
        href,
        re.IGNORECASE,
    )

    if not match:
        return None

    return match.group(0)


def extract_publication_date(text):
    if not text:
        return None

    pattern = (
        r"(\d{1,2})\.\s*"
        r"(Januar|Februar|März|MÃ¤rz|April|Mai|Juni|Juli|August|"
        r"September|Oktober|November|Dezember)\s+"
        r"(\d{4})\s+"
        r"(\d{1,2}:\d{2})"
    )

    match = re.search(
        pattern,
        text,
        re.IGNORECASE,
    )

    if not match:
        return None

    day = int(match.group(1))
    month_name = match.group(2)
    year = int(match.group(3))
    time = match.group(4)

    month = None

    for name, number in GERMAN_MONTHS.items():
        if name.lower() == month_name.lower():
            month = number
            break

    if month is None:
        return None

    return (
        f"{year:04d}-{month:02d}-{day:02d} "
        f"{time}"
    )


def extract_title(segment):
    """
    Extract the title from legacy / malformed Komparse HTML.

    Some announcements split one word across multiple <b> tags.
    Therefore all <b> elements are concatenated without inserting
    artificial spaces between them.
    """
    soup = BeautifulSoup(
        segment,
        "html.parser",
    )

    bold_elements = soup.find_all("b")

    if bold_elements:
        title = "".join(
            bold.get_text(
                "",
                strip=True,
            )
            for bold in bold_elements
        )

        title = re.sub(
            r"\s+",
            " ",
            title,
        ).strip()

        # Legacy page heading is sometimes included in the first
        # offer's bold elements, concatenated directly with its city.
        title = re.sub(
            r"^\s*Aktuelle\s*Gesuche(?:\s*[:|,–-]\s*|\s*)",
            "",
            title,
            flags=re.IGNORECASE,
        ).strip()

        if title:
            return title

    text = soup.get_text(
        " ",
        strip=True,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()
    text = re.sub(
        r"^\s*Aktuelle\s*Gesuche(?:\s*[:|,–-]\s*|\s*)",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()

    return text


def extract_offers(html):
    """
    Extract Komparse offers directly from the raw HTML.

    Important:
    - the visible offer ID is taken from the offer segment;
    - the detail URL is taken from the actual href;
    - these two numbers can legitimately differ for updated offers.
    """

    offers = []
    seen_offer_ids = set()

    # Komparse contains legacy / malformed HTML.
    # Detect hrefs directly in the raw HTML instead of relying
    # on BeautifulSoup's reconstructed DOM.
    href_pattern = re.compile(
        r'href\s*=\s*["\']?([^"\' >]*Gesuch\d+\.htm)',
        re.IGNORECASE,
    )

    matches = list(
        href_pattern.finditer(html)
    )

    previous_end = 0

    for match in matches:
        raw_href = match.group(1)

        source_href = extract_source_href(
            raw_href
        )

        if source_href is None:
            previous_end = match.end()
            continue

        # Everything between the previous detail link and
        # the current detail link belongs to this offer block.
        segment = html[
            previous_end:match.start()
        ]

        previous_end = match.end()

        offer_id = extract_offer_id(
            segment
        )

        if offer_id is None:
            continue

        if offer_id in seen_offer_ids:
            continue

        seen_offer_ids.add(
            offer_id
        )

        soup = BeautifulSoup(
            segment,
            "html.parser",
        )

        full_text = soup.get_text(
            " ",
            strip=True,
        )

        full_text = re.sub(
            r"\s+",
            " ",
            full_text,
        ).strip()

        title = extract_title(
            segment
        )

        publication_date = (
            extract_publication_date(
                full_text
            )
        )

        detail_url = requests.compat.urljoin(
            URL,
            source_href,
        )

        offer = {
            "offer_id": offer_id,
            "publication_date": publication_date,
            "title": title,
            "detail_url": detail_url,
            "source_href": source_href,
            "raw_text": full_text,
        }

        offers.append(
            offer
        )

    return offers


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

    print(
        "\n" + "=" * 80
    )

    for offer in offers[:20]:
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


if __name__ == "__main__":
    main()