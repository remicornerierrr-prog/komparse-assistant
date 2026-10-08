import unittest

from scraper.parser import (
    detect_gender,
    extract_age_ranges,
    extract_profiles,
    extract_shoot_dates,
)


class TestAgeParsing(unittest.TestCase):

    def test_age_bis(self):
        result = extract_age_ranges(
            "männl. Komparse (35 bis 60 Jahre)"
        )

        self.assertEqual(
            [
                {
                    "min": 35,
                    "max": 60,
                    "start": result[0]["start"],
                    "end": result[0]["end"],
                }
            ],
            result,
        )

    def test_age_dash_with_j(self):
        result = extract_age_ranges(
            "männl. 28-53 J."
        )

        self.assertEqual(
            result[0]["min"],
            28,
        )

        self.assertEqual(
            result[0]["max"],
            53,
        )

    def test_age_dash_with_spaces(self):
        result = extract_age_ranges(
            "zwei Menschen, 18 - 55 Jahre"
        )

        self.assertTrue(result)

        self.assertEqual(
            result[0]["min"],
            18,
        )

        self.assertEqual(
            result[0]["max"],
            55,
        )

    def test_age_between(self):
        result = extract_age_ranges(
            "Testerinnen zwischen 30-60 Jahren"
        )

        self.assertTrue(result)

        self.assertEqual(
            result[0]["min"],
            30,
        )

        self.assertEqual(
            result[0]["max"],
            60,
        )

    def test_age_plus(self):
        result = extract_profiles(
            "Protagonist 25 Jahre +"
        )

        self.assertTrue(result)

        self.assertEqual(
            result[0]["age_min"],
            25,
        )

        self.assertIsNone(
            result[0]["age_max"],
        )


class TestGenderParsing(unittest.TestCase):

    def test_male_abbreviation(self):
        result = detect_gender(
            "männl. Komparse"
        )

        self.assertEqual(
            result,
            {"male"},
        )

    def test_female_abbreviation(self):
        result = detect_gender(
            "weibl. Darstellerin"
        )

        self.assertEqual(
            result,
            {"female"},
        )

    def test_female_compound_word(self):
        result = detect_gender(
            "Kleindarstellerin gesucht"
        )

        self.assertEqual(
            result,
            {"female"},
        )

    def test_male_komparse(self):
        result = detect_gender(
            "Komparse für TV-Produktion"
        )

        self.assertEqual(
            result,
            {"male"},
        )

    def test_gender_star(self):
        result = detect_gender(
            "Kompars*innen gesucht"
        )

        self.assertEqual(
            result,
            {"male", "female"},
        )


class TestShootDates(unittest.TestCase):

    def test_numeric_date_without_trailing_dot(self):
        result = extract_shoot_dates(
            "Drehtag 03.11"
        )

        self.assertEqual(
            result,
            ["2026-11-03"],
        )

    def test_numeric_date_with_comma(self):
        result = extract_shoot_dates(
            "Drehtag, 05.11, ca. 10 Uhr"
        )

        self.assertEqual(
            result,
            ["2026-11-05"],
        )

    def test_numeric_date_with_year(self):
        result = extract_shoot_dates(
            "Drehtag 22.10.26"
        )

        self.assertEqual(
            result,
            ["2026-10-22"],
        )


if __name__ == "__main__":
    unittest.main()