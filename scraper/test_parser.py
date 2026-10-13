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
    parse_detail_page,
    enrich_offer_from_detail,
)
from scraper.extract_offers import extract_title


class TestCompoundLocationRules(unittest.TestCase):
    def test_ruhrgebiet_reinland_is_reviewed_not_silently_excluded(self):
        result = detect_location("Raum Ruhrgebiet/Reinland | unsportliche Paarungen (25-45)")
        self.assertEqual(result["location_status"], "manual_review")
        self.assertFalse(result["matches_mvp"])

    def test_unambiguous_outside_location_stays_outside(self):
        result = detect_location("Raum München")
        self.assertEqual(result["location_status"], "outside")
        self.assertFalse(result["matches_mvp"])


class TestAgeParsing(unittest.TestCase):
    def test_age_bis(self):
        result = extract_age_ranges("männl. Komparse (35 bis 60 Jahre)")
        self.assertEqual(result[0]["min"], 35)
        self.assertEqual(result[0]["max"], 60)

    def test_clothing_size_is_not_mistaken_for_an_age_range(self):
        title = "Großraum Köln | 3 junge weibliche Kompars.innen (18 bis 45 Jahre - Konf. 36 bis 40)"
        result = parse_offer({
            "offer_id": "91.321",
            "publication_date": "2026-10-10 10:00",
            "title": title,
            "raw_text": "",
            "detail_url": "https://komparse.de/Gesuch91321.htm",
        })
        self.assertEqual((result["age_min"], result["age_max"]), (18, 45))
        self.assertEqual(result["age_description"], "18 bis 45 Jahre")

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

    def test_mitte_age_ranges(self):
        for decade in range(20, 100, 10):
            with self.subTest(decade=decade):
                result = extract_age_ranges(f"Kleindarstellerin, Mitte {decade}")
                self.assertTrue(result)
                self.assertEqual(result[0]["min"], decade)
                self.assertEqual(result[0]["max"], decade + 9)

    def test_mitte_40_is_propagated_to_profile(self):
        result = extract_profiles("Raum Köln | Kleindarstellerin, Mitte 40")
        self.assertTrue(result)
        self.assertEqual(result[0]["age_min"], 40)
        self.assertEqual(result[0]["age_max"], 49)

    def test_explicit_spielalter_range_without_unit(self):
        result = extract_age_ranges("Darsteller, Spielalter 30-40")
        self.assertEqual((result[0]["min"], result[0]["max"]), (30, 40))

    def test_explicit_alter_range_without_unit(self):
        result = extract_age_ranges("Alter: 18–23")
        self.assertEqual((result[0]["min"], result[0]["max"]), (18, 23))

    def test_parenthesized_age_range_without_unit(self):
        result = extract_age_ranges("unsportliche Paarungen (25-45)")
        self.assertEqual((result[0]["min"], result[0]["max"]), (25, 45))

    def test_parenthesized_duration_range_is_not_age(self):
        self.assertEqual(extract_age_ranges("Drehdauer (2-3 Drehtage)"), [])

    def test_duration_range_without_age_cue_is_not_age(self):
        self.assertEqual(extract_age_ranges("2-3 Drehtage im Zeitraum"), [])

    def test_duration_hours_is_not_mistaken_for_age(self):
        self.assertEqual(extract_age_ranges("ca. 2 bis 3 Stunden Drehzeit"), [])

    def test_date_endpoint_is_not_mistaken_for_age(self):
        self.assertEqual(extract_age_ranges("vom 13. bis 16.10.2026"), [])

    def test_jungs_is_male(self):
        self.assertEqual(detect_gender("Jungs, 8-10 Jahre"), {"male"})

    def test_weibliches_picture_double_is_female(self):
        self.assertEqual(detect_gender("weibliches Picture Double, 35-55 Jahre"), {"female"})

    def test_singlemuetter_is_female(self):
        self.assertEqual(detect_gender("Singlemütter für Datingformat"), {"female"})


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

    def test_einzelpersonen_und_paare_is_mixed(self):
        self.assertEqual(
            detect_gender("Einzelpersonen und Paare (ca. 22-70 Jahre)"),
            {"male", "female"},
        )

    def test_damen_und_herren_is_mixed(self):
        title = "Raum KÖLN | 3 Damen und Herren als Redakteure einer Tageszeitung, 25 bis 55 Jahre | 15. Oktober"
        self.assertEqual(detect_gender(title), {"male", "female"})

    def test_damen_only_is_female(self):
        self.assertEqual(detect_gender("Damen für eine Fernsehproduktion"), {"female"})

    def test_herren_only_is_male(self):
        self.assertEqual(detect_gender("Herren für eine Fernsehproduktion"), {"male"})


class TestScheduleParsing(unittest.TestCase):
    def test_explicit_date_range_takes_precedence_over_broad_month(self):
        title = "Köln +100km | Double, 16 - 35 J. | 12 Drehtage im Zeitraum 09.11. bis 17.12. | Oktober 2026"
        self.assertEqual(
            extract_shoot_date_text(title, default_year=2026),
            "9. November bis 17. Dezember 2026",
        )

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

    def test_numeric_range_without_zeitraum_is_not_two_exact_dates(self):
        title = "Köln | Darsteller 30-50 Jahre | 09.11.2026 bis 17.12.2026"
        self.assertEqual(extract_shoot_dates(title, default_year=2026), [])
        self.assertEqual(
            extract_shoot_date_text(title, default_year=2026),
            "9. November bis 17. Dezember 2026",
        )

    def test_full_years_on_both_range_endpoints_are_preserved_as_period(self):
        title = "Köln | Darsteller 30-50 Jahre | Drehzeitraum 09.11.2026 bis 17.12.2026"
        self.assertEqual(extract_shoot_dates(title, default_year=2026), [])
        self.assertEqual(
            extract_shoot_date_text(title, default_year=2026),
            "9. November bis 17. Dezember 2026",
        )

    def test_cross_year_range_keeps_both_years(self):
        title = "Köln | Darsteller 30-50 Jahre | Drehzeitraum 28.12.2026 bis 05.01.2027"
        self.assertEqual(extract_shoot_dates(title, default_year=2026), [])
        self.assertEqual(
            extract_shoot_date_text(title, default_year=2026),
            "28. Dezember 2026 bis 5. Januar 2027",
        )

    def test_date_range_is_preserved_as_a_period_not_month_from_metadata(self):
        title = "Köln +100km | Double, 16 - 35 J. | 12 Drehtage im Zeitraum 09.11. bis 17.12. | Gage 200€"
        dates = extract_shoot_dates(title, default_year=2026)
        self.assertEqual(dates, [])
        self.assertEqual(
            extract_shoot_date_text(title, default_year=2026, shoot_dates=dates),
            "9. November bis 17. Dezember 2026",
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


class TestDetailLocationEnrichment(unittest.TestCase):
    def test_detail_page_extracts_explicit_location_label(self):
        result = parse_detail_page(
            "<html><body><p>Drehort: Köln</p><p>Die Produktion wird in Berlin geplant.</p></body></html>"
        )
        self.assertEqual(result["location_text"], "Köln")

    def test_enrichment_uses_explicit_detail_location_and_records_source(self):
        parsed = parse_offer({
            "offer_id": "test-location",
            "publication_date": "2026-10-12",
            "title": "Bundesweit | Komparse 25-40 Jahre",
            "raw_text": "",
            "detail_url": "https://komparse.de/Gesuch99999.htm",
        })
        detail = enrich_offer_from_detail(parsed, {
            "detail_text": "Drehort: Köln Die Produktion wird auch in Berlin geplant.",
            "location_text": "Köln",
            "email": None,
            "subject_keyword": None,
            "shoot_dates": [],
            "application_url": None,
            "application_method": "unknown",
        })
        self.assertEqual(detail["location_text"], "Köln")
        self.assertEqual(detail["location_status"], "v1")
        self.assertEqual(detail["field_sources"]["location_text"]["source"], "detail_page")
        self.assertEqual(detail["field_sources"]["location_text"]["url"], "https://komparse.de/Gesuch99999.htm")


class TestShootDates(unittest.TestCase):
    def test_detail_page_extracts_date_from_drehtermin_label(self):
        result = parse_detail_page(
            "<html><body><p>Drehtermin: 15. Oktober 2026</p></body></html>"
        )
        self.assertEqual(result["shoot_dates"], ["2026-10-15"])

    def test_detail_page_extracts_date_from_shooting_sentence(self):
        result = parse_detail_page(
            "<html><body><p>Die Dreharbeiten finden am 15. Oktober 2026 statt.</p></body></html>"
        )
        self.assertEqual(result["shoot_dates"], ["2026-10-15"])

    def test_numeric_date_without_trailing_dot(self):
        self.assertEqual(extract_shoot_dates("Drehtag 03.11"), ["2026-11-03"])

    def test_abbreviated_month_range_is_preserved_as_period(self):
        title = "NRW | Mieter, 30-60 Jahre | 2 Std. Dreh, gern in Woche 12. -16. Okt. | 150 Euro"
        self.assertEqual(extract_shoot_dates(title, default_year=2026), [])
        self.assertEqual(
            extract_shoot_date_text(title, default_year=2026),
            "12. bis 16. Oktober 2026",
        )

    def test_abbreviated_may_range_is_preserved_as_period(self):
        title = "Raum Köln | Frau, 30-45 Jahre | Dreh in Woche 4. -8. Mai | 150 Euro"
        self.assertEqual(extract_shoot_dates(title, default_year=2026), [])
        self.assertEqual(
            extract_shoot_date_text(title, default_year=2026),
            "4. bis 8. Mai 2026",
        )

    def test_shared_month_shooting_window_is_preserved_as_period(self):
        title = "Raum Köln | Darsteller, ca. 40-55 Jahre | 1-2 Drehtage zwischen 3. und 5. November"
        self.assertEqual(extract_shoot_dates(title, default_year=2026), [])
        self.assertEqual(
            extract_shoot_date_text(title, default_year=2026),
            "3. bis 5. November 2026",
        )

    def test_from_to_shared_month_shooting_window_is_preserved(self):
        title = "Köln | Komparse 25-40 Jahre | Dreharbeiten vom 12. bis 14. Oktober 2026"
        self.assertEqual(extract_shoot_dates(title, default_year=2026), [])
        self.assertEqual(
            extract_shoot_date_text(title, default_year=2026),
            "12. bis 14. Oktober 2026",
        )

    def test_month_to_month_shooting_window_is_preserved(self):
        title = "Großraum Köln | m/w/d, 20-60 Jahre | 1 Drehtag im Zeitraum Oktober-November"
        self.assertEqual(
            extract_shoot_date_text(title, default_year=2026),
            "Oktober bis November 2026",
        )

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

# CI trigger: ensure the pull-request test workflow runs for this branch.
