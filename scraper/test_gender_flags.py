import unittest

from scraper.gender_flags import gender_flags_from_value


class TestGenderFlagNormalization(unittest.TestCase):
    def test_female_label_does_not_imply_male(self):
        self.assertEqual(gender_flags_from_value(["female"]), (False, True))

    def test_male_label_does_not_imply_female(self):
        self.assertEqual(gender_flags_from_value(["male"]), (True, False))

    def test_explicit_mixed_labels(self):
        self.assertEqual(gender_flags_from_value(["male", "female"]), (True, True))

    def test_m_w_d_abbreviation(self):
        self.assertEqual(gender_flags_from_value("m/w/d"), (True, True))

    def test_unrecognized_gender_is_not_assumed(self):
        self.assertEqual(gender_flags_from_value(None), (False, False))


if __name__ == "__main__":
    unittest.main()
