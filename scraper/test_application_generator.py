import unittest

from scraper.application_generator import (
    build_application
)


class ApplicationGeneratorTests(
    unittest.TestCase
):

    def setUp(self):

        self.offer = {

            "id":
                "91.309",

            "email":
                "heileweltcasting@gmail.com",

            "subject_keyword":
                "Kollegen",

            "shoot_date":
                "2026-10-09",

            "location":
                "Großraum Köln/Düsseldorf",

        }


        self.profile = {

            "first_name":
                "Max",

            "last_name":
                "Mustermann",

            "city":
                "Köln",

            "phone":
                "+49 170 1234567",

            "birth_date":
                "1970-01-01",

            "clothing_size":
                "L",

            "height_cm":
                180,

            "shoe_size":
                "43",

        }


        self.photos = [

            "user-id/portrait-123.jpg",

            "user-id/left-456.jpg",

            "user-id/right-789.jpg",

            "user-id/full_body-999.jpg",

        ]


    # ========================================================
    # TEST 1 — DESTINATAIRE
    # ========================================================

    def test_recipient(self):

        application = build_application(

            self.offer,

            self.profile,

            self.photos

        )


        self.assertEqual(

            application["to"],

            "heileweltcasting@gmail.com"

        )


    # ========================================================
    # TEST 2 — BETREFF
    # ========================================================

    def test_subject_keyword_is_preserved(self):

        application = build_application(

            self.offer,

            self.profile,

            self.photos

        )


        self.assertEqual(

            application["subject"],

            "Kollegen"

        )


    # ========================================================
    # TEST 3 — DATE
    # ========================================================

    def test_shoot_date_is_in_body(self):

        application = build_application(

            self.offer,

            self.profile,

            self.photos

        )


        self.assertIn(

            "2026-10-09",

            application["body"]

        )


    # ========================================================
    # TEST 4 — DONNÉES PROFIL
    # ========================================================

    def test_profile_information_is_in_body(self):

        application = build_application(

            self.offer,

            self.profile,

            self.photos

        )


        body = application["body"]


        self.assertIn(
            "Max Mustermann",
            body
        )


        self.assertIn(
            "Köln",
            body
        )


        self.assertIn(
            "+49 170 1234567",
            body
        )


        self.assertIn(
            "1970-01-01",
            body
        )


        self.assertIn(
            "L",
            body
        )


        self.assertIn(
            "180 cm",
            body
        )


        self.assertIn(
            "43",
            body
        )


    # ========================================================
    # TEST 5 — QUATRE PHOTOS
    # ========================================================

    def test_four_photos_are_prepared(self):

        application = build_application(

            self.offer,

            self.profile,

            self.photos

        )


        self.assertEqual(

            len(
                application["attachments"]
            ),

            4

        )


        self.assertEqual(

            application["attachments"],

            self.photos

        )


    # ========================================================
    # TEST 6 — FALLBACK BETREFF
    # ========================================================

    def test_subject_fallback(self):

        offer = {

            "email":
                "casting@example.com",

            "shoot_date":
                "2026-11-05",

        }


        application = build_application(

            offer,

            self.profile,

            self.photos

        )


        self.assertEqual(

            application["subject"],

            "Bewerbung Komparse 2026-11-05"

        )


    # ========================================================
    # TEST 7 — RÔLE
    # ========================================================

    def test_role_is_preserved(self):

        offer = {

            "email":
                "casting@example.com",

            "subject_keyword":
                "Sohn",

            "shoot_date":
                "2026-10-08",

            "role":
                "Sohn",

        }


        application = build_application(

            offer,

            self.profile,

            self.photos

        )


        self.assertIn(

            "als Sohn",

            application["body"]

        )


if __name__ == "__main__":

    unittest.main(
        verbosity=2
    )