import unittest

from scraper.parser import (
    detect_gender,
    determine_application_method,
    extract_age_ranges,
    extract_application_url,
    extract_profiles,
    extract_shoot_dates,
)


class TestAgeParsing(unittest.TestCase):
    def test_age_bis(self):
        result = extract_age_ranges("männl. Komparse (35 bis 60 Jahre)")
        self.assertEqual(result[0]["min"], 35)
        self.assertEqual(result[0]["max"], 60)

    def test_age_dash_with_j(self):
        result = extract_age_ranges("männl. 28-53 J.")
        self.assertEqual(result[0]["min"], 28)
        self.assertEqual(result[0]["max"], 53)

    def test_age_dash_with_spaces(self):
        result = extract_age_ranges("zwei Menschen, 18 - 55 Jahre")
        self.assertTrue(result)
        self.assertEqual(result[0]["min"], 18)
        self.assertEqual(result[0]["max"], 55)

    def test_age_between(self):
        result = extract_age_ranges("Testerinnen zwischen 30-60 Jahren")
        self.assertTrue(result)
        self.assertEqual(result[0]["min"], 30)
        self.assertEqual(result[0]["max"], 60)

    def test_age_plus(self):
        result = extract_profiles("Protagonist 25 Jahre +")
        self.assertTrue(result)
        self.assertEqual(result[0]["age_min"], 25)
        self.assertIsNone(result[0]["age_max"])


class TestGenderParsing(unittest.TestCase):
    def test_male_abbreviation(self):
        self.assertEqual(detect_gender("männl. Komparse"), {"male"})

    def test_female_abbreviation(self):
        self.assertEqual(detect_gender("weibl. Darstellerin"), {"female"})

    def test_female_compound_word(self):
        self.assertEqual(detect_gender("Kleindarstellerin gesucht"), {"female"})

    def test_male_komparse(self):
        self.assertEqual(detect_gender("Komparse für TV-Produktion"), {"male"})

    def test_gender_star(self):
        self.assertEqual(detect_gender("Kompars*innen gesucht"), {"male", "female"})

    def test_damen_und_herren_is_mixed(self):
        title = "Raum KÖLN | 3 Damen und Herren als Redakteure einer Tageszeitung, 25 bis 55 Jahre | 15. Oktober"
        self.assertEqual(detect_gender(title), {"male", "female"})

    def test_damen_only_is_female(self):
        self.assertEqual(detect_gender("Damen für eine Fernsehproduktion"), {"female"})

    def test_herren_only_is_male(self):
        self.assertEqual(detect_gender("Herren für eine Fernsehproduktion"), {"male"})


class TestShootDates(unittest.TestCase):
    def test_numeric_date_without_trailing_dot(self):
        self.assertEqual(extract_shoot_dates("Drehtag 03.11"), ["2026-11-03"])

    def test_numeric_date_with_comma(self):
        self.assertEqual(extract_shoot_dates("Drehtag, 05.11, ca. 10 Uhr"), ["2026-11-05"])

    def test_numeric_date_with_year(self):
        self.assertEqual(extract_shoot_dates("Drehtag 22.10.26"), ["2026-10-22"])


class TestApplicationDetection(unittest.TestCase):
    def test_website_application_url(self):
        html = '''<html><body><p>Bewerbungen bitte über unsere Homepage:</p><a href="http://www.mavies.de/bewerben">www.mavies.de/bewerben</a></body></html>'''
        result = extract_application_url(html, base_url="https://komparse.de/Gesuch91273.htm")
        self.assertEqual(result, "http://www.mavies.de/bewerben")

    def test_application_method_website(self):
        self.assertEqual(determine_application_method(None, "http://www.mavies.de/bewerben"), "website")

    def test_application_method_email(self):
        self.assertEqual(determine_application_method("casting@example.com", None), "email")

    def test_application_method_multiple(self):
        self.assertEqual(determine_application_method("casting@example.com", "https://example.com/apply"), "multiple")

    def test_application_method_unknown(self):
        self.assertEqual(determine_application_method(None, None), "unknown")

    def test_real_mavies_instruction_text(self):
        html = '''<html><body><p>Bewerbungen bitte über unsere Homepage:</p><a href="http://www.mavies.de/bewerben">www.mavies.de/bewerben</a><p>Projektauswahl: Stichwort „Komparse“</p></body></html>'''
        self.assertEqual(
            extract_application_url(html, base_url="https://komparse.de/Gesuch91273.htm"),
            "http://www.mavies.de/bewerben",
        )


if __name__ == "__main__":
    unittest.main()
