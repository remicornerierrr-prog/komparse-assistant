import unittest

from scraper.parser import (
    detect_gender,
    detect_location,
    determine_application_method,
    extract_age_ranges,
    extract_application_url,
    extract_profiles,
    extract_shoot_date_text,
    extract_shoot_dates,
    extract_shoot_duration_text,
    parse_offer,
    enrich_offer_from_detail,
)
from scraper.extract_offers import extract_title


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

    def test_age_ab_is_open_upper_bound(self):
        result = extract_age_ranges("Frau ab 30 Jahren")
        self.assertEqual(result[0]["min"], 30)
        self.assertIsNone(result[0]["max"])

    def test_age_plus_is_open_upper_bound(self):
        result = extract_age_ranges("Protagonist 25 Jahre +")
        self.assertEqual(result[0]["min"], 25)
        self.assertIsNone(result[0]["max"])

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

    def test_generic_komparse_is_not_assumed_male(self):
        self.assertEqual(detect_gender("Komparse für TV-Produktion"), set())

    def test_generic_komparsen_is_not_assumed_male(self):
        self.assertEqual(detect_gender("100 Komparsen, 19-70 Jahre"), set())

    def test_generic_kleindarsteller_is_not_assumed_male(self):
        self.assertEqual(detect_gender("Kleindarsteller gesucht"), set())

    def test_darsteller_star_is_mixed(self):
        self.assertEqual(detect_gender("4 volljährige Darsteller*innen"), {"male", "female"})

    def test_testerin_is_female(self):
        self.assertEqual(detect_gender("1 Testerin ab 35 Jahren"), {"female"})

    def test_gender_star(self):
        self.assertEqual(detect_gender("Kompars*innen gesucht"), {"male", "female"})

    def test_damen_und_herren_is_mixed(self):
        title = "Raum KÖLN | 3 Damen und Herren als Redakteure einer Tageszeitung, 25 bis 55 Jahre | 15. Oktober"
        self.assertEqual(detect_gender(title), {"male", "female"})

    def test_damen_only_is_female(self):
        self.assertEqual(detect_gender("Damen für eine Fernsehproduktion"), {"female"})

    def test_herren_only_is_male(self):
        self.assertEqual(detect_gender("Herren für eine Fernsehproduktion"), {"male"})


class TestScheduleParsing(unittest.TestCase):
    def test_end_of_month_is_text_period_not_fake_date(self):
        title = "Bundesweit | US-Native-Speaker (9-17 J.) | 1 Drehtag, Ende November | VB"
        dates = extract_shoot_dates(title, default_year=2026)
        self.assertEqual(dates, [])
        self.assertEqual(
            extract_shoot_date_text(title, default_year=2026, shoot_dates=dates),
            "Ende November 2026",
        )
        self.assertEqual(extract_shoot_duration_text(title), "1 Drehtag")

    def test_home_shoot_by_arrangement_is_preserved(self):
        title = "Berlin | Frau ab 30 Jahren | 1 Drehtag bei dir zu Hause nach Absprache | 100 Euro"
        self.assertIsNone(extract_shoot_dates(title, default_year=2026)[0] if extract_shoot_dates(title, default_year=2026) else None)
        self.assertEqual(
            extract_shoot_date_text(title, default_year=2026),
            "Nach Absprache",
        )
        self.assertEqual(
            extract_shoot_duration_text(title),
            "1 Drehtag bei dir zu Hause",
        )

    def test_multiple_possible_dates_are_not_collapsed_to_one(self):
        title = "Raum Köln | Kleindarstellerin, Mitte 40 | 1 Drehtag, 7. o. 8. November"
        dates = extract_shoot_dates(title, default_year=2026)
        self.assertEqual(dates, ["2026-11-07", "2026-11-08"])
        self.assertEqual(
            extract_shoot_date_text(title, default_year=2026, shoot_dates=dates),
            "7. oder 8. November 2026",
        )

    def test_duration_and_video_diary_are_preserved(self):
        title = "Berlin/Potsdam | Testerin ab 35 Jahren | 2x 0,5 Drehtage nach Absprache + Videotagebuch | 150 Euro"
        self.assertEqual(
            extract_shoot_duration_text(title),
            "2x 0,5 Drehtage + Videotagebuch",
        )

    def test_seasonal_period_is_preserved_without_exact_date(self):
        title = "Deutschlandweit | Singlemütter 35-50 Jahre | Drehzeitraum im Sommer 2027, Anzahl Drehtage noch unbestimmt"
        self.assertEqual(
            extract_shoot_date_text(title, default_year=2026),
            "Sommer 2027",
        )
        self.assertEqual(
            extract_shoot_duration_text(title),
            "Anzahl Drehtage noch unbestimmt",
        )

    def test_numeric_and_multiple_dates_are_removed_from_duration(self):
        title = "Köln | männlicher Patient 45-65 J. | ganzer Drehtag, 13.10. | 140 Euro"
        self.assertEqual(extract_shoot_duration_text(title), "ganzer Drehtag")
        title = "Köln | Vater, 30-40 Jahre | 2 Drehtage, 13. und 14. Oktober | 150 Euro"
        self.assertEqual(extract_shoot_duration_text(title), "2 Drehtage")

    def test_location_header_prefix_is_removed(self):
        result = detect_location("Aktuelle GesucheKÖLN | 3 Damen und Herren, 25 bis 55 Jahre")
        self.assertEqual(result["location_text"], "KÖLN")
        self.assertTrue(result["matches_mvp"])


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


class TestRealAnnouncementExamples(unittest.TestCase):
    def test_91_339_damen_und_herren_age_and_location(self):
        result = parse_offer({
            "offer_id": "91.339",
            "publication_date": "2026-10-09 14:00",
            "title": "Aktuelle GesucheKÖLN | 3 Damen und Herren als Redakteure einer Tageszeitung, 25 bis 55 Jahre | 15. Oktober | Gage je € 112",
            "raw_text": "",
            "detail_url": "https://komparse.de/Gesuch91339.htm",
        })
        self.assertEqual(result["location_text"], "KÖLN")
        self.assertEqual(result["location_status"], "v1")
        self.assertEqual(result["shoot_date"], "2026-10-15")
        self.assertEqual(result["age_min"], 25)
        self.assertEqual(result["age_max"], 55)
        self.assertEqual(result["gender"], ["female", "male"])
        self.assertFalse(result["needs_review"])

    def test_91_334_preserves_end_of_november_period_and_duration(self):
        title = "Bundesweit | US-Native-Speaker (9-17 J.) für eine neue US-Kinder-Game-Show | 1 Drehtag, Ende November | Vergütung VB"
        result = parse_offer({
            "offer_id": "91.334",
            "publication_date": "2026-10-09 12:40",
            "title": title,
            "raw_text": "",
            "detail_url": "https://komparse.de/Gesuch91334.htm",
        })
        detail = enrich_offer_from_detail(result, {
            "detail_text": "Kinder und Jugendliche (9-17 Jahre). Die Dreharbeiten finden Ende November 2026 in Köln statt.",
            "email": "bewerbung@mavies.de",
            "subject_keyword": "Initiativbewerbung",
            "shoot_dates": [],
            "application_url": "https://www.mavies.de/bewerben",
            "application_method": "multiple",
        })
        self.assertIsNone(detail["shoot_date"])
        self.assertEqual(detail["shoot_date_text"], "Ende November 2026")
        self.assertEqual(detail["shoot_duration_text"], "1 Drehtag")
        self.assertEqual((detail["age_min"], detail["age_max"]), (9, 17))
        self.assertEqual(detail["email"], "bewerbung@mavies.de")
        self.assertEqual(detail["subject_keyword"], "Initiativbewerbung")
        self.assertEqual(detail["application_url"], "https://www.mavies.de/bewerben")
        self.assertTrue(detail["needs_review"])  # Bundesweit and gender are intentionally reviewed.

    def test_91_330_open_age_and_home_shooting(self):
        result = parse_offer({
            "offer_id": "91.330",
            "publication_date": "2026-10-08 21:48",
            "title": "Berlin | Frau ab 30 Jahren | 1 Drehtag bei dir zu Hause nach Absprache | 100 Euro",
            "raw_text": "",
            "detail_url": "https://komparse.de/Gesuch91330.htm",
        })
        self.assertEqual(result["age_min"], 30)
        self.assertIsNone(result["age_max"])
        self.assertEqual(result["gender"], ["female"])
        self.assertIsNone(result["shoot_date"])
        self.assertEqual(result["shoot_date_text"], "Nach Absprache")
        self.assertEqual(result["shoot_duration_text"], "1 Drehtag bei dir zu Hause")

    def test_91_329_testerin_open_age_and_duration(self):
        result = parse_offer({
            "offer_id": "91.329",
            "publication_date": "2026-10-08 17:11",
            "title": "Berlin/Potsdam | 1 Testerin ab 35 Jahren für Rotlicht-Matten-Test | 2x 0,5 Drehtage nach Absprache + Videotagebuch | 150 Euro",
            "raw_text": "",
            "detail_url": "https://komparse.de/Gesuch91329.htm",
        })
        self.assertEqual(result["age_min"], 35)
        self.assertIsNone(result["age_max"])
        self.assertEqual(result["gender"], ["female"])
        self.assertEqual(result["shoot_date_text"], "Nach Absprache")
        self.assertEqual(result["shoot_duration_text"], "2x 0,5 Drehtage + Videotagebuch")

    def test_extractor_removes_concatenated_page_heading(self):
        html = '<div><b>Aktuelle GesucheKÖLN | 3 Damen und Herren als Redakteure</b></div>'
        self.assertEqual(
            extract_title(html),
            "KÖLN | 3 Damen und Herren als Redakteure",
        )

    def test_extractor_removes_page_heading_with_separator(self):
        html = '<div><b>Aktuelle Gesuche | Köln | 3 Damen und Herren</b></div>'
        self.assertEqual(
            extract_title(html),
            "Köln | 3 Damen und Herren",
        )

    def test_91_306_multiple_roles_keep_their_own_gender(self):
        title = 'Köln | "männlicher Patient in Zahnarztpraxis", 45 - 65 J., "weibliche Sprechstundenhilfe", 25 - 35 J. | ganzer Drehtag, 13.10. | 140€'
        result = parse_offer({
            "offer_id": "91.306",
            "publication_date": "2026-10-08 10:00",
            "title": title,
            "raw_text": "",
        })
        self.assertEqual(len(result["profiles"]), 2)
        self.assertEqual(result["profiles"][0]["gender"], ["male"])
        self.assertEqual(result["profiles"][1]["gender"], ["female"])
        self.assertEqual(result["profiles"][0]["age_min"], 45)
        self.assertEqual(result["profiles"][0]["age_max"], 65)
        self.assertEqual(result["profiles"][1]["age_min"], 25)
        self.assertEqual(result["profiles"][1]["age_max"], 35)
        self.assertIn("45–65 ans", result["age_description"])
        self.assertIn("25–35 ans", result["age_description"])
        self.assertNotIn("sexe_annonce_non_precise", result["parser_review_reasons"])
        self.assertNotIn("age_non_numerique", result["parser_review_reasons"])


if __name__ == "__main__":
    unittest.main()
