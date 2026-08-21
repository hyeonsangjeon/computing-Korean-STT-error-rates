import json
import unittest

import nlptutti as nt


class TestCompareSystems(unittest.TestCase):
    def test_compares_two_systems_with_micro_macro_and_deltas(self):
        report = nt.compare_systems(
            ["오늘 날씨가 맑습니다", "서울은 따뜻합니다"],
            {
                "baseline": ["오늘 날씨는 맑습니다", "서울은 춥습니다"],
                "candidate": ["오늘 날씨가 맑습니다", "서울은 따뜻합니다"],
            },
            rate_mode="standard",
        )

        self.assertEqual(report["schema"], nt.COMPARISON_SCHEMA)
        self.assertEqual(report["dataset"]["item_count"], 2)
        self.assertEqual([item["id"] for item in report["systems"]], ["baseline", "candidate"])
        self.assertGreater(report["systems"][0]["metrics"]["cer"]["micro"], 0)
        self.assertEqual(report["systems"][1]["metrics"]["cer"]["micro"], 0)
        self.assertLess(report["pairwise"][0]["metrics"]["cer"]["micro"], 0)
        self.assertEqual(report["systems"][1]["metrics"]["crr"]["micro"], 1.0)

    def test_mapping_inputs_are_aligned_by_id_not_mapping_order(self):
        report = nt.compare_systems(
            {"utt-2": "나", "utt-1": "가"},
            {
                "a": {"utt-1": "다", "utt-2": "나"},
                "b": {"utt-2": "나", "utt-1": "가"},
            },
        )

        self.assertGreater(report["systems"][0]["metrics"]["cer"]["micro"], 0)
        self.assertEqual(report["systems"][1]["metrics"]["cer"]["micro"], 0)

    def test_mismatched_ids_and_lengths_fail_closed(self):
        invalid_cases = [
            (
                {"one": "가"},
                {"a": {"one": "가"}, "b": {"two": "가"}},
            ),
            (
                ["가", "나"],
                {"a": ["가", "나"], "b": ["가"]},
            ),
        ]

        for references, systems in invalid_cases:
            with self.subTest(references=references), self.assertRaises(ValueError):
                nt.compare_systems(references, systems)

    def test_at_least_two_systems_are_required(self):
        with self.assertRaises(ValueError):
            nt.compare_systems(["가"], {"only": ["가"]})

    def test_raw_text_is_excluded_by_default_and_opt_in_is_explicit(self):
        reference = "민감한 기준 문장"
        hypothesis = "민감한 가설 문장"
        default = nt.compare_systems(
            [reference],
            {"a": [hypothesis], "b": [reference]},
        )
        included = nt.compare_systems(
            [reference],
            {"a": [hypothesis], "b": [reference]},
            include_transcripts=True,
        )

        self.assertNotIn(reference, json.dumps(default, ensure_ascii=False))
        self.assertNotIn(hypothesis, json.dumps(default, ensure_ascii=False))
        self.assertEqual(included["raw_inputs"]["references"], [reference])
        self.assertTrue(included["warnings"])

    def test_keyword_and_entity_metrics_reuse_existing_public_results(self):
        report = nt.compare_systems(
            ["삼성전자가 발표했다"],
            {"a": ["삼성이 발표했다"], "b": ["삼성전자가 발표했다"]},
            keywords=["삼성전자"],
            entities={"ORG": ["삼성전자"]},
        )

        self.assertEqual(report["systems"][0]["keywords"]["summary"]["recall"], 0)
        self.assertEqual(report["systems"][1]["entities"]["summary"]["f1"], 1)


if __name__ == "__main__":
    unittest.main()
