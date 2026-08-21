import json
import unittest

import nlptutti as nt


class TestPairedBootstrap(unittest.TestCase):
    def test_same_seed_produces_identical_intervals(self):
        arguments = (
            ["가", "나", "다"],
            {
                "baseline": ["라", "나", "다"],
                "candidate": ["가", "마", "다"],
            },
        )

        first = nt.compare_systems(
            *arguments, rate_mode="standard", bootstrap=200, seed=7
        )
        second = nt.compare_systems(
            *arguments, rate_mode="standard", bootstrap=200, seed=7
        )

        self.assertEqual(
            json.dumps(first, sort_keys=True),
            json.dumps(second, sort_keys=True),
        )
        interval = first["pairwise"][0]["metrics"]["cer"]["confidence_interval"]
        self.assertEqual(interval["method"], "paired_percentile_bootstrap")
        self.assertEqual(interval["sampling_unit"], "utterance")
        self.assertEqual(interval["resamples"], 200)

    def test_hand_calculated_two_item_interval_covers_both_extremes(self):
        report = nt.compare_systems(
            ["가", "나"],
            {
                "baseline": ["다", "나"],
                "candidate": ["가", "라"],
            },
            rate_mode="standard",
            bootstrap=1000,
            seed=42,
            confidence=0.95,
        )

        delta = report["pairwise"][0]["metrics"]["cer"]
        interval = delta["confidence_interval"]
        self.assertEqual(delta["micro"], 0.0)
        self.assertEqual(interval["lower"], -1.0)
        self.assertEqual(interval["upper"], 1.0)

    def test_bootstrap_zero_keeps_only_point_estimates(self):
        report = nt.compare_systems(
            ["가"],
            {"baseline": ["나"], "candidate": ["가"]},
            bootstrap=0,
        )

        self.assertNotIn(
            "confidence_interval",
            report["pairwise"][0]["metrics"]["cer"],
        )

    def test_bootstrap_rejects_too_small_or_invalid_samples(self):
        with self.assertRaises(ValueError):
            nt.compare_systems(
                ["가"],
                {"baseline": ["나"], "candidate": ["가"]},
                bootstrap=100,
            )
        with self.assertRaises(ValueError):
            nt.compare_systems(
                ["가", "나"],
                {"baseline": ["나", "나"], "candidate": ["가", "나"]},
                bootstrap=-1,
            )
        with self.assertRaises(ValueError):
            nt.compare_systems(
                ["가", "나"],
                {"baseline": ["나", "나"], "candidate": ["가", "나"]},
                bootstrap=100,
                confidence=1,
            )


if __name__ == "__main__":
    unittest.main()
