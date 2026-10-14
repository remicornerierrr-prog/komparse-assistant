"""Regression tests for V1 location eligibility."""
import unittest

from scraper.location_rules import classify_location


class LocationRulesTests(unittest.TestCase):
    def test_supported_target_area_is_eligible(self):
        for label in (
            "Köln",
            "Großraum Köln",
            "Großraum Bonn",
            "Großraum Düsseldorf",
            "Großraum Köln/Bonn/Düsseldorf",
        ):
            with self.subTest(label=label):
                self.assertEqual(classify_location(label), "v1")

    def test_broad_regions_are_valid_scopes(self):
        for label in (
            "NRW",
            "Nordrhein-Westfalen",
            "bundesweit",
            "Deutschlandweit",
            "Deutschland",
        ):
            with self.subTest(label=label):
                self.assertEqual(classify_location(label), "v1")

    def test_radius_and_surrounding_area_require_manual_review(self):
        for label in (
            "Köln + 50 km",
            "Großraum Köln + Umgebung",
            "Bonn und Umgebung",
            "Köln und Ruhrgebiet",
        ):
            with self.subTest(label=label):
                self.assertEqual(classify_location(label), "manual_review")

    def test_unrelated_city_is_outside(self):
        self.assertEqual(classify_location("München"), "outside")

    def test_missing_location_requires_review(self):
        self.assertEqual(classify_location(""), "manual_review")


if __name__ == "__main__":
    unittest.main()
