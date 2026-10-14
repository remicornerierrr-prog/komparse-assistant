import unittest
from datetime import date

from scraper.notification_eligibility import is_offer_recent, profile_allows_offer_scope


class NotificationEligibilityTests(unittest.TestCase):
    def test_only_today_and_yesterday_are_recent(self):
        today = date(2026, 10, 13)
        self.assertTrue(is_offer_recent("2026-10-13", today=today))
        self.assertTrue(is_offer_recent("2026-10-12", today=today))
        self.assertFalse(is_offer_recent("2026-10-11", today=today))
        self.assertFalse(is_offer_recent(None, today=today))

    def test_national_preference(self):
        profile = {"city": "Köln", "notify_national": True, "notify_regional": False}
        self.assertTrue(profile_allows_offer_scope("Deutschlandweit", profile))
        profile["notify_national"] = False
        self.assertFalse(profile_allows_offer_scope("Deutschlandweit", profile))

    def test_regional_requires_profile_city_or_supported_state_scope(self):
        profile = {"city": "Köln", "notify_national": False, "notify_regional": True}
        self.assertTrue(profile_allows_offer_scope("Großraum Köln/Bonn/Düsseldorf", profile))
        self.assertFalse(profile_allows_offer_scope("Großraum Bonn", profile))
        self.assertTrue(profile_allows_offer_scope("NRW", profile))
        profile["notify_regional"] = False
        self.assertFalse(profile_allows_offer_scope("Großraum Köln", profile))

    def test_nrw_preference_includes_nrw_and_city_only_labels(self):
        profile = {
            "city": "Köln",
            "notify_national": False,
            "notify_regional": False,
            "notify_region": "nrw",
        }
        self.assertTrue(profile_allows_offer_scope("NRW", profile))
        self.assertTrue(profile_allows_offer_scope("Münster", profile))
        self.assertTrue(profile_allows_offer_scope("Dortmund", profile))
        self.assertTrue(profile_allows_offer_scope("Großraum Düsseldorf", profile))
        self.assertFalse(profile_allows_offer_scope("Hamburg", profile))

    def test_nrw_city_labels_are_classified_for_profile_matching(self):
        from scraper.location_rules import classify_location
        self.assertEqual(classify_location("Münster"), "v1")
        self.assertEqual(classify_location("Dortmund"), "v1")
        self.assertEqual(classify_location("NRW"), "v1")


if __name__ == "__main__":
    unittest.main()
