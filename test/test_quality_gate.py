import contextlib
import copy
import io
import json
import tempfile
import re
import shlex
import os
import unittest
from pathlib import Path

import nlptutti as nt
from nlptutti.cli import main

ROOT = Path(__file__).resolve().parents[1]


class TestQualityGate(unittest.TestCase):
    def policy(self):
        return json.loads(
            (ROOT / "examples/gate_policy.json").read_text(encoding="utf-8")
        )

    def report(self, candidate="가"):
        return nt.compare_systems(
            ["가", "나"],
            {"baseline": ["가", "나"], "candidate": [candidate, "나"]},
            rate_mode="standard",
        )

    def test_pass_fail_and_explicit_allowance(self):
        policy = self.policy()
        decision = nt.evaluate_quality_gate(self.report(), policy)
        self.assertTrue(decision["passed"])
        self.assertTrue(all(not check["reasons"] for check in decision["checks"]))
        failed = nt.evaluate_quality_gate(self.report("다"), policy)
        self.assertFalse(failed["passed"])
        self.assertEqual(failed["checks"][0]["regression"], 0.5)
        self.assertIn("max_regression", failed["checks"][0]["reasons"][0])
        policy["rules"] = [
            {"metric": "wer", "aggregation": "macro", "max_regression": 0.5}
        ]
        self.assertTrue(nt.evaluate_quality_gate(self.report("다"), policy)["passed"])

    def test_higher_better_metrics_have_reverse_regression_sign(self):
        report = nt.compare_systems(
            ["서울"],
            {"baseline": ["서울"], "candidate": ["서을"]},
            entities=["서울"],
            keywords=["서울"],
            rate_mode="standard",
        )
        policy = self.policy()
        policy["evaluation_config_sha256"] = report["evaluation_config"]["sha256"]
        policy["rules"] = [
            {
                "metric": "keyword_recall",
                "aggregation": "summary",
                "max_regression": 0.1,
            },
            {"metric": "entity_f1", "aggregation": "summary", "min_score": 1},
            {"metric": "crr", "aggregation": "micro", "max_regression": 0},
        ]
        result = nt.evaluate_quality_gate(report, policy)
        self.assertFalse(result["passed"])
        self.assertGreater(result["checks"][0]["regression"], 0)
        self.assertGreater(result["checks"][2]["regression"], 0)

    def test_bad_or_mismatched_policy_fails_closed(self):
        for key, value in (
            ("schema", "unknown"),
            ("report_schema", "nlptutti.comparison/2.0"),
            ("rate_mode", "normalized"),
            ("rm_punctuation", 1),
            ("unicode_normalization", "NFC"),
            ("score_unit", "percent"),
            ("evaluation_config_sha256", "a" * 64),
            ("baseline", "missing"),
            ("candidate", "baseline"),
            ("rules", []),
            ("extra", True),
        ):
            policy = self.policy()
            policy[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                nt.evaluate_quality_gate(self.report(), policy)
        for key in self.policy():
            policy = self.policy()
            del policy[key]
            with self.assertRaises(ValueError):
                nt.evaluate_quality_gate(self.report(), policy)

    def test_bad_rules_and_thresholds(self):
        rules = [
            {"metric": "CER", "aggregation": "micro", "max_regression": 0},
            {"metric": "wer", "aggregation": "summary", "max_regression": 0},
            {"metric": "wer", "aggregation": "micro", "min_score": 0},
            {"metric": "crr", "aggregation": "micro", "max_score": 0},
            {"metric": "wer", "aggregation": "micro"},
            {"metric": "entity_f1", "aggregation": "summary", "min_score": 0.8},
        ]
        rules += [
            {"metric": "cer", "aggregation": "micro", "max_regression": value}
            for value in (2, -1, True, float("nan"), float("inf"), "0.02")
        ]
        for rule in rules:
            policy = self.policy()
            policy["rules"] = [rule]
            with self.subTest(rule=rule), self.assertRaises(ValueError):
                nt.evaluate_quality_gate(self.report(), policy)
        policy = self.policy()
        policy["rules"] *= 2
        with self.assertRaisesRegex(ValueError, "duplicates"):
            nt.evaluate_quality_gate(self.report(), policy)

    def test_standard_insertions_are_not_clipped(self):
        report = nt.compare_systems(
            ["가"],
            {"baseline": ["가"], "candidate": ["가 나 다 라"]},
            rate_mode="standard",
        )
        result = nt.evaluate_quality_gate(report, self.policy())
        self.assertFalse(result["passed"])
        self.assertGreater(result["checks"][1]["candidate_score"], 1)

    def test_decision_is_deterministic_and_does_not_mutate_inputs(self):
        report, policy = self.report(), self.policy()
        before = copy.deepcopy((report, policy))
        first = nt.evaluate_quality_gate(report, policy)
        second = nt.evaluate_quality_gate(report, policy)
        self.assertEqual(first, second)
        self.assertEqual((report, policy), before)
        first["policy"]["rules"].clear()
        self.assertTrue(policy["rules"])

    def test_cli_exit_codes_and_preserved_output_on_bad_input(self):
        with tempfile.TemporaryDirectory() as directory:
            report_path, policy_path, decision_path = [
                Path(directory) / name
                for name in ("report.json", "policy.json", "decision.json")
            ]
            policy_path.write_text(json.dumps(self.policy()), encoding="utf-8")
            for candidate, expected in (("가", 0), ("다", 3)):
                report_path.write_text(
                    nt.render_comparison_json(self.report(candidate)), encoding="utf-8"
                )
                self.assertEqual(
                    main(
                        [
                            "gate",
                            str(report_path),
                            "--policy",
                            str(policy_path),
                            "--output",
                            str(decision_path),
                        ]
                    ),
                    expected,
                )
                decision = json.loads(decision_path.read_text(encoding="utf-8"))
                self.assertEqual(decision["passed"], expected == 0)
            before = decision_path.read_bytes()
            policy_path.write_text('{"schema":1,"schema":2}', encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(
                SystemExit
            ) as caught:
                main(
                    [
                        "gate",
                        str(report_path),
                        "--policy",
                        str(policy_path),
                        "--output",
                        str(decision_path),
                    ]
                )
            self.assertEqual(caught.exception.code, 2)
            self.assertEqual(decision_path.read_bytes(), before)

    def test_documented_sample_gate_workflow(self):
        document = json.loads(
            (ROOT / "examples/comparison_input.json").read_text(encoding="utf-8")
        )
        report = nt.compare_systems(
            document["references"], document["systems"], rate_mode="standard"
        )
        self.assertTrue(nt.evaluate_quality_gate(report, self.policy())["passed"])

    def test_action_recipe_uses_the_same_cli_fixture(self):
        document = (ROOT / "docs/quality-gate.md").read_text(encoding="utf-8")
        commands = re.findall(r"^      - run: nlptutti (.+)$", document, re.MULTILINE)
        self.assertEqual(len(commands), 3)
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "examples").mkdir()
            (root / "examples/gate_policy.json").write_text(json.dumps(self.policy()), encoding="utf-8")
            try:
                os.chdir(root)
                for command in commands:
                    self.assertEqual(main(shlex.split(command)), 0)
            finally:
                os.chdir(previous)
            decision = json.loads((root / "decision.json").read_text(encoding="utf-8"))
            self.assertTrue(decision["passed"])
