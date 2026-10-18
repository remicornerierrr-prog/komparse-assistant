import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from scraper.main import OFFER_STATUS_STATS, prepare_offer_status, process_offer


class OfferRunStatusTests(unittest.TestCase):
    def setUp(self):
        self.original_offer_stats = OFFER_STATUS_STATS.copy()

    def tearDown(self):
        OFFER_STATUS_STATS.update(self.original_offer_stats)

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

    def test_radius_location_remains_manual_review(self):
        offer = self.make_offer(
            location_text="Köln + 100 km Umkreis",
            parser_needs_review=True,
            parser_review_reason="localisation_ambigue",
        )
        # Radius-based locations are not auto-approved without explicit config.
        self.assertEqual(prepare_offer_status(offer), "manual_review")
        self.assertEqual(offer["location_status"], "manual_review")
        self.assertTrue(offer["parser_needs_review"])
        self.assertIn("localisation_ambigue", offer["parser_review_reason"])


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
        # The product rule is now explicit: a missing age does not block an
        # offer when location is supported, even if the legacy toggle is false.
        with patch("scraper.main.NOTIFY_WHEN_AGE_UNSPECIFIED", False):
            self.assertEqual(prepare_offer_status(offer), "v1")
        self.assertFalse(offer["parser_needs_review"])


    def test_mitte_40_is_interpreted_without_manual_review(self):
        offer = self.make_offer(
            age_min=None,
            age_max=None,
            age_description="Mitte 40",
            parser_needs_review=True,
            parser_review_reason=None,
        )
        with patch("scraper.main.NOTIFY_WHEN_AGE_UNSPECIFIED", True):
            self.assertEqual(prepare_offer_status(offer), "v1")
        self.assertFalse(offer["parser_needs_review"])

    def test_week_old_offer_backfills_new_profile_without_push(self):
        offer = self.make_offer(
            komparse_id="91.319",
            title="Komparse in Köln",
            raw_text="Komparse in Köln",
            detail_text="",
            published_at="2026-10-10",
            email=None,
            subject_keyword=None,
            application_method=None,
            application_url=None,
            source_url="https://komparse.de/Gesuch91319.htm",
        )
        new_profile = {
            "id": "new-user",
            "created_at": "2026-10-13T12:30:00+02:00",
        }
        established_profile = {
            "id": "established-user",
            "created_at": "2026-09-01T12:30:00+02:00",
        }

        with (
            patch("scraper.main.normalize_offer", return_value=offer),
            patch("scraper.main.get_existing_offer", return_value=None),
            patch("scraper.main.apply_admin_qualification"),
            patch("scraper.main.prepare_offer_status", return_value="v1"),
            patch("scraper.main.save_offer", return_value=(123, True)),
            patch("scraper.main.is_offer_recent", return_value=False),
            patch(
                "scraper.main.is_offer_recent_for_new_profile",
                side_effect=lambda _published, created: created == new_profile["created_at"],
            ),
            patch("scraper.main.build_matching_offer", return_value={"offer_id": "91.319"}),
            patch("scraper.main.profile_allows_offer_scope", return_value=True),
            patch(
                "scraper.main.match_offer_to_profile",
                return_value={
                    "matched": True,
                    "reason": {"location": True, "age": True, "gender": True},
                },
            ),
            patch("scraper.main.create_match", return_value=(456, True)) as create_match_mock,
            patch("scraper.main.notify_match_user") as notify_mock,
        ):
            with redirect_stdout(io.StringIO()):
                process_offer(object(), {"unused": True}, [new_profile, established_profile])

        self.assertEqual(create_match_mock.call_count, 1)
        self.assertEqual(
            create_match_mock.call_args.args[1:],
            (123, "new-user", {"location": True, "age": True, "gender": True}),
        )
        notify_mock.assert_not_called()
        self.assertEqual(OFFER_STATUS_STATS["new_profile_backfilled_matches"], 1)


if __name__ == "__main__":
    unittest.main()
