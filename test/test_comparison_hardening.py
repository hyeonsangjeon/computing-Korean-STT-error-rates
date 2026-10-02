import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import nlptutti as nt
from nlptutti import asr_metrics
from nlptutti.report_validation import validate_comparison_report


class TestSentenceErrorMeaning(unittest.TestCase):
    def test_character_and_word_sentence_errors(self):
        report = nt.evaluate_corpus(
            ["가 나", "안녕!", "", ""], ["가나", "안녕", "", "가"]
        )
        self.assertEqual(report["sentence_error_unit"], "character")
        self.assertEqual(report["perfect_sentences"], 3)
        self.assertEqual(report["sentence_error_rate"], 0.25)
        self.assertEqual(report["word_perfect_sentences"], 2)
        self.assertEqual(report["word_sentence_error_rate"], 0.5)
        kept = nt.evaluate_corpus(["안녕!"], ["안녕"], rm_punctuation=False)
        self.assertEqual(kept["sentence_error_rate"], 1)
        self.assertEqual(kept["word_sentence_error_rate"], 1)


class TestSingleMeasurement(unittest.TestCase):
    def test_two_measurements_per_pair_even_with_bootstrap(self):
        for resamples in (0, 50):
            with self.subTest(resamples=resamples), patch.object(
                asr_metrics, "levenshtein", wraps=asr_metrics.levenshtein
            ) as measure:
                nt.compare_systems(
                    ["가 나", "다"],
                    {"a": ["가나", "라"], "b": ["가 나", "다"]},
                    bootstrap=resamples,
                )
                self.assertEqual(measure.call_count, 8)

    def test_metrics_match_historical_public_functions(self):
        references = ["", "", "가 나!", "서울", "가나", "abc"]
        hypotheses = ["", "가 나", "가나", "서울", "나가", "xyzabc"]
        for mode in ("normalized", "standard"):
            for normalization in (None, "NFC", "NFD"):
                for punctuation in (True, False):
                    with self.subTest(
                        mode=mode, norm=normalization, punctuation=punctuation
                    ):
                        options = dict(
                            rate_mode=mode,
                            unicode_normalization=normalization,
                            rm_punctuation=punctuation,
                        )
                        actual = nt.compare_systems(
                            references, {"a": hypotheses, "b": references}, **options
                        )["systems"][0]["metrics"]
                        expected = nt.evaluate_corpus(references, hypotheses, **options)
                        for metric in ("cer", "wer"):
                            self.assertEqual(actual[metric], expected[metric])
                        values = [
                            nt.get_crr(r, h, **options)["crr"]
                            for r, h in zip(references, hypotheses)
                        ]
                        self.assertEqual(
                            actual["crr"],
                            {
                                "micro": round(1 - expected["cer"]["micro"], 2),
                                "macro": sum(values) / len(values),
                            },
                        )


class TestRuntimeReportValidation(unittest.TestCase):
    def report(self):
        return nt.compare_systems(
            ["가", "나"], {"a": ["다", "나"], "b": ["가", "나"]}, bootstrap=20
        )

    def assert_invalid(self, report, path):
        messages = []
        for renderer in (nt.render_comparison_json, nt.render_comparison_markdown):
            with self.assertRaises(ValueError) as caught:
                renderer(report)
            messages.append(str(caught.exception))
        self.assertEqual(messages[0], messages[1])
        self.assertIn(path, messages[0])

    def test_missing_top_level_fields(self):
        for key in self.report():
            with self.subTest(key=key):
                report = self.report()
                del report[key]
                self.assert_invalid(report, "report." + key)

    def test_bad_nested_fields(self):
        for path, value in (
            (("options", "rate_mode"), "percent"),
            (("options", "rm_punctuation"), 1),
            (("options", "confidence"), True),
            (("options", "bootstrap_resamples"), -1),
            (("options", "unicode_normalization"), "nfc"),
            (("dataset", "item_count"), 0),
            (("dataset", "ids_sha256"), "bad"),
            (("systems", 0, "metrics", "cer", "micro"), float("nan")),
            (("systems", 0, "metrics", "cer", "hits"), True),
            (("systems", 0, "provenance", "item_count"), 3),
            (("systems", 1, "id"), "a"),
            (("pairwise", 0, "candidate"), "missing"),
            (("pairwise", 0, "metrics", "cer", "confidence_interval", "lower"), 50),
            (("pairwise", 0, "metrics", "wer", "confidence_interval", "seed"), 41),
            (("warnings",), [None]),
            (("evaluator", "version"), ""),
            (("schema",), "nlptutti.comparison/2.0"),
        ):
            with self.subTest(path=path):
                report = self.report()
                parent = report
                for key in path[:-1]:
                    parent = parent[key]
                parent[path[-1]] = value
                self.assert_invalid(report, "report." + str(path[0]))

    def test_roundtrip_minor_version_and_extra_fields(self):
        report = self.report()
        report["schema"] = "nlptutti.comparison/1.9"
        report["future_extension"] = {"values": [None, True, 2, "가"]}
        decoded = json.loads(nt.render_comparison_json(report))
        validate_comparison_report(decoded)
        self.assertEqual(
            nt.render_comparison_markdown(report),
            nt.render_comparison_markdown(decoded),
        )
        for value in (float("inf"), object(), {1: "bad"}):
            report["future_extension"] = value
            self.assert_invalid(report, "report.future_extension")

    def test_circular_data_rejected(self):
        report = self.report()
        report["cycle"] = report
        self.assert_invalid(report, "report.cycle")

    def test_optional_sections_validated(self):
        report = nt.compare_systems(
            ["서울"],
            {"a": ["서을"], "b": ["서울"]},
            keywords=["서울"],
            entities=["서울"],
            diagnostic_profile="korean-v1",
            include_transcripts=True,
        )
        validate_comparison_report(report)
        for path in (
            ("keywords", "summary", "recall"),
            ("entities", "entity_cer", "micro"),
            ("diagnostics", "number_unit", "missing_mentions"),
        ):
            broken = copy.deepcopy(report)
            del broken["systems"][0][path[0]][path[1]][path[2]]
            self.assert_invalid(broken, ".".join(path))
        report["raw_inputs"]["ids"] = ["", "extra"]
        self.assert_invalid(report, "report.raw_inputs.ids")

    def test_render_failure_preserves_both_existing_files(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = nt.write_comparison_bundle(self.report(), directory)
            before = {name: path.read_bytes() for name, path in paths.items()}
            with patch(
                "nlptutti.reporting.render_comparison_markdown",
                side_effect=ValueError("bad markdown"),
            ):
                with self.assertRaises(ValueError):
                    nt.write_comparison_bundle(self.report(), directory)
            self.assertEqual(
                before, {name: path.read_bytes() for name, path in paths.items()}
            )
            self.assertFalse(list(Path(directory).glob("*.tmp")))
