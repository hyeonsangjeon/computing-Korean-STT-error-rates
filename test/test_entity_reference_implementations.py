import json
import unittest
from pathlib import Path

import nlptutti as nt


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "entity_reference_implementations.json"


class TestEntityReferenceImplementations(unittest.TestCase):
    """Compare shared contracts with outputs captured from pinned upstream code."""

    @classmethod
    def setUpClass(cls):
        with FIXTURE_PATH.open(encoding="utf-8") as fixture_file:
            cls.fixture = json.load(fixture_file)

    def _case(self, implementation, name):
        return self.fixture["implementations"][implementation]["fixtures"][name]

    def _evaluate(self, case):
        return nt.evaluate_entities(
            [case["reference"]],
            [case["hypothesis"]],
            [case["entity"]],
            josa_list=[],
            eomi_list=[],
            rate_mode="standard",
        )

    def _assert_nlptutti_result(self, report, expected):
        entity_cer = report["entity_cer"]
        self.assertAlmostEqual(entity_cer["micro"], expected["micro"])
        for name in (
            "hits",
            "substitutions",
            "deletions",
            "insertions",
            "reference_characters",
        ):
            self.assertEqual(entity_cer[name], expected[name])
        self.assertAlmostEqual(report["summary"]["f1"], expected["f1"])

    def test_pier_entity_substitution_has_the_same_selected_span_counts(self):
        case = self._case("pier", "entity_substitution")
        report = self._evaluate(case)
        upstream = case["upstream"]

        self._assert_nlptutti_result(report, case["nlptutti"])
        self.assertAlmostEqual(
            report["entity_cer"]["micro"] * 100,
            upstream["pier_percent"],
        )
        for name in ("hits", "substitutions", "deletions", "insertions"):
            self.assertEqual(report["entity_cer"][name], upstream[name])

    def test_pier_and_nlptutti_exclude_an_insertion_after_the_entity(self):
        case = self._case("pier", "insertion_outside_entity")
        report = self._evaluate(case)
        upstream = case["upstream"]

        self._assert_nlptutti_result(report, case["nlptutti"])
        self.assertEqual(upstream["rest_insertions"], 1)
        self.assertAlmostEqual(
            report["entity_cer"]["micro"] * 100,
            upstream["pier_percent"],
        )

    def test_contextasr_exact_entity_contract_matches_nlptutti(self):
        case = self._case("contextasr_bench", "exact_entity_with_outside_insertion")
        report = self._evaluate(case)
        upstream = case["upstream"]

        self._assert_nlptutti_result(report, case["nlptutti"])
        self.assertAlmostEqual(report["entity_cer"]["micro"], upstream["ne_wer"])
        self.assertAlmostEqual(1 - report["summary"]["recall"], upstream["ne_fnr"])

    def test_contextasr_word_rate_and_nlptutti_character_rate_stay_distinct(self):
        case = self._case("contextasr_bench", "fuzzy_entity_misrecognition")
        report = self._evaluate(case)
        upstream = case["upstream"]

        self._assert_nlptutti_result(report, case["nlptutti"])
        self.assertAlmostEqual(upstream["ne_wer"], 1 / upstream["reference_words"])
        self.assertAlmostEqual(1 - report["summary"]["recall"], upstream["ne_fnr"])
        self.assertNotAlmostEqual(report["entity_cer"]["micro"], upstream["ne_wer"])


if __name__ == "__main__":
    unittest.main()
