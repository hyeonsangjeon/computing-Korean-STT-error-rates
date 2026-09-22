import json
import unittest

import nlptutti as nt


class TestComparisonPrivacy(unittest.TestCase):
    def report(self, **options):
        return nt.compare_systems(
            {"private-record-1": "김민수 01012345678 서울"},
            {
                "private-engine-a": {"private-record-1": "김민서 01012345679 서울"},
                "private-engine-b": {"private-record-1": "김민수 01012345678 서울"},
            },
            keywords={"private-keyword-label": ["김민수", "01012345678"]},
            entities={"private-entity-label": ["김민수", "01012345678"]},
            diagnostic_profile="korean-v1",
            **options,
        )

    def test_aggregate_removes_text_throughout_the_bundle(self):
        report = self.report(privacy_mode="aggregate")
        for rendered in (
            nt.render_comparison_json(report),
            nt.render_comparison_markdown(report),
        ):
            for text in (
                "김민수",
                "김민서",
                "01012345678",
                "01012345679",
                "private-record-1",
                "private-engine-a",
                "private-engine-b",
                "private-keyword-label",
                "private-entity-label",
            ):
                with self.subTest(text=text):
                    self.assertNotIn(text, rendered)
        self.assertNotIn("raw_inputs", report)
        self.assertEqual(
            [system["id"] for system in report["systems"]], ["system-1", "system-2"]
        )
        self.assertEqual(report["pairwise"][0]["baseline"], "system-1")
        self.assertEqual(report["pairwise"][0]["candidate"], "system-2")
        for system in report["systems"]:
            self.assertEqual(set(system["keywords"]), {"summary"})
            self.assertNotIn("errors", system["entities"])
            self.assertNotIn("entities", system["entities"])
            self.assertNotIn("labels", system["entities"])
            edits = system["diagnostics"]["top_character_edits"]
            self.assertTrue(edits["redacted"])
            self.assertTrue(
                all(
                    edits[key] == []
                    for key in ("substitutions", "deletions", "insertions")
                )
            )
        self.assertIn("[redacted]", nt.render_comparison_markdown(report))

    def test_aggregate_preserves_scores_fingerprints_and_repeatability(self):
        detailed = self.report()
        aggregate = self.report(privacy_mode="aggregate")
        self.assertEqual(aggregate, self.report(privacy_mode="aggregate"))
        self.assertEqual(detailed["dataset"], aggregate["dataset"])
        self.assertEqual(detailed["evaluation_config"], aggregate["evaluation_config"])
        for original, redacted in zip(detailed["systems"], aggregate["systems"]):
            self.assertEqual(original["metrics"], redacted["metrics"])
            self.assertEqual(original["provenance"], redacted["provenance"])
            for key in ("keywords", "entities"):
                self.assertEqual(original[key]["summary"], redacted[key]["summary"])
            self.assertEqual(
                original["entities"]["entity_cer"], redacted["entities"]["entity_cer"]
            )
        self.assertEqual(
            detailed["pairwise"][0]["metrics"], aggregate["pairwise"][0]["metrics"]
        )

    def test_legacy_details_are_preserved_but_warn_about_text(self):
        report = self.report()
        self.assertEqual(report["options"]["privacy_mode"], "detailed")
        self.assertTrue(report["systems"][0]["entities"]["errors"])
        self.assertIn("김민서", json.dumps(report, ensure_ascii=False))
        self.assertTrue(
            any(
                "include_transcripts=False" in warning for warning in report["warnings"]
            )
        )
        self.assertNotIn(
            "only fingerprints and aggregate", nt.render_comparison_markdown(report)
        )
        old_report = self.report()
        del old_report["options"]["privacy_mode"]
        self.assertIn("may contain text", nt.render_comparison_markdown(old_report))

    def test_modes_are_explicit_and_conflicting_options_fail(self):
        for mode in (None, True, "unknown", []):
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                self.report(privacy_mode=mode)
        with self.assertRaisesRegex(ValueError, "cannot include transcripts"):
            self.report(privacy_mode="aggregate", include_transcripts=True)
        raw = self.report(privacy_mode="detailed", include_transcripts=True)
        self.assertEqual(raw["raw_inputs"]["ids"], ["private-record-1"])
