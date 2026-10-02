import unicodedata
import unittest

import nlptutti as nt


class TestUnicodeMatching(unittest.TestCase):
    def test_keyword_matching_normalizes_text_dictionary_and_suffixes(self):
        for form in ("NFC", "NFD", "NFKC", "NFKD"):
            for input_form in ("NFC", "NFD"):
                for dictionary_form in ("NFC", "NFD"):
                    keyword = unicodedata.normalize(dictionary_form, "서울")
                    for text, count in (
                        ("서울", 1),
                        ("서울은", 1),
                        ("서울대학교", 0),
                        ("신서울", 0),
                    ):
                        with self.subTest(
                            form=form,
                            input=input_form,
                            dictionary=dictionary_form,
                            text=text,
                        ):
                            result = nt.evaluate_keywords(
                                [text],
                                [unicodedata.normalize(input_form, text)],
                                [keyword],
                                unicode_normalization=form,
                            )
                            self.assertEqual(
                                result["summary"]["reference_count"], count
                            )
                            self.assertEqual(result["summary"]["true_positives"], count)
                            self.assertIn(keyword, result["keywords"])

    def test_entities_keep_boundaries_aliases_and_suffixes_in_each_form(self):
        for form in ("NFC", "NFD", "NFKC", "NFKD"):
            for text, count in (
                ("서울", 1),
                ("서울은", 1),
                ("서울대학교", 0),
                ("신서울", 0),
            ):
                with self.subTest(form=form, text=text):
                    result = nt.evaluate_entities(
                        [text], [text], ["서울"], unicode_normalization=form
                    )
                    self.assertEqual(result["summary"]["reference_count"], count)
                    self.assertEqual(result["summary"]["true_positives"], count)
            result = nt.evaluate_entities(
                ["서울시쯤"],
                ["서울쯤"],
                ["서울시"],
                aliases={"서울시": ["서울"]},
                josa_list=["쯤"],
                eomi_list=[],
                unicode_normalization=form,
            )
            self.assertEqual(result["summary"]["true_positives"], 1)
            self.assertEqual(result["entity_cer"]["micro"], 0)

    def test_none_keeps_unicode_distinctions_and_punctuation_is_not_stripped(self):
        nfd = unicodedata.normalize("NFD", "서울")
        result = nt.evaluate_keywords(["서울"], [nfd], ["서울"])
        self.assertEqual(result["summary"]["recall"], 0)
        for form in (None, "NFC", "NFD", "NFKC", "NFKD"):
            result = nt.evaluate_keywords(
                ["C++"], ["C"], ["C++"], unicode_normalization=form
            )
            self.assertEqual(result["summary"]["recall"], 0)

    def test_compatibility_characters_and_combining_marks_are_explicit(self):
        for form, count in (("NFC", 0), ("NFKC", 1), ("NFKD", 1)):
            result = nt.evaluate_keywords(
                ["ＡＩ"], ["AI"], ["AI"], unicode_normalization=form
            )
            self.assertEqual(result["summary"]["true_positives"], count)
        for suffix in ("\u1100", "\u3131", "\ua960", "\ud7b0", "\u0301"):
            self.assertIsNone(nt.make_keyword_pattern("서울").search("서울" + suffix))
        self.assertIsNone(nt.make_keyword_pattern("cafe").search("cafe\u0301"))

    def test_normalization_collisions_and_invalid_modes_fail(self):
        for keywords, form in (
            (["서울", unicodedata.normalize("NFD", "서울")], "NFC"),
            (["AI", "ＡＩ"], "NFKC"),
        ):
            with self.subTest(form=form), self.assertRaisesRegex(ValueError, "unique"):
                nt.evaluate_keywords(
                    ["서울"], ["서울"], keywords, unicode_normalization=form
                )
        with self.assertRaises(ValueError):
            nt.evaluate_keywords(
                ["서울"], ["서울"], ["서울"], unicode_normalization="bad"
            )

    def test_compare_passes_normalization_and_fingerprints_the_policy(self):
        nfd = unicodedata.normalize("NFD", "서울")

        def compare(form):
            return nt.compare_systems(
                ["서울"],
                {"a": [nfd], "b": ["서울"]},
                keywords=["서울"],
                entities=["서울"],
                unicode_normalization=form,
            )

        report = compare("NFC")
        system = report["systems"][0]
        self.assertEqual(system["metrics"]["cer"]["micro"], 0)
        self.assertEqual(system["keywords"]["summary"]["recall"], 1)
        self.assertEqual(system["entities"]["summary"]["recall"], 1)
        self.assertNotEqual(
            report["evaluation_config"]["sha256"],
            compare(None)["evaluation_config"]["sha256"],
        )
        self.assertEqual(report, compare("nfc"))
