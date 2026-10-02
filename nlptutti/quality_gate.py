"""Explicit practical regression limits, independent of significance tests."""

import copy
import math
from typing import Any, Dict, Mapping

from nlptutti.comparison import _fingerprint
from nlptutti.comparison_types import ComparisonReport
from nlptutti.report_validation import validate_comparison_report

POLICY_SCHEMA = "nlptutti.gate-policy/1.0"
GATE_SCHEMA = "nlptutti.quality-gate/1.0"
NUMERIC_TOLERANCE = 1e-12


def _exact(value: Any, path: str, required: set, optional: set) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(path + " must be an object")
    if not required.issubset(value) or set(value) - required - optional:
        raise ValueError(path + " has missing or unsupported fields")
    return value


def _threshold(value: Any, path: str) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not 0 <= value <= 1
    ):
        raise ValueError(path + " must be a finite ratio from 0 to 1, not a percentage")


def _score(system: Mapping[str, Any], metric: str, aggregation: str) -> float:
    if metric in ("cer", "wer", "crr"):
        return float(system["metrics"][metric][aggregation])
    section, key = (
        ("keywords", "recall") if metric == "keyword_recall" else ("entities", "f1")
    )
    if section not in system:
        raise ValueError("report system lacks requested " + section + " evaluation")
    value = system[section]["summary"][key]
    _threshold(value, "report." + section + ".summary." + key)
    return float(value)


def evaluate_quality_gate(
    report: ComparisonReport, policy: Mapping[str, object]
) -> Dict[str, object]:
    """Return a decision with reasons; malformed/mismatched input raises ValueError.

    Thresholds are user-supplied ratios in [0, 1]. Existing metric values are not
    clipped. This is not a hypothesis test or a declaration of a winning model.
    """
    validate_comparison_report(report)
    required = {
        "schema",
        "report_schema",
        "baseline",
        "candidate",
        "rate_mode",
        "rm_punctuation",
        "unicode_normalization",
        "score_unit",
        "evaluation_config_sha256",
        "rules",
    }
    config = _exact(policy, "policy", required, set())
    if config["schema"] != POLICY_SCHEMA:
        raise ValueError("policy.schema must be " + POLICY_SCHEMA)
    if config["report_schema"] != report["schema"]:
        raise ValueError("policy.report_schema must match report.schema")
    if report["evaluator"]["name"] != "nlptutti":
        raise ValueError("gate requires an nlptutti report")
    if config["score_unit"] != "ratio":
        raise ValueError("policy.score_unit must be ratio, not percent")
    if not isinstance(config["rm_punctuation"], bool):
        raise ValueError("policy.rm_punctuation must be a boolean")
    for key in ("rate_mode", "rm_punctuation", "unicode_normalization"):
        if config[key] != report["options"][key]:
            raise ValueError("policy." + key + " must match report.options." + key)
    if config["evaluation_config_sha256"] != report["evaluation_config"]["sha256"]:
        raise ValueError(
            "policy.evaluation_config_sha256 must match report evaluation config"
        )
    systems = {system["id"]: system for system in report["systems"]}
    for key in ("baseline", "candidate"):
        if not isinstance(config[key], str) or config[key] not in systems:
            raise ValueError("policy." + key + " must reference an existing system")
    if config["baseline"] == config["candidate"]:
        raise ValueError("policy baseline and candidate must differ")
    rules = config["rules"]
    if not isinstance(rules, list) or not rules:
        raise ValueError("policy.rules must be a non-empty list")
    checks = []
    seen = set()
    for index, value in enumerate(rules):
        path = "policy.rules[{}]".format(index)
        rule = _exact(
            value,
            path,
            {"metric", "aggregation"},
            {"max_regression", "min_score", "max_score"},
        )
        metric = rule["metric"]
        aggregation = rule["aggregation"]
        if metric not in ("cer", "wer", "crr", "keyword_recall", "entity_f1"):
            raise ValueError(path + ".metric is unsupported")
        allowed_aggregations = (
            ("micro", "macro") if metric in ("cer", "wer", "crr") else ("summary",)
        )
        if aggregation not in allowed_aggregations:
            raise ValueError(path + ".aggregation is unsupported for this metric")
        identity = (metric, aggregation)
        if identity in seen:
            raise ValueError(path + " duplicates a metric/aggregation rule")
        seen.add(identity)
        limits = set(rule) - {"metric", "aggregation"}
        if not limits:
            raise ValueError(path + " requires at least one threshold")
        lower_is_better = metric in ("cer", "wer")
        if (lower_is_better and "min_score" in limits) or (
            not lower_is_better and "max_score" in limits
        ):
            raise ValueError(path + " uses the wrong min/max score direction")
        for key in limits:
            _threshold(rule[key], path + "." + key)
        baseline = _score(systems[config["baseline"]], metric, aggregation)
        candidate = _score(systems[config["candidate"]], metric, aggregation)
        delta = candidate - baseline
        regression = delta if lower_is_better else -delta
        reasons = []
        actuals = {
            "max_regression": regression,
            "max_score": candidate,
            "min_score": candidate,
        }
        for key in sorted(limits):
            actual = actuals[key]
            threshold = float(rule[key])
            violated = actual < threshold if key == "min_score" else actual > threshold
            if violated and not math.isclose(
                actual, threshold, rel_tol=0, abs_tol=NUMERIC_TOLERANCE
            ):
                reasons.append(
                    "{} not satisfied: observed={:.12g}, limit={:.12g}".format(
                        key, actual, threshold
                    )
                )
        checks.append(
            {
                "metric": metric,
                "aggregation": aggregation,
                "baseline_score": baseline,
                "candidate_score": candidate,
                "delta": delta,
                "regression": regression,
                "passed": not reasons,
                "reasons": reasons,
            }
        )
    return {
        "schema": GATE_SCHEMA,
        "passed": all(check["passed"] for check in checks),
        "policy": copy.deepcopy(dict(policy)),
        "report_sha256": _fingerprint(report),
        "numeric_tolerance": NUMERIC_TOLERANCE,
        "checks": checks,
        "warnings": ["practical thresholds are not statistical significance tests"]
        + list(report["warnings"]),
    }


__all__ = ["evaluate_quality_gate"]
