import unittest

from scraper.location_rules import classify_location


class ExpandedLocationRulesTests(unittest.TestCase):
    def test_nrw_and_nationwide_are_valid_scopes(self):
        for location in (
            "NRW",
            "Nordrhein-Westfalen",
            "Bundesweit",
            "Deutschlandweit",
            "Ganz Deutschland",
            "Deutschland",
            "Germany",
        ):
            with self.subTest(location=location):
                self.assertEqual(classify_location(location), "v1")

    def test_supported_target_cities_are_v1(self):
        for location in (
            "Köln",
            "Großraum Köln",
            "Großraum Bonn",
            "Großraum Düsseldorf",
            "Großraum Köln/Bonn/Düsseldorf",
        ):
            with self.subTest(location=location):
                self.assertEqual(classify_location(location), "v1")

    def test_radius_and_surrounding_labels_require_review(self):
        for location in (
            "Köln + 50 km",
            "Köln + 100 km Umkreis",
            "Köln + 200 km",
            "Köln + Umgebung",
            "Bonn und Umgebung",
        ):
            with self.subTest(location=location):
                self.assertEqual(classify_location(location), "manual_review")

    def test_ambiguous_compound_location_requires_review(self):
        self.assertEqual(
            classify_location("Köln und Ruhrgebiet"),
            "manual_review",
        )

    def test_unrelated_city_is_outside(self):
        self.assertEqual(classify_location("Berlin"), "outside")


if __name__ == "__main__":
    unittest.main()
