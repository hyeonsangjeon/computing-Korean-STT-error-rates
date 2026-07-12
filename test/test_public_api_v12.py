import itertools
import unicodedata
import unittest

import nlptutti as nt


class TestRateModes(unittest.TestCase):
    def test_normalized_mode_remains_the_default(self):
        default_result = nt.get_cer("STEAM", "STREAM")
        explicit_result = nt.get_cer("STEAM", "STREAM", rate_mode="normalized")

        self.assertEqual(default_result, explicit_result)
        self.assertEqual(
            set(default_result),
            {"cer", "substitutions", "deletions", "insertions"},
        )
        self.assertAlmostEqual(default_result["cer"], 1 / 6)

    def test_standard_mode_uses_reference_length(self):
        self.assertAlmostEqual(
            nt.get_cer("STEAM", "STREAM", rate_mode="standard")["cer"],
            1 / 5,
        )
        self.assertAlmostEqual(
            nt.get_wer(
                "hello world",
                "hello very big world",
                rate_mode="standard",
            )["wer"],
            1.0,
        )

    def test_standard_mode_counts_insertions_for_empty_reference(self):
        self.assertEqual(
            nt.get_cer("", "가나다", rate_mode="standard")["cer"],
            3.0,
        )
        self.assertEqual(
            nt.get_wer("", "hello world", rate_mode="standard")["wer"],
            2.0,
        )

    def test_crr_default_remains_normalized(self):
        self.assertEqual(
            nt.get_crr("STEAM", "STREAM"),
            nt.get_crr("STEAM", "STREAM", rate_mode="normalized"),
        )

    def test_invalid_rate_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            nt.get_cer("가", "나", rate_mode="legacy")

    def test_unicode_normalization_is_opt_in(self):
        reference = "가"
        decomposed = unicodedata.normalize("NFD", reference)

        self.assertEqual(nt.get_cer(reference, decomposed)["cer"], 1.0)
        self.assertEqual(
            nt.get_cer(
                reference,
                decomposed,
                unicode_normalization="NFC",
            )["cer"],
            0.0,
        )

    def test_invalid_unicode_normalization_is_rejected(self):
        with self.assertRaises(ValueError):
            nt.get_cer("가", "가", unicode_normalization="UTF-8")


class TestCorpusEvaluation(unittest.TestCase):
    def test_evaluate_corpus_returns_micro_and_macro_rates(self):
        report = nt.evaluate_corpus(
            ["가나", "다라"],
            ["가마", "다라바"],
        )

        self.assertEqual(report["rate_mode"], "normalized")
        self.assertEqual(report["utterances"], 2)
        self.assertEqual(report["perfect_sentences"], 0)
        self.assertEqual(report["sentence_error_rate"], 1.0)
        self.assertAlmostEqual(report["cer"]["micro"], 2 / 5)
        self.assertAlmostEqual(report["cer"]["macro"], (1 / 2 + 1 / 3) / 2)
        self.assertEqual(report["cer"]["substitutions"], 1)
        self.assertEqual(report["cer"]["insertions"], 1)
        self.assertEqual(report["cer"]["hits"], 3)

    def test_evaluate_corpus_supports_standard_mode(self):
        report = nt.evaluate_corpus(
            ["가나", "다라"],
            ["가마", "다라바"],
            rate_mode="standard",
        )

        self.assertAlmostEqual(report["cer"]["micro"], 1 / 2)
        self.assertAlmostEqual(report["cer"]["macro"], 1 / 2)

    def test_evaluate_corpus_accepts_generators(self):
        references = (value for value in ["가", "나"])
        hypotheses = (value for value in ["가", "다"])

        report = nt.evaluate_corpus(references, hypotheses)

        self.assertEqual(report["utterances"], 2)

    def test_evaluate_corpus_rejects_invalid_collections(self):
        with self.assertRaises(TypeError):
            nt.evaluate_corpus("가나다", ["가나다"])
        with self.assertRaises(ValueError):
            nt.evaluate_corpus([], [])
        with self.assertRaises(ValueError):
            nt.evaluate_corpus(["가"], [])


class TestKeywordEvaluation(unittest.TestCase):
    def test_evaluate_keywords_counts_mentions_and_false_positives(self):
        report = nt.evaluate_keywords(
            [
                "삼성전자와 삼성전자가 협력했다.",
                "애플이 발표했다.",
            ],
            [
                "삼성전자가 협력했다.",
                "애플과 삼성전자가 발표했다.",
            ],
            {"ORG": ["삼성전자", "애플"]},
        )

        samsung = report["keywords"]["삼성전자"]
        self.assertEqual(samsung["reference_count"], 2)
        self.assertEqual(samsung["hypothesis_count"], 2)
        self.assertEqual(samsung["true_positives"], 1)
        self.assertEqual(samsung["false_positives"], 1)
        self.assertEqual(samsung["false_negatives"], 1)
        self.assertEqual(samsung["precision"], 0.5)
        self.assertEqual(samsung["recall"], 0.5)
        self.assertEqual(samsung["f1"], 0.5)

        self.assertEqual(report["summary"]["true_positives"], 2)
        self.assertEqual(report["summary"]["false_positives"], 1)
        self.assertEqual(report["summary"]["false_negatives"], 1)
        self.assertAlmostEqual(report["labels"]["ORG"]["f1"], 2 / 3)

    def test_spaced_keyword_matches_joined_and_spaced_mentions(self):
        report = nt.evaluate_keywords(
            ["메리츠화재가 상승했다."],
            ["메리츠 화재가 상승했다."],
            ["메리츠 화재"],
        )

        stats = report["keywords"]["메리츠 화재"]
        self.assertEqual(stats["true_positives"], 1)
        self.assertEqual(stats["preservation_rate"], 1.0)

    def test_make_keyword_pattern_has_safe_josa_defaults(self):
        pattern = nt.make_keyword_pattern("삼성전자")

        self.assertTrue(pattern.search("삼성전자는 발표했다."))
        self.assertFalse(pattern.search("삼성전자제품"))

    def test_whitespace_equivalent_duplicate_keywords_are_rejected(self):
        with self.assertRaises(ValueError):
            nt.evaluate_keywords(
                ["메리츠화재"],
                ["메리츠화재"],
                ["메리츠화재", "메리츠 화재"],
            )


class TestErrorExplanation(unittest.TestCase):
    def test_explain_errors_returns_alignment_and_frequencies(self):
        report = nt.explain_errors("아키택트", "아키택쳐")

        self.assertEqual(report["metric"], "cer")
        self.assertEqual(report["rate"], 0.25)
        self.assertEqual(report["counts"]["hits"], 3)
        self.assertEqual(report["counts"]["substitutions"], 1)
        self.assertEqual(
            report["error_frequencies"]["substitutions"],
            [{"reference": "트", "hypothesis": "쳐", "count": 1}],
        )

    def test_explain_errors_supports_word_mode(self):
        report = nt.explain_errors(
            "나는 사과를 먹는다.",
            "나는 배를 먹는다.",
            unit="word",
        )

        self.assertEqual(report["metric"], "wer")
        self.assertAlmostEqual(report["rate"], 1 / 3)
        self.assertEqual(report["counts"]["substitutions"], 1)

    def test_explanation_matches_legacy_edit_tie_breaking(self):
        alphabet = "가나"
        strings = [""]
        for length in range(1, 4):
            strings.extend(
                "".join(characters)
                for characters in itertools.product(alphabet, repeat=length)
            )

        for reference in strings:
            for hypothesis in strings:
                metric = nt.get_cer(
                    reference,
                    hypothesis,
                    rm_punctuation=False,
                )
                explanation = nt.explain_errors(
                    reference,
                    hypothesis,
                    rm_punctuation=False,
                )
                self.assertEqual(
                    explanation["counts"]["substitutions"],
                    metric["substitutions"],
                )
                self.assertEqual(
                    explanation["counts"]["deletions"],
                    metric["deletions"],
                )
                self.assertEqual(
                    explanation["counts"]["insertions"],
                    metric["insertions"],
                )
                self.assertAlmostEqual(explanation["rate"], metric["cer"])

    def test_word_explanation_matches_legacy_edit_tie_breaking(self):
        vocabulary = ("가", "나")
        sentences = [""]
        for length in range(1, 4):
            sentences.extend(
                " ".join(tokens)
                for tokens in itertools.product(vocabulary, repeat=length)
            )

        for reference in sentences:
            for hypothesis in sentences:
                metric = nt.get_wer(
                    reference,
                    hypothesis,
                    rm_punctuation=False,
                )
                explanation = nt.explain_errors(
                    reference,
                    hypothesis,
                    unit="word",
                    rm_punctuation=False,
                )
                self.assertEqual(
                    explanation["counts"]["substitutions"],
                    metric["substitutions"],
                )
                self.assertEqual(
                    explanation["counts"]["deletions"],
                    metric["deletions"],
                )
                self.assertEqual(
                    explanation["counts"]["insertions"],
                    metric["insertions"],
                )
                self.assertAlmostEqual(explanation["rate"], metric["wer"])

    def test_explain_errors_rejects_unknown_unit(self):
        with self.assertRaises(ValueError):
            nt.explain_errors("가", "나", unit="sentence")


if __name__ == "__main__":
    unittest.main()
