import json
import unittest
from pathlib import Path

from scraper.matching import (
    calculate_age_at_date,
    classify_location,
    deduplicate_matches,
    match_offer_to_profile,
    match_offer_to_profiles,
)


class MatchingV1Tests(unittest.TestCase):

    def setUp(self):

        self.male_35 = {

            "id":
                "user-male-35",

            "birth_date":
                "1990-10-21",

            "gender":
                "male",

        }


        self.female_30 = {

            "id":
                "user-female-30",

            "birth_date":
                "1996-06-15",

            "gender":
                "female",

        }


        self.male_56 = {

            "id":
                "user-male-56",

            "birth_date":
                "1970-01-01",

            "gender":
                "male",

        }


        self.female_70 = {

            "id":
                "user-female-70",

            "birth_date":
                "1956-05-10",

            "gender":
                "female",

        }


    # ========================================================
    # OUTIL POUR CRÉER UNE OFFRE DE TEST
    # ========================================================

    @staticmethod
    def make_offer(
        location,
        age_min,
        age_max,
        genders,
        offer_id="offer-test",
        shoot_date="2026-10-20",
    ):

        return {

            "offer_id":
                offer_id,

            "location":
                location,

            "shoot_date":
                shoot_date,

            "age_min":
                age_min,

            "age_max":
                age_max,

            "genders":
                genders,

        }


    # ========================================================
    # 1. MATCH PARFAIT
    # ========================================================

    def test_01_perfect_match(self):

        offer = self.make_offer(

            "Raum Köln",

            35,

            35,

            ["male"],

        )


        result = match_offer_to_profile(
            offer,
            self.male_35
        )


        self.assertTrue(
            result["matched"]
        )


        self.assertEqual(

            result["reason"],

            {

                "location":
                    True,

                "age":
                    True,

                "gender":
                    True,

            }

        )


    # ========================================================
    # 2. MAUVAIS ÂGE
    # ========================================================

    def test_02_wrong_age(self):

        offer = self.make_offer(

            "Raum Köln",

            40,

            50,

            ["male"],

        )


        self.assertFalse(

            match_offer_to_profile(
                offer,
                self.male_35
            )

        )


    # ========================================================
    # 3. MAUVAIS SEXE
    # ========================================================

    def test_03_wrong_gender(self):

        offer = self.make_offer(

            "Raum Köln",

            30,

            40,

            ["female"],

        )


        self.assertFalse(

            match_offer_to_profile(
                offer,
                self.male_35
            )

        )


    # ========================================================
    # 4. BERLIN
    # ========================================================

    def test_04_berlin_is_outside_v1(self):

        offer = self.make_offer(

            "Berlin",

            30,

            40,

            ["male"],

        )


        self.assertFalse(

            match_offer_to_profile(
                offer,
                self.male_35
            )

        )


    # ========================================================
    # 5. GROSSRAUM KÖLN
    # ========================================================

    def test_05_grossraum_koln(self):

        offer = self.make_offer(

            "Großraum Köln",

            30,

            40,

            ["male"],

        )


        result = match_offer_to_profile(
            offer,
            self.male_35
        )


        self.assertTrue(
            result["matched"]
        )


    # ========================================================
    # 6. GROSSRAUM KÖLN/BONN/DÜSSELDORF
    # ========================================================

    def test_06_grossraum_koln_bonn_duesseldorf(self):

        offer = self.make_offer(

            "Großraum Köln/Bonn/Düsseldorf",

            30,

            40,

            ["m/w/d"],

        )


        male_result = match_offer_to_profile(
            offer,
            self.male_35
        )


        female_result = match_offer_to_profile(
            offer,
            self.female_30
        )


        self.assertTrue(
            male_result["matched"]
        )


        self.assertTrue(
            female_result["matched"]
        )


    # ========================================================
    # 7. GROSSRAUM KÖLN/DÜSSELDORF
    # ========================================================

    def test_07_grossraum_koln_duesseldorf(self):

        offer = self.make_offer(

            "Großraum Köln/Düsseldorf",

            50,

            60,

            ["male"],

        )


        result = match_offer_to_profile(
            offer,
            self.male_56
        )


        self.assertTrue(
            result["matched"]
        )


    # ========================================================
    # 8. KÖLN +100 KM
    # ========================================================

    def test_08_koln_plus_100km(self):

        offer = self.make_offer(

            "Köln +100km",

            30,

            40,

            ["male"],

        )


        result = match_offer_to_profile(
            offer,
            self.male_35
        )


        self.assertTrue(
            result["matched"]
        )


    # ========================================================
    # 9. NRW = MANUAL REVIEW
    # ========================================================

    def test_09_nrw_requires_manual_review(self):

        offer = self.make_offer(

            "NRW",

            30,

            40,

            ["male"],

        )


        result = match_offer_to_profile(
            offer,
            self.male_35
        )


        self.assertTrue(
            result["manual_review"]
        )


        self.assertFalse(
            result["matched"]
        )


    # ========================================================
    # 10. DEUTSCHLANDWEIT = MANUAL REVIEW
    # ========================================================

    def test_10_deutschlandweit_requires_manual_review(self):

        offer = self.make_offer(

            "Deutschlandweit",

            30,

            40,

            ["male"],

        )


        result = match_offer_to_profile(
            offer,
            self.male_35
        )


        self.assertTrue(
            result["manual_review"]
        )


        self.assertFalse(
            result["matched"]
        )


    # ========================================================
    # 11. PLUSIEURS RÔLES
    # ========================================================

    def test_11_multiple_roles_match_second_role(self):

        offer = {

            "offer_id":
                "91.306",

            "location":
                "Großraum Köln",

            "shoot_date":
                "2026-10-13",

            "profiles": [

                {

                    "role":
                        "männlicher Patient",

                    "age_min":
                        45,

                    "age_max":
                        65,

                    "genders":
                        ["male"],

                },

                {

                    "role":
                        "weibliche Sprechstundenhilfe",

                    "age_min":
                        25,

                    "age_max":
                        35,

                    "genders":
                        ["female"],

                },

            ],

        }


        result = match_offer_to_profile(

            offer,

            self.female_30

        )


        self.assertTrue(
            result["matched"]
        )


        self.assertEqual(
            result["profile_index"],
            1
        )


    # ========================================================
    # 12. PAS DE FAUX MATCH ENTRE DEUX RÔLES
    # ========================================================

    def test_12_multiple_roles_no_global_false_positive(self):

        offer = {

            "offer_id":
                "91.306",

            "location":
                "Großraum Köln",

            "shoot_date":
                "2026-10-13",

            "profiles": [

                {

                    "role":
                        "männlicher Patient",

                    "age_min":
                        45,

                    "age_max":
                        65,

                    "genders":
                        ["male"],

                },

                {

                    "role":
                        "weibliche Sprechstundenhilfe",

                    "age_min":
                        25,

                    "age_max":
                        35,

                    "genders":
                        ["female"],

                },

            ],

        }


        # Homme de 35 ans :
        # aucun des deux rôles.
        result = match_offer_to_profile(

            offer,

            self.male_35

        )


        self.assertFalse(
            result
        )


    # ========================================================
    # 13. ÂGE CALCULÉ À LA DATE DU TOURNAGE
    # ========================================================

    def test_13_age_is_calculated_at_shoot_date(self):

        # Né le 21/10/1990 :
        # encore 35 ans le 20/10/2026.
        age = calculate_age_at_date(

            "1990-10-21",

            "2026-10-20"

        )


        self.assertEqual(
            age,
            35
        )


        offer = self.make_offer(

            "Raum Köln",

            35,

            35,

            ["male"],

        )


        result = match_offer_to_profile(

            offer,

            {

                "id":
                    "user-birthday",

                "birth_date":
                    "1990-10-21",

                "gender":
                    "male",

            }

        )


        self.assertTrue(
            result["matched"]
        )


    # ========================================================
    # 14. DÉDOUBLONNAGE
    # ========================================================

    def test_14_duplicate_matches_are_removed(self):

        matches = [

            {

                "offer_id":
                    "91.309",

                "user_id":
                    "u1",

                "reason": {

                    "location":
                        True,

                    "age":
                        True,

                    "gender":
                        True,

                },

            },

            {

                "offer_id":
                    "91.309",

                "user_id":
                    "u1",

                "reason": {

                    "location":
                        True,

                    "age":
                        True,

                    "gender":
                        True,

                },

            },

            {

                "offer_id":
                    "91.309",

                "user_id":
                    "u2",

                "reason": {

                    "location":
                        True,

                    "age":
                        True,

                    "gender":
                        True,

                },

            },

        ]


        result = deduplicate_matches(
            matches
        )


        self.assertEqual(
            len(result),
            2
        )


    # ========================================================
    # 15. TEST DES LOCALISATIONS V1
    # ========================================================

    def test_15_supported_locations(self):

        supported_locations = [

            "Großraum Köln",

            "Großraum Bonn",

            "Großraum Düsseldorf",

            "Großraum Köln/Düsseldorf",

            "Großraum Köln/Bonn/Düsseldorf",

            "Raum Köln",

            "Köln & Umgebung",

            "Köln und Umgebung",

            "Köln +100 km",

            "Köln +100km",

            "Köln +150 km",

            "Köln +150km",

        ]


        for location in supported_locations:

            with self.subTest(
                location=location
            ):

                self.assertEqual(

                    classify_location(
                        location
                    ),

                    "v1"

                )


    # ========================================================
    # 16. TEST DES CAS AMBIGUS
    # ========================================================

    def test_16_ambiguous_locations(self):

        ambiguous_locations = [

            "NRW",

            "NRW + Grenzregion NL/BE (deutschsprachig)",

            "Deutschlandweit",

            "Bundesweit",

        ]


        for location in ambiguous_locations:

            with self.subTest(
                location=location
            ):

                self.assertEqual(

                    classify_location(
                        location
                    ),

                    "manual_review"

                )


    # ========================================================
    # 17. TEST SUR LES OFFRES PARSÉES ACTUELLES
    # ========================================================

    def test_17_current_parsed_offers(self):

        project_root = Path(
            __file__
        ).resolve().parent.parent


        parsed_file = (
            project_root
            / "komparse_parsed_offers.json"
        )


        self.assertTrue(
            parsed_file.exists()
        )


        with parsed_file.open(
            "r",
            encoding="utf-8"
        ) as file:

            parsed_data = json.load(
                file
            )


        # Accepte soit une liste directe,
        # soit un objet contenant une liste.
        if isinstance(
            parsed_data,
            list
        ):

            offers = parsed_data

        elif isinstance(
            parsed_data,
            dict
        ):

            offers = (
                parsed_data.get(
                    "offers"
                )
                or parsed_data.get(
                    "results"
                )
                or []
            )

        else:

            offers = []


        # Le jeu actuel doit contenir
        # suffisamment d'offres pour la validation.
        self.assertGreaterEqual(
            len(offers),
            10
        )


        test_profiles = [

            self.male_35,

            self.female_30,

            self.male_56,

            self.female_70,

        ]


        selected_offers = offers[:20]


        all_matches = []


        for offer in selected_offers:

            matches = match_offer_to_profiles(

                offer,

                test_profiles

            )


            all_matches.extend(
                matches
            )


        # Aucune duplication automatique
        keys = [

            (
                match["offer_id"],
                match["user_id"]
            )

            for match in all_matches

        ]


        self.assertEqual(

            len(keys),

            len(set(keys))

        )


    # ========================================================
    # 18. TESTS SPÉCIFIQUES SUR LES OFFRES CONNUES
    # ========================================================

    def test_18_known_current_offers(self):

        project_root = Path(
            __file__
        ).resolve().parent.parent


        parsed_file = (
            project_root
            / "komparse_parsed_offers.json"
        )


        if not parsed_file.exists():
            self.skipTest(
                "komparse_parsed_offers.json introuvable"
            )


        with parsed_file.open(
            "r",
            encoding="utf-8"
        ) as file:

            parsed_data = json.load(
                file
            )


        if isinstance(
            parsed_data,
            list
        ):

            offers = parsed_data

        else:

            offers = (
                parsed_data.get(
                    "offers"
                )
                or parsed_data.get(
                    "results"
                )
                or []
            )


        offers_by_id = {}


        for offer in offers:

            offer_id = (

                offer.get("id")

                or offer.get("offer_id")

            )


            if offer_id is not None:

                offers_by_id[
                    str(offer_id)
                ] = offer


        # Offre 91.309 :
        # Großraum Köln/Düsseldorf,
        # homme 50-60 ans.
        offer_91309 = offers_by_id.get(
            "91.309"
        )


        if offer_91309:

            result = match_offer_to_profile(

                offer_91309,

                self.male_56

            )


            self.assertTrue(
                result["matched"]
            )


        # Offre 91.302 :
        # Großraum Köln/Bonn/Düsseldorf,
        # femme 68-85 ans.
        offer_91302 = offers_by_id.get(
            "91.302"
        )


        if offer_91302:

            result = match_offer_to_profile(

                offer_91302,

                self.female_70

            )


            self.assertTrue(
                result["matched"]
            )


if __name__ == "__main__":

    unittest.main(
        verbosity=2
    )