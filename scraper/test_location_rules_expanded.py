import unittest

from scraper.location_rules import classify_location


class ExpandedLocationRulesTests(unittest.TestCase):
    def test_nrw_and_nationwide_are_v1(self):
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

    def test_supported_cities_and_radius_up_to_100_km_are_v1(self):
        for location in (
            "Köln",
            "Großraum Köln",
            "Großraum Bonn",
            "Großraum Düsseldorf",
            "Großraum Köln/Bonn/Düsseldorf",
            "Köln + 50 km",
            "Köln + 100 km Umkreis",
        ):
            with self.subTest(location=location):
                self.assertEqual(classify_location(location), "v1")

    def test_radius_over_100_km_is_not_automatically_eligible(self):
        self.assertEqual(
            classify_location("Köln + 200 km"),
            "manual_review",
        )

    def test_ambiguous_compound_location_requires_review(self):
        self.assertEqual(
            classify_location("Köln und Ruhrgebiet"),
            "manual_review",
        )

    def test_unrelated_city_is_outside(self):
        self.assertEqual(classify_location("Berlin"), "outside")


if __name__ == "__main__":
    unittest.main()
