import unittest

from scraper.supabase_store import apply_admin_qualification


class TestAdminQualificationPersistence(unittest.TestCase):
    def test_manual_values_override_later_parser_values(self):
        parsed = {
            "komparse_id": "91312",
            "title": "Parser title",
            "location_text": "NRW",
            "location_status": "manual_review",
            "shoot_date": None,
            "shoot_date_text": None,
            "shoot_duration_text": None,
            "age_min": None,
            "age_max": None,
            "age_description": None,
            "gender_male": False,
            "gender_female": False,
            "application_method": "unknown",
            "application_url": None,
            "parser_needs_review": True,
            "parser_review_reason": "sexe_annonce_non_precise",
            "admin_review_required": True,
        }
        existing = {
            "admin_qualified": True,
            "title": "Titre corrigé par admin",
            "location_text": "Köln",
            "location_status": "v1",
            "shoot_date": "2026-10-20",
            "shoot_date_text": "20 octobre 2026",
            "shoot_duration_text": "1 journée",
            "age_min": 18,
            "age_max": None,
            "age_description": "ab 18 Jahren",
            "gender_male": True,
            "gender_female": True,
            "application_method": "email",
            "application_url": None,
            "parser_needs_review": False,
            "parser_review_reason": None,
            "admin_review_required": False,
        }

        result = apply_admin_qualification(parsed, existing)

        self.assertEqual(result["title"], "Titre corrigé par admin")
        self.assertEqual(result["location_text"], "Köln")
        self.assertEqual(result["location_status"], "v1")
        self.assertEqual(result["shoot_date"], "2026-10-20")
        self.assertEqual(result["age_min"], 18)
        self.assertTrue(result["gender_male"])
        self.assertTrue(result["gender_female"])
        self.assertTrue(result["admin_qualified"])
        self.assertFalse(result["parser_needs_review"])
        self.assertIsNone(result["parser_review_reason"])
        self.assertFalse(result["admin_review_required"])

    def test_unqualified_offer_keeps_parser_values(self):
        parsed = {
            "komparse_id": "91312",
            "location_text": "NRW",
            "parser_needs_review": True,
            "parser_review_reason": "sexe_annonce_non_precise",
        }

        result = apply_admin_qualification(parsed, {
            "admin_qualified": False,
            "location_text": "Köln",
        })

        self.assertEqual(result["location_text"], "NRW")
        self.assertTrue(result["parser_needs_review"])
        self.assertFalse(result["admin_qualified"])


if __name__ == "__main__":
    unittest.main()
