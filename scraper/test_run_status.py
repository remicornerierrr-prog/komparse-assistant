import unittest
from unittest.mock import patch

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

    def test_missing_exact_shoot_date_does_not_block_eligible_offer(self):
        offer = self.make_offer(
            shoot_date=None,
            shoot_date_text="Ende November 2026",
        )
        self.assertEqual(prepare_offer_status(offer), "v1")
        self.assertNotIn("date_exacte_absente", offer["parser_review_reason"] or "")
        self.assertFalse(offer["parser_needs_review"])

    def test_outside_offer_is_not_sent_to_manual_review(self):
        offer = self.make_offer(
            location_text="Berlin",
            shoot_date=None,
        )
        self.assertEqual(prepare_offer_status(offer), "outside")
        self.assertEqual(offer["location_status"], "outside")

    def test_ambiguous_location_still_requires_review_when_date_is_missing(self):
        offer = self.make_offer(
            location_text="Köln und Ruhrgebiet",
            shoot_date=None,
            shoot_date_text="Nach Absprache",
        )
        self.assertEqual(prepare_offer_status(offer), "manual_review")
        self.assertIn("localisation_ambigue", offer["parser_review_reason"])
        self.assertNotIn("date_exacte_absente", offer["parser_review_reason"] or "")

    def test_stale_location_review_reason_is_cleared_when_now_supported(self):
        offer = self.make_offer(
            location_text="Köln + 100 km Umkreis",
            parser_needs_review=True,
            parser_review_reason="localisation_ambigue",
        )
        # A supported radius up to 100 km clears the stale location-review
        # reason and makes the offer eligible for V1.
        self.assertEqual(prepare_offer_status(offer), "v1")
        self.assertEqual(offer["location_status"], "v1")
        self.assertNotIn("localisation_ambigue", offer["parser_review_reason"])


    def test_open_age_and_unspecified_gender_are_eligible_when_date_is_exact(self):
        offer = self.make_offer(
            age_min=None,
            age_max=None,
            gender_male=False,
            gender_female=False,
            parser_needs_review=True,
            parser_review_reason="age_non_numerique, sexe_annonce_non_precise",
        )
        with patch("scraper.main.NOTIFY_WHEN_AGE_UNSPECIFIED", True):
            self.assertEqual(prepare_offer_status(offer), "v1")
        self.assertFalse(offer["parser_needs_review"])
        self.assertIsNone(offer["parser_review_reason"])

    def test_open_age_policy_can_keep_offer_eligible_without_exact_date(self):
        offer = self.make_offer(
            shoot_date=None,
            age_min=None,
            age_max=None,
            gender_male=False,
            gender_female=False,
            parser_needs_review=True,
            parser_review_reason="age_non_numerique, sexe_annonce_non_precise",
        )
        with patch("scraper.main.NOTIFY_WHEN_AGE_UNSPECIFIED", True):
            self.assertEqual(prepare_offer_status(offer), "v1")
        self.assertFalse(offer["parser_needs_review"])

    def test_open_age_policy_can_be_disabled(self):
        offer = self.make_offer(
            age_min=None,
            age_max=None,
            gender_male=False,
            gender_female=False,
            parser_needs_review=True,
            parser_review_reason="age_non_numerique, sexe_annonce_non_precise",
        )
        with patch("scraper.main.NOTIFY_WHEN_AGE_UNSPECIFIED", False):
            self.assertEqual(prepare_offer_status(offer), "manual_review")
        self.assertTrue(offer["parser_needs_review"])


    def test_descriptive_non_numeric_age_is_not_treated_as_open_age(self):
        offer = self.make_offer(
            age_min=None,
            age_max=None,
            age_description="Mitte 40",
            parser_needs_review=True,
            parser_review_reason=None,
        )
        with patch("scraper.main.NOTIFY_WHEN_AGE_UNSPECIFIED", True):
            self.assertEqual(prepare_offer_status(offer), "manual_review")
        self.assertTrue(offer["parser_needs_review"])


if __name__ == "__main__":
    unittest.main()
