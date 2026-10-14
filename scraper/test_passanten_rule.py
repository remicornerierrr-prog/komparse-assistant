import unittest

from scraper.parser import parse_offer, enrich_offer_from_detail
from scraper.location_rules import classify_location


class TestPassantenCastingRule(unittest.TestCase):
    def test_passanten_means_adults_and_both_genders_and_multiple_dates_are_valid(self):
        parsed = parse_offer({
            "offer_id": "91221",
            "publication_date": "2026-10-14 09:00",
            "title": "Köln und Hürth | Passanten | 14. oder 15. Oktober",
            "raw_text": "",
            "detail_url": "https://komparse.de/Gesuch91221.htm",
        })

        enriched = enrich_offer_from_detail(parsed, {
            "detail_text": (
                "Für die Dreharbeiten sind wir auf der Suche nach Passanten "
                "in Köln und Hürth. Termine: 14. oder 15. Oktober 2026."
            ),
            "shoot_dates": ["2026-10-14", "2026-10-15"],
            "shoot_date_text": "14. oder 15. Oktober 2026",
            "email": None,
            "subject_keyword": None,
            "application_url": None,
            "application_method": "unknown",
        })

        self.assertEqual(enriched["location_status"], "v1")
        self.assertEqual(classify_location("Köln und Hürth"), "v1")
        self.assertEqual(enriched["age_min"], 18)
        self.assertIsNone(enriched["age_max"])
        self.assertEqual(enriched["age_description"], "ab 18 Jahren")
        self.assertEqual(enriched["gender"], ["female", "male"])
        self.assertEqual(enriched["profiles"][0]["age_min"], 18)
        self.assertIsNone(enriched["profiles"][0]["age_max"])
        self.assertEqual(enriched["profiles"][0]["gender"], ["female", "male"])
        self.assertEqual(enriched["shoot_dates"], ["2026-10-14", "2026-10-15"])
        self.assertIsNone(enriched["shoot_date"])
        self.assertNotIn("date_exacte_absente", enriched["parser_review_reasons"])
        self.assertNotIn("age_non_numerique", enriched["parser_review_reasons"])
        self.assertNotIn("sexe_annonce_non_precise", enriched["parser_review_reasons"])
        self.assertFalse(enriched["needs_review"])


if __name__ == "__main__":
    unittest.main()
