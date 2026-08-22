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
        self.assertEqual(
            [item["id"] for item in report["systems"]], ["baseline", "candidate"]
        )
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

    def test_id_mapping_order_does_not_change_bootstrap_or_fingerprints(self):
        first = nt.compare_systems(
            {"utt-1": "가나다", "utt-2": "라마바", "utt-3": "사아자"},
            {
                "baseline": {"utt-1": "가다", "utt-2": "라바", "utt-3": "사자"},
                "candidate": {"utt-1": "가나다", "utt-2": "라마", "utt-3": "아자"},
            },
            rate_mode="standard",
            bootstrap=200,
            seed=42,
            include_transcripts=True,
        )
        reordered = nt.compare_systems(
            {"utt-3": "사아자", "utt-1": "가나다", "utt-2": "라마바"},
            {
                "baseline": {"utt-2": "라바", "utt-3": "사자", "utt-1": "가다"},
                "candidate": {"utt-3": "아자", "utt-1": "가나다", "utt-2": "라마"},
            },
            rate_mode="standard",
            bootstrap=200,
            seed=42,
            include_transcripts=True,
        )

        self.assertEqual(first, reordered)
        self.assertEqual(first["raw_inputs"]["ids"], ["utt-1", "utt-2", "utt-3"])

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

    def test_evaluation_config_fingerprint_tracks_optional_scoring_inputs(self):
        first = nt.compare_systems(
            ["삼성전자가 갤럭시를 발표했다"],
            {
                "a": ["삼성이 갤럭시를 발표했다"],
                "b": ["삼성전자가 갤럭시를 발표했다"],
            },
            keywords={"PRODUCT": ["갤럭시"], "ORG": ["삼성전자"]},
            entities={"ORG": ["삼성전자"]},
            entity_aliases={"삼성전자": ["삼성"]},
        )
        reordered = nt.compare_systems(
            ["삼성전자가 갤럭시를 발표했다"],
            {
                "a": ["삼성이 갤럭시를 발표했다"],
                "b": ["삼성전자가 갤럭시를 발표했다"],
            },
            keywords={"ORG": ["삼성전자"], "PRODUCT": ["갤럭시"]},
            entities={"ORG": ["삼성전자"]},
            entity_aliases={"삼성전자": ["삼성"]},
        )
        changed_aliases = nt.compare_systems(
            ["삼성전자가 갤럭시를 발표했다"],
            {
                "a": ["삼성이 갤럭시를 발표했다"],
                "b": ["삼성전자가 갤럭시를 발표했다"],
            },
            keywords={"ORG": ["삼성전자"], "PRODUCT": ["갤럭시"]},
            entities={"ORG": ["삼성전자"]},
            entity_aliases={"삼성전자": ["삼전"]},
        )

        self.assertEqual(first["evaluation_config"], reordered["evaluation_config"])
        self.assertNotEqual(
            first["evaluation_config"]["sha256"],
            changed_aliases["evaluation_config"]["sha256"],
        )
        self.assertEqual(len(first["evaluation_config"]["sha256"]), 64)
        self.assertEqual(
            nt.compare_systems(["가"], {"a": ["가"], "b": ["가"]})["evaluation_config"],
            {
                "keywords": False,
                "entities": False,
                "entity_aliases": False,
                "sha256": None,
            },
        )

        with self.assertRaisesRegex(ValueError, "entity_aliases requires entities"):
            nt.compare_systems(
                ["가"],
                {"a": ["가"], "b": ["가"]},
                entity_aliases={"가": ["나"]},
            )


if __name__ == "__main__":
    unittest.main()
