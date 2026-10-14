import unittest

from scraper.extract_offers import extract_repeat_detail_href


class TestRepeatedOfferLinks(unittest.TestCase):
    def test_repeat_listing_resolves_to_latest_referenced_detail_page(self):
        self.assertEqual(
            extract_repeat_detail_href(
                "91.144 Wiederholung von 91.100/ 91.045 Bundesweit | Familie"
            ),
            "Gesuch91045.htm",
        )

    def test_normal_listing_without_repeat_has_no_override(self):
        self.assertIsNone(
            extract_repeat_detail_href("91.097 Großraum Köln | Haushaltsexperte")
        )


if __name__ == "__main__":
    unittest.main()
