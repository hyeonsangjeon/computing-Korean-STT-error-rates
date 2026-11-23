import json
import unittest
from pathlib import Path

import nlptutti as nt


FIXTURE = Path(__file__).parent / "fixtures" / "diagnostics" / "korean_profile.json"


class TestKoreanDiagnosticProfile(unittest.TestCase):
    def test_profile_reports_korean_breakdowns_without_changing_metrics(self):
        document = json.loads(FIXTURE.read_text(encoding="utf-8"))
        plain = nt.compare_systems(document["references"], document["systems"])
        report = nt.compare_systems(
            document["references"],
            document["systems"],
            diagnostic_profile="korean-v1",
        )
        baseline = report["systems"][0]
        diagnostics = baseline["diagnostics"]

        self.assertEqual(report["options"]["diagnostic_profile"], "korean-v1")
        self.assertEqual(baseline["metrics"], plain["systems"][0]["metrics"])
        self.assertEqual(diagnostics["schema"], "nlptutti.diagnostics/1.0")
        self.assertEqual(diagnostics["spacing_boundary"]["missing_boundaries"], 1)
        self.assertEqual(diagnostics["number_unit"]["missing_mentions"], 1)
        self.assertEqual(diagnostics["number_unit"]["unexpected_mentions"], 1)
        self.assertEqual(diagnostics["josa_eomi_adjacent"]["substitutions"], 2)
        self.assertTrue(diagnostics["top_character_edits"]["substitutions"])
        self.assertTrue(report["warnings"])

    def test_profile_is_deterministic_and_rules_are_versioned(self):
        document = json.loads(FIXTURE.read_text(encoding="utf-8"))
        first = nt.compare_systems(
            document["references"],
            document["systems"],
            diagnostic_profile="korean-v1",
        )
        second = nt.compare_systems(
            document["references"],
            document["systems"],
            diagnostic_profile="korean-v1",
        )

        self.assertEqual(
            nt.render_comparison_json(first), nt.render_comparison_json(second)
        )
        rules = first["systems"][0]["diagnostics"]["rules"]
        self.assertTrue(all(rule["name"] and rule["version"] for rule in rules))
        self.assertEqual(
            [rule["status"] for rule in rules],
            ["stable", "experimental", "experimental", "stable"],
        )

    def test_false_positive_boundaries_are_skipped(self):
        report = nt.compare_systems(
            ["abc3kgx", "바다는 맑다", "가 나"],
            {
                "a": ["abc4kgx", "하늘은 맑다", "다 라"],
                "b": ["abc3kgx", "바다는 맑다", "가 나"],
            },
            diagnostic_profile="korean-v1",
        )
        diagnostics = report["systems"][0]["diagnostics"]

        self.assertEqual(diagnostics["number_unit"]["reference_mentions"], 0)
        self.assertEqual(diagnostics["josa_eomi_adjacent"]["substitutions"], 0)
        self.assertEqual(diagnostics["spacing_boundary"]["eligible_items"], 0)
        self.assertEqual(diagnostics["spacing_boundary"]["skipped_lexical_items"], 3)

    def test_keyword_and_entity_summaries_are_linked(self):
        report = nt.compare_systems(
            ["삼성전자가 3대를 출시했다"],
            {
                "a": ["삼성이 4대를 출시했다"],
                "b": ["삼성전자가 3대를 출시했다"],
            },
            keywords=["삼성전자"],
            entities={"ORG": ["삼성전자"]},
            diagnostic_profile="korean-v1",
        )
        breakdowns = report["systems"][0]["diagnostics"]["metric_breakdowns"]

        self.assertEqual(breakdowns["keywords"]["recall"], 0)
        self.assertEqual(breakdowns["entities"]["f1"], 0)
        markdown = nt.render_comparison_markdown(report)
        self.assertIn("Korean diagnostics", markdown)
        self.assertIn("not morphological analysis", markdown)

    def test_profile_is_opt_in_and_unknown_versions_fail(self):
        report = nt.compare_systems(["가"], {"a": ["나"], "b": ["가"]})
        self.assertIsNone(report["options"]["diagnostic_profile"])
        self.assertNotIn("diagnostics", report["systems"][0])
        with self.assertRaisesRegex(ValueError, "diagnostic_profile"):
            nt.compare_systems(
                ["가"],
                {"a": ["나"], "b": ["가"]},
                diagnostic_profile="korean-v2",
            )

    def test_surface_amounts_times_and_unknown_coverage(self):
        refs = ["3.5만 원을", "3,500원", "오전 9시 30분", "2시간", "삼만 원",
                "오후 25시", "12,34원", "v1.2.3kg", "3만원과 101호", "서울은", "1개"]
        hyps = ["35만 원을", "3500원", "오후 9시30분", "2 시간", "3만 원",
                "오후 25시", "12,34원", "v1.2.3kg", "3만 원과 101호", "서울이", ""]
        report = nt.compare_systems(refs, {"a": hyps, "b": refs}, diagnostic_profile="korean-v1")
        units = report["systems"][0]["diagnostics"]["number_unit"]
        self.assertEqual(units["matched_mentions"], 3)
        self.assertEqual(units["missing_mentions"], 3)
        self.assertEqual(units["unexpected_mentions"], 3)
        self.assertEqual(units["coverage"], {
            "items": 11, "both_detected_items": 5, "neither_detected_items": 4,
            "hypothesis_only_items": 1, "reference_only_items": 1, "unknown_items": 7
        })
        self.assertIn("5 / 7 / 11", nt.render_comparison_markdown(report))

    def test_diagnostic_does_not_convert_units_or_infer_names(self):
        report = nt.compare_systems(
            ["3.5만 원", "오후 두 시 반", "이서준"],
            {"a": ["35,000원", "14:30", "이서진"], "b": ["3.5만원", "오후 두 시 반", "이서준"]},
            diagnostic_profile="korean-v1",
        )
        first, second = report["systems"]
        units = first["diagnostics"]["number_unit"]
        self.assertEqual((units["matched_mentions"], units["coverage"]["unknown_items"]), (0, 2))
        self.assertEqual(second["diagnostics"]["number_unit"]["matched_mentions"], 1)
        self.assertNotIn("entities", first)


if __name__ == "__main__":
    unittest.main()
