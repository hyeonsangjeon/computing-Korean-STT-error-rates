import copy
import unittest
from unittest.mock import patch

import nlptutti as nt
from nlptutti import asr_metrics


class TestComparisonDetails(unittest.TestCase):
    references = {"number": "12개", "spacing": "가 나", "entity": "김민수"}
    systems = {
        "baseline": {"number": "13개", "spacing": "가 나", "entity": "김민수"},
        "candidate": {"number": "12개", "spacing": "가나", "entity": "김민서"},
    }
    labels = {
        "number": {"domain": "숫자"},
        "spacing": {"domain": "일반"},
        "entity": {"domain": "일반"},
    }

    def report(self, **kwargs):
        return nt.compare_systems(
            self.references, self.systems, rate_mode="standard", **kwargs
        )

    def test_opt_in_and_aggregate_privacy(self):
        default = self.report()
        self.assertNotIn("details", default)
        self.assertNotIn("slices", default)
        for options in ({"include_items": True}, {"labels": self.labels}):
            with self.assertRaisesRegex(ValueError, "aggregate"):
                self.report(privacy_mode="aggregate", **options)

    def test_item_counts_sum_to_micro_without_new_alignments(self):
        with patch.object(
            asr_metrics, "levenshtein", wraps=asr_metrics.levenshtein
        ) as measure:
            report = self.report(include_items=True, labels=self.labels)
            self.assertEqual(measure.call_count, 12)
        nt.validate_comparison_report(report)
        for detail, summary in zip(report["details"]["systems"], report["systems"]):
            for metric in ("cer", "wer"):
                for key in ("hits", "substitutions", "deletions", "insertions"):
                    self.assertEqual(
                        sum(item["metrics"][metric][key] for item in detail["items"]),
                        summary["metrics"][metric][key],
                    )
        pair = report["details"]["pairwise"][0]
        self.assertEqual(pair["top_regressions"]["cer"], ["entity"])
        self.assertEqual(pair["top_improvements"]["cer"], ["number"])
        self.assertEqual(pair["top_regressions"]["wer"], ["entity", "spacing"])
        by_id = {row["id"]: row["deltas"] for row in pair["items"]}
        self.assertEqual(by_id["spacing"]["cer"], 0)
        self.assertEqual(by_id["spacing"]["wer"], 1)

    def test_slice_counts_and_scores(self):
        report = self.report(labels=self.labels)
        self.assertEqual(sum(slice_["item_count"] for slice_ in report["slices"]), 3)
        for slice_ in report["slices"]:
            ids = [
                key
                for key in self.references
                if self.labels[key]["domain"] == slice_["value"]
            ]
            expected = nt.compare_systems(
                {key: self.references[key] for key in ids},
                {
                    name: {key: values[key] for key in ids}
                    for name, values in self.systems.items()
                },
                rate_mode="standard",
            )
            self.assertEqual(slice_["pairwise"], expected["pairwise"])
            for actual, reference in zip(slice_["systems"], expected["systems"]):
                self.assertEqual(actual["metrics"], reference["metrics"])
        markdown = nt.render_comparison_markdown(report)
        self.assertIn("Small slices", markdown)
        self.assertIn("| domain | 숫자 | 1 |", markdown)

    def test_id_order_and_ties_are_deterministic(self):
        first = self.report(include_items=True, labels=self.labels)
        second = nt.compare_systems(
            dict(reversed(list(self.references.items()))),
            {k: dict(reversed(list(v.items()))) for k, v in self.systems.items()},
            rate_mode="standard",
            include_items=True,
            labels=dict(reversed(list(self.labels.items()))),
        )
        self.assertEqual(first, second)
        report = nt.compare_systems(
            {"z": "가", "a": "가"},
            {"x": {"z": "가", "a": "가"}, "y": {"z": "나", "a": "나"}},
            include_items=True,
            top_n=1,
        )
        self.assertEqual(
            report["details"]["pairwise"][0]["top_regressions"]["cer"], ["a"]
        )

    def test_invalid_labels_and_parameters(self):
        for labels in (
            {},
            {"number": {}},
            {k: {"domain": 1} for k in self.references},
            {k: ({"a": "x"} if k == "number" else {"b": "x"}) for k in self.references},
        ):
            with self.assertRaises(ValueError):
                self.report(labels=labels)
        for top_n in (0, -1, True, 1.5):
            with self.assertRaises(ValueError):
                self.report(top_n=top_n)

    def test_extensions_validated_before_both_renderers(self):
        report = self.report(include_items=True, labels=self.labels)
        mutations = [
            lambda r: r["details"]["systems"][0]["items"][0].pop("metrics"),
            lambda r: r["details"]["pairwise"][0]["top_regressions"]["cer"].append(
                "missing"
            ),
            lambda r: r["slices"][0].update(item_count=100),
            lambda r: r["slices"][0]["systems"][0].update(id="bad"),
        ]
        for mutate in mutations:
            broken = copy.deepcopy(report)
            mutate(broken)
            for renderer in (nt.render_comparison_json, nt.render_comparison_markdown):
                with self.assertRaises(ValueError):
                    renderer(broken)
