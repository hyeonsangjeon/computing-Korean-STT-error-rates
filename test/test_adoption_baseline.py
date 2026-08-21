import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "docs" / "adoption" / "2026-08-21-baseline.json"


class TestAdoptionBaseline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))

    def test_snapshot_summaries_match_daily_raw_counts(self):
        github = self.snapshot["github"]
        pypistats = self.snapshot["pypistats"]

        self.assertEqual(len(github["views_daily"]), 14)
        self.assertEqual(len(github["clones_daily"]), 14)
        self.assertEqual(
            sum(day["count"] for day in github["views_daily"]),
            github["traffic_window"]["views"],
        )
        self.assertEqual(
            sum(day["count"] for day in github["clones_daily"]),
            github["traffic_window"]["clones"],
        )
        self.assertEqual(len(pypistats["daily_30_days"]), 30)
        self.assertEqual(
            sum(day["downloads"] for day in pypistats["daily_30_days"]),
            pypistats["last_30_days"],
        )
        self.assertEqual(
            sum(day["downloads"] for day in pypistats["daily_30_days"][-7:]),
            pypistats["last_7_days"],
        )
        self.assertEqual(
            sum(day["downloads"] for day in pypistats["daily_30_days"][-14:]),
            pypistats["last_14_days"],
        )
        self.assertEqual(
            sum(day["downloads"] for day in pypistats["daily_30_days"][:5]),
            pypistats["spike_2026_07_22_through_26"],
        )
        self.assertEqual(
            pypistats["daily_30_days"][-1]["downloads"],
            pypistats["last_day"],
        )

    def test_release_context_is_pre_release_and_windows_are_separate(self):
        self.assertEqual(
            self.snapshot["release_context"]["published_version"], "0.0.0.19"
        )
        self.assertEqual(
            self.snapshot["release_context"]["release_candidate"], "0.0.0.20"
        )
        self.assertFalse(self.snapshot["release_context"]["candidate_published"])
        self.assertEqual(
            self.snapshot["github"]["traffic_window"]["start"],
            "2026-08-07T00:00:00Z",
        )
        self.assertEqual(
            self.snapshot["pypistats"]["daily_30_days"][0]["date"],
            "2026-07-22",
        )

    def test_public_code_search_baseline_is_explicit(self):
        queries = self.snapshot["public_code_search"]["queries"]

        self.assertEqual(queries["distinct_repositories_outside_owner"], 28)
        self.assertEqual(
            len(self.snapshot["public_code_search"]["repositories_outside_owner"]),
            28,
        )
        self.assertEqual(queries["nlptutti_and_compare_systems_files"], 0)
        self.assertEqual(queries["nlptutti_compare_cli_files"], 0)

    def test_review_dates_and_no_telemetry_policy_are_documented(self):
        baseline = (ROOT / "docs" / "adoption-baseline.md").read_text(encoding="utf-8")
        template = (ROOT / "docs" / "adoption-review-template.md").read_text(
            encoding="utf-8"
        )

        for date in ("2026-09-20", "2026-10-20", "2026-11-19"):
            self.assertIn(date, baseline)
        self.assertIn("telemetry를 추가하지 않습니다", baseline)
        self.assertIn("인과를 단정하지 않습니다", template)


if __name__ == "__main__":
    unittest.main()
