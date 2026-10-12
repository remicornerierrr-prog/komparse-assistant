import unittest

from scraper.main import prepare_offer_status


class OfferRunStatusTests(unittest.TestCase):
    @staticmethod
    def make_offer(**overrides):
        offer = {
            "komparse_id": "test-1",
            "location_text": "Raum Köln",
            "location_status": None,
            "shoot_date": "2026-10-20",
            "shoot_date_text": None,
            "shoot_duration_text": "1 Drehtag",
            "age_min": 25,
            "age_max": 55,
            "age_description": None,
            "gender_male": True,
            "gender_female": True,
            "parser_needs_review": False,
            "parser_review_reason": None,
        }
        offer.update(overrides)
        return offer

    def test_clear_v1_offer_remains_eligible(self):
        offer = self.make_offer()
        self.assertEqual(prepare_offer_status(offer), "v1")
        self.assertEqual(offer["location_status"], "v1")
        self.assertFalse(offer["parser_needs_review"])

    def test_ambiguous_target_city_is_manual_review(self):
        offer = self.make_offer(
            location_text="Köln und Ruhrgebiet",
        )
        self.assertEqual(prepare_offer_status(offer), "manual_review")
        self.assertIn("localisation_ambigue", offer["parser_review_reason"])
        self.assertTrue(offer["parser_needs_review"])

    def test_missing_exact_shoot_date_is_manual_review(self):
        offer = self.make_offer(
            shoot_date=None,
            shoot_date_text="Ende November 2026",
        )
        self.assertEqual(prepare_offer_status(offer), "manual_review")
        self.assertIn("date_exacte_absente", offer["parser_review_reason"])
        self.assertTrue(offer["parser_needs_review"])

    def test_outside_offer_is_not_sent_to_manual_review(self):
        offer = self.make_offer(
            location_text="Berlin",
            shoot_date=None,
        )
        self.assertEqual(prepare_offer_status(offer), "outside")
        self.assertEqual(offer["location_status"], "outside")

    def test_location_and_date_reasons_are_both_preserved(self):
        offer = self.make_offer(
            location_text="Köln und Ruhrgebiet",
            shoot_date=None,
            shoot_date_text="Nach Absprache",
        )
        self.assertEqual(prepare_offer_status(offer), "manual_review")
        self.assertIn("localisation_ambigue", offer["parser_review_reason"])
        self.assertIn("date_exacte_absente", offer["parser_review_reason"])

    def test_stale_location_review_reason_is_cleared_when_now_supported(self):
        offer = self.make_offer(
            location_text="Köln + 150 km Umkreis",
            parser_needs_review=True,
            parser_review_reason="localisation_ambigue",
        )
        # The existing parser flag is preserved as a review signal unless
        # another known reason can explain it. The classification itself is
        # upgraded to the supported V1 status.
        self.assertEqual(prepare_offer_status(offer), "manual_review")
        self.assertEqual(offer["location_status"], "v1")
        self.assertNotIn("localisation_ambigue", offer["parser_review_reason"])


if __name__ == "__main__":
    unittest.main()
