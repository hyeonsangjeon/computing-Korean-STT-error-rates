import unicodedata
import unittest

import nlptutti as nt


class TestEntityEvaluation(unittest.TestCase):
    def test_public_api_reports_entity_cer_f1_labels_and_errors(self):
        report = nt.evaluate_entities(
            ["삼성전자의 갤럭시 S26 발표"],
            ["삼성전다의 갤럭시 S26 발표와 애플"],
            {
                "ORG": ["삼성전자", "애플"],
                "PRODUCT": ["갤럭시 S26"],
            },
        )

        self.assertEqual(report["rate_mode"], "normalized")
        self.assertAlmostEqual(report["entity_cer"]["micro"], 1 / 10)
        self.assertAlmostEqual(report["entity_cer"]["macro"], 1 / 8)
        self.assertEqual(report["entity_cer"]["substitutions"], 1)
        self.assertEqual(report["summary"]["true_positives"], 1)
        self.assertEqual(report["summary"]["false_positives"], 1)
        self.assertEqual(report["summary"]["false_negatives"], 1)
        self.assertEqual(report["summary"]["f1"], 0.5)
        self.assertEqual(report["labels"]["PRODUCT"]["f1"], 1.0)
        self.assertEqual(
            [(item["type"], item["entity"]) for item in report["errors"]],
            [("misrecognition", "삼성전자"), ("addition", "애플")],
        )
        self.assertEqual(report["errors"][0]["hypothesis"], "삼성전다")

    def test_aliases_are_opt_in_and_score_as_exact_when_configured(self):
        reference = ["갤럭시 S26을 공개했다"]
        hypothesis = ["갤럭시 에스 이십육을 공개했다"]
        entities = {"PRODUCT": ["갤럭시 S26"]}

        strict_report = nt.evaluate_entities(reference, hypothesis, entities)
        alias_report = nt.evaluate_entities(
            reference,
            hypothesis,
            entities,
            aliases={"갤럭시 S26": ["갤럭시 에스 이십육"]},
        )

        self.assertEqual(strict_report["summary"]["false_negatives"], 1)
        self.assertGreater(strict_report["entity_cer"]["micro"], 0.0)
        self.assertFalse(strict_report["aliases_enabled"])
        self.assertEqual(alias_report["summary"]["f1"], 1.0)
        self.assertEqual(alias_report["entity_cer"]["micro"], 0.0)
        self.assertEqual(alias_report["errors"], [])
        self.assertTrue(alias_report["aliases_enabled"])

    def test_spacing_and_korean_suffixes_do_not_change_entity_score(self):
        report = nt.evaluate_entities(
            ["삼성전자의 실적"],
            ["삼성 전자는 실적"],
            ["삼성전자"],
        )

        self.assertEqual(report["summary"]["f1"], 1.0)
        self.assertEqual(report["entity_cer"]["micro"], 0.0)
        self.assertEqual(report["entities"]["삼성전자"]["hits"], 4)

    def test_entity_internal_insertion_respects_rate_mode(self):
        normalized = nt.evaluate_entities(
            ["삼성전자"],
            ["삼성대전자"],
            ["삼성전자"],
        )
        standard = nt.evaluate_entities(
            ["삼성전자"],
            ["삼성대전자"],
            ["삼성전자"],
            rate_mode="standard",
        )

        self.assertAlmostEqual(normalized["entity_cer"]["micro"], 1 / 5)
        self.assertAlmostEqual(standard["entity_cer"]["micro"], 1 / 4)
        self.assertEqual(normalized["entity_cer"]["insertions"], 1)
        self.assertEqual(normalized["errors"][0]["type"], "misrecognition")
        self.assertEqual(normalized["errors"][0]["hypothesis"], "삼성대전자")

    def test_insertion_outside_entity_span_does_not_inflate_entity_cer(self):
        report = nt.evaluate_entities(
            ["삼성전자 실적 발표"],
            ["삼성전자 새 실적 발표"],
            ["삼성전자"],
        )

        self.assertEqual(report["summary"]["f1"], 1.0)
        self.assertEqual(report["entity_cer"]["micro"], 0.0)
        self.assertEqual(report["entity_cer"]["insertions"], 0)
        self.assertEqual(report["errors"], [])

    def test_repeated_mentions_count_an_omission_and_character_deletions(self):
        report = nt.evaluate_entities(
            ["삼성전자와 삼성전자"],
            ["삼성전자"],
            ["삼성전자"],
        )

        self.assertEqual(report["summary"]["true_positives"], 1)
        self.assertEqual(report["summary"]["false_negatives"], 1)
        self.assertEqual(report["summary"]["recall"], 0.5)
        self.assertEqual(report["entity_cer"]["deletions"], 4)
        self.assertEqual(report["errors"][0]["type"], "omission")

    def test_false_positive_mentions_are_reported_separately_from_entity_cer(self):
        report = nt.evaluate_entities(
            ["오늘 발표했다"],
            ["애플이 오늘 발표했다"],
            ["애플"],
        )

        self.assertEqual(report["summary"]["false_positives"], 1)
        self.assertEqual(report["summary"]["precision"], 0.0)
        self.assertEqual(report["entity_cer"]["reference_characters"], 0)
        self.assertEqual(report["entity_cer"]["micro"], 0.0)
        self.assertEqual(report["errors"][0]["type"], "addition")

    def test_unicode_normalization_remains_opt_in(self):
        reference = "가"
        hypothesis = unicodedata.normalize("NFD", reference)

        strict_report = nt.evaluate_entities(
            [reference],
            [hypothesis],
            [reference],
        )
        normalized_report = nt.evaluate_entities(
            [reference],
            [hypothesis],
            [reference],
            unicode_normalization="NFC",
        )

        self.assertEqual(strict_report["summary"]["false_negatives"], 1)
        self.assertGreater(strict_report["entity_cer"]["micro"], 0.0)
        self.assertEqual(normalized_report["summary"]["f1"], 1.0)
        self.assertEqual(normalized_report["entity_cer"]["micro"], 0.0)

    def test_generators_are_supported(self):
        references = (value for value in ["삼성전자", "애플"])
        hypotheses = (value for value in ["삼성전자", "애플"])

        report = nt.evaluate_entities(
            references,
            hypotheses,
            {"ORG": ["삼성전자", "애플"]},
        )

        self.assertEqual(report["summary"]["true_positives"], 2)
        self.assertEqual(report["summary"]["f1"], 1.0)

    def test_aliases_reject_unknown_ambiguous_and_duplicate_surfaces(self):
        with self.assertRaises(ValueError):
            nt.evaluate_entities(
                ["삼성전자"],
                ["삼성전자"],
                ["삼성전자"],
                aliases={"애플": ["애플사"]},
            )

        with self.assertRaises(ValueError):
            nt.evaluate_entities(
                ["삼성전자"],
                ["삼성전자"],
                ["삼성전자", "갤럭시"],
                aliases={"삼성전자": ["갤럭시"]},
            )

        with self.assertRaises(ValueError):
            nt.evaluate_entities(
                ["삼성전자"],
                ["삼성전자"],
                ["삼성전자"],
                aliases={"삼성전자": ["삼성 전자"]},
            )

    def test_invalid_alias_affix_and_entity_inputs_are_rejected(self):
        with self.assertRaises(TypeError):
            nt.evaluate_entities(
                ["삼성전자"],
                ["삼성전자"],
                ["삼성전자"],
                aliases={"삼성전자": [1]},
            )

        with self.assertRaises(TypeError):
            nt.evaluate_entities(
                ["삼성전자"],
                ["삼성전자"],
                ["삼성전자"],
                josa_list="의",
            )

        with self.assertRaises(ValueError):
            nt.evaluate_entities(
                ["..."],
                ["..."],
                ["..."],
            )

        with self.assertRaises(ValueError):
            nt.evaluate_entities(
                ["삼성전자"],
                [],
                ["삼성전자"],
            )


if __name__ == "__main__":
    unittest.main()
