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

    def test_mehrgenerationenhaus_is_open_to_all_ages_and_genders(self):
        parsed = parse_offer({
            "offer_id": "91347",
            "publication_date": "2026-10-12 15:25",
            "title": "NRW | Familien, die in einem Mehrgenerationenhaus leben | zwei Drehtage nach Absprache zwischen Oktober 2026 und März 2027",
            "raw_text": "",
            "detail_url": "https://komparse.de/Gesuch91347.htm",
        })
        enriched = enrich_offer_from_detail(parsed, {
            "detail_text": (
                "Für ein spannendes Verbraucher-Format suchen wir Familien, "
                "die in einem Mehrgenerationenhaus leben. Es geht um mehrere "
                "Generationen einer Familie."
            ),
            "shoot_dates": [],
            "shoot_date_text": "nach Absprache zwischen Oktober 2026 und März 2027",
            "email": None,
            "subject_keyword": None,
            "application_url": None,
            "application_method": "unknown",
        })

        self.assertIsNone(enriched["age_min"])
        self.assertIsNone(enriched["age_max"])
        self.assertEqual(enriched["age_description"], "alle Altersgruppen")
        self.assertEqual(enriched["gender"], ["female", "male"])
        self.assertNotIn("age_non_numerique", enriched["parser_review_reasons"])
        self.assertNotIn("sexe_annonce_non_precise", enriched["parser_review_reasons"])


    def test_child_casting_with_unspecified_gender_is_open_to_girls_and_boys(self):
        parsed = parse_offer({
            "offer_id": "91334",
            "publication_date": "2026-10-14 10:00",
            "title": "Köln | Kinder 9–17 Jahre | für eine Produktion gesucht",
            "raw_text": "",
            "detail_url": "https://komparse.de/Gesuch91334.htm",
        })
        enriched = enrich_offer_from_detail(parsed, {
            "detail_text": "Für eine Produktion suchen wir Kinder im Alter von 9 bis 17 Jahren.",
            "shoot_dates": ["2026-10-20"],
            "shoot_date_text": "20. Oktober 2026",
            "email": None,
            "subject_keyword": None,
            "application_url": None,
            "application_method": "unknown",
        })

        self.assertEqual(enriched["age_min"], 9)
        self.assertEqual(enriched["age_max"], 17)
        self.assertEqual(enriched["gender"], ["female", "male"])
        self.assertEqual(enriched["profiles"][0]["gender"], ["female", "male"])
        self.assertNotIn("sexe_annonce_non_precise", enriched["parser_review_reasons"])


    def test_prota_without_gender_is_adult_and_open_to_both_genders(self):
        parsed = parse_offer({
            "offer_id": "91312",
            "publication_date": "2026-10-14 10:00",
            "title": "Köln | Prota, die unter Ungeziefer in Haus oder Wohnung im Herbst leidet (Bsp. Stinkwanzen)",
            "raw_text": "",
            "detail_url": "https://komparse.de/Gesuch91312.htm",
        })
        enriched = enrich_offer_from_detail(parsed, {
            "detail_text": "Prota, die unter Ungeziefer in Haus oder Wohnung im Herbst leidet (Bsp. Stinkwanzen).",
            "shoot_dates": ["2026-10-20"],
            "shoot_date_text": "20. Oktober 2026",
            "email": None,
            "subject_keyword": None,
            "application_url": None,
            "application_method": "unknown",
        })

        self.assertEqual(enriched["age_min"], 18)
        self.assertIsNone(enriched["age_max"])
        self.assertEqual(enriched["gender"], ["female", "male"])
        self.assertNotIn("age_non_numerique", enriched["parser_review_reasons"])
        self.assertNotIn("sexe_annonce_non_precise", enriched["parser_review_reasons"])


if __name__ == "__main__":
    unittest.main()
