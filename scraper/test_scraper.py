"""Unit tests for Komparse listing extraction.

These tests use static HTML fixtures only. They must never access the live
Komparse website, so CI can safely run them before the production pipeline.
"""

import unittest

from scraper.extract_offers import (
    extract_offer_id,
    extract_offer_id_from_href,
    extract_offers,
    extract_publication_date,
    extract_source_href,
    extract_title,
)


class TestOfferIdentifiers(unittest.TestCase):
    def test_extract_visible_offer_id(self):
        self.assertEqual(
            extract_offer_id("Annonce 91.339 publiée aujourd'hui"),
            "91.339",
        )

    def test_extract_id_from_detail_href(self):
        self.assertEqual(
            extract_offer_id_from_href("Gesuch91339.htm"),
            "91.339",
        )

    def test_invalid_detail_href_returns_none(self):
        self.assertIsNone(
            extract_offer_id_from_href("andere-seite.htm")
        )

    def test_source_href_is_normalized(self):
        self.assertEqual(
            extract_source_href("https://komparse.de/Gesuch91339.htm?x=1"),
            "Gesuch91339.htm",
        )


class TestPublicationAndTitleExtraction(unittest.TestCase):
    def test_extract_german_publication_timestamp(self):
        self.assertEqual(
            extract_publication_date(
                "91.339 9. Oktober 2026 14:00 Uhr"
            ),
            "2026-10-09 14:00",
        )

    def test_extract_title_removes_concatenated_page_heading(self):
        html = (
            "<b>Aktuelle Gesuche</b>"
            "<b>KÖLN | 3 Damen und Herren, 25 bis 55 Jahre</b>"
        )
        self.assertEqual(
            extract_title(html),
            "KÖLN | 3 Damen und Herren, 25 bis 55 Jahre",
        )

    def test_extract_title_removes_heading_with_separator(self):
        html = "<b>Aktuelle Gesuche | Raum Köln | Komparse gesucht</b>"
        self.assertEqual(
            extract_title(html),
            "Raum Köln | Komparse gesucht",
        )


class TestExtractOffersFromStaticHtml(unittest.TestCase):
    def test_extract_offer_does_not_need_network(self):
        html = """
        <html><body>
          <div>
            91.339 9. Oktober 2026 14:00 Uhr
            <b>Aktuelle Gesuche</b>
            <b>KÖLN | 3 Damen und Herren, 25 bis 55 Jahre</b>
            <a href="Gesuch91339.htm">Details</a>
          </div>
        </body></html>
        """

        offers = extract_offers(html)

        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0]["offer_id"], "91.339")
        self.assertEqual(
            offers[0]["publication_date"],
            "2026-10-09 14:00",
        )
        self.assertEqual(
            offers[0]["title"],
            "KÖLN | 3 Damen und Herren, 25 bis 55 Jahre",
        )
        self.assertEqual(
            offers[0]["source_href"],
            "Gesuch91339.htm",
        )
        self.assertEqual(
            offers[0]["detail_url"],
            "https://komparse.de/Gesuch91339.htm",
        )


if __name__ == "__main__":
    unittest.main()
