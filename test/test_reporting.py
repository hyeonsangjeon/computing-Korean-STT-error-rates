import json
import tempfile
import unittest
from pathlib import Path

import nlptutti as nt

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "comparison"


def fixed_report():
    report = nt.compare_systems(
        ["가", "나"],
        {"baseline": ["다", "나"], "candidate": ["가", "나"]},
        rate_mode="standard",
    )
    report["evaluator"]["version"] = "test-version"
    return report


class TestComparisonReporting(unittest.TestCase):
    def test_json_and_markdown_are_deterministic(self):
        report = fixed_report()

        first_json = nt.render_comparison_json(report)
        second_json = nt.render_comparison_json(report)
        first_markdown = nt.render_comparison_markdown(report)
        second_markdown = nt.render_comparison_markdown(report)

        self.assertEqual(first_json, second_json)
        self.assertEqual(first_markdown, second_markdown)
        self.assertEqual(json.loads(first_json), report)
        self.assertIn("| baseline | 0.500000 |", first_markdown)
        self.assertIn("| candidate | 0.000000 |", first_markdown)
        self.assertIn("| baseline | candidate | CER | -0.500000 |", first_markdown)

    def test_markdown_matches_golden_fixture(self):
        expected = (FIXTURE_DIR / "golden_report.md").read_text(encoding="utf-8")

        self.assertEqual(nt.render_comparison_markdown(fixed_report()), expected)

    def test_default_renderers_do_not_leak_raw_transcripts(self):
        report = nt.compare_systems(
            ["공개하면 안 되는 기준"],
            {"a": ["공개하면 안 되는 결과"], "b": ["다른 결과"]},
        )

        json_report = nt.render_comparison_json(report)
        markdown_report = nt.render_comparison_markdown(report)

        self.assertNotIn("공개하면 안 되는 기준", json_report)
        self.assertNotIn("공개하면 안 되는 결과", json_report)
        self.assertNotIn("공개하면 안 되는 기준", markdown_report)
        self.assertIn("Raw transcripts are excluded", markdown_report)

    def test_bundle_contains_two_views_of_the_same_report(self):
        report = fixed_report()
        with tempfile.TemporaryDirectory() as directory:
            paths = nt.write_comparison_bundle(report, directory)
            json_report = json.loads(paths["json"].read_text(encoding="utf-8"))
            markdown_report = paths["markdown"].read_text(encoding="utf-8")

        self.assertEqual(json_report["systems"], report["systems"])
        self.assertIn("test-version", markdown_report)
        self.assertTrue(markdown_report.endswith("\n"))

    def test_unknown_schema_is_rejected(self):
        report = fixed_report()
        report["schema"] = "unknown/1.0"

        with self.assertRaises(ValueError):
            nt.render_comparison_json(report)


if __name__ == "__main__":
    unittest.main()
