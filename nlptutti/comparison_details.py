"""Opt-in item and user-labelled slice views of already measured edit counts."""

from itertools import combinations
from typing import Dict, List, Mapping, Optional, Sequence

from nlptutti.bootstrap import MetricStatistics, summarize_statistics
from nlptutti.comparison_types import (
    ComparisonDetails,
    DetailSystem,
    ItemDelta,
    PairwiseDetail,
    PairwiseDelta,
    SliceReport,
    SliceSystem,
    SystemMetrics,
    MetricDelta,
)


def validate_labels(
    labels: Optional[Mapping[str, Mapping[str, str]]], ids: Sequence[str]
) -> None:
    if labels is None:
        return
    if not isinstance(labels, Mapping) or set(labels) != set(ids):
        raise ValueError("labels must map exactly the reference IDs to label objects")
    expected = None
    for item_id in ids:
        values = labels[item_id]
        if not isinstance(values, Mapping) or not values:
            raise ValueError("each labels entry must be a non-empty object")
        if not all(
            isinstance(k, str) and k.strip() and isinstance(v, str) and v.strip()
            for k, v in values.items()
        ):
            raise ValueError("label fields and values must be non-empty strings")
        if expected is None:
            expected = set(values)
        if set(values) != expected:
            raise ValueError("each labels entry must use the same label fields")


def _subset(statistics: MetricStatistics, indices: Sequence[int]) -> MetricStatistics:
    return {
        name: [statistics[name][index] for index in indices] for name in ("cer", "wer")
    }


def _deltas(baseline: SystemMetrics, candidate: SystemMetrics) -> Dict[str, float]:
    return {
        "cer": candidate["cer"]["micro"] - baseline["cer"]["micro"],
        "wer": candidate["wer"]["micro"] - baseline["wer"]["micro"],
        "crr": candidate["crr"]["micro"] - baseline["crr"]["micro"],
    }


def build_item_details(
    ids: Sequence[str],
    statistics: Mapping[str, MetricStatistics],
    rate_mode: str,
    top_n: int,
) -> ComparisonDetails:
    systems: List[DetailSystem] = [
        {
            "id": system_id,
            "items": [
                {
                    "id": item_id,
                    "metrics": summarize_statistics(
                        _subset(values, [index]), rate_mode
                    ),
                }
                for index, item_id in enumerate(ids)
            ],
        }
        for system_id, values in statistics.items()
    ]
    pairwise: List[PairwiseDetail] = []
    for baseline, candidate in combinations(systems, 2):
        rows: List[ItemDelta] = [
            {"id": item_id, "deltas": _deltas(left["metrics"], right["metrics"])}
            for item_id, left, right in zip(ids, baseline["items"], candidate["items"])
        ]
        top_regressions: Dict[str, List[str]] = {}
        top_improvements: Dict[str, List[str]] = {}
        for name in ("cer", "wer"):
            worse = sorted(
                (row for row in rows if row["deltas"][name] > 0),
                key=lambda row: (-row["deltas"][name], row["id"]),
            )
            better = sorted(
                (row for row in rows if row["deltas"][name] < 0),
                key=lambda row: (row["deltas"][name], row["id"]),
            )
            top_regressions[name] = [row["id"] for row in worse[:top_n]]
            top_improvements[name] = [row["id"] for row in better[:top_n]]
        pairwise.append(
            {
                "baseline": baseline["id"],
                "candidate": candidate["id"],
                "items": rows,
                "top_regressions": top_regressions,
                "top_improvements": top_improvements,
            }
        )
    return {
        "schema": "nlptutti.details/1.0",
        "top_n": top_n,
        "systems": systems,
        "pairwise": pairwise,
    }


def build_slices(
    ids: Sequence[str],
    labels: Mapping[str, Mapping[str, str]],
    statistics: Mapping[str, MetricStatistics],
    rate_mode: str,
) -> List[SliceReport]:
    slices: List[SliceReport] = []
    for field in sorted(labels[ids[0]]):
        for value in sorted({labels[item_id][field] for item_id in ids}):
            indices = [
                index
                for index, item_id in enumerate(ids)
                if labels[item_id][field] == value
            ]
            systems: List[SliceSystem] = [
                {
                    "id": system_id,
                    "metrics": summarize_statistics(
                        _subset(values, indices), rate_mode
                    ),
                }
                for system_id, values in statistics.items()
            ]
            pairs: List[PairwiseDelta] = []
            for baseline, candidate in combinations(systems, 2):
                metrics: Dict[str, MetricDelta] = {}
                for name in ("cer", "wer", "crr"):
                    metrics[name] = {
                        "micro": candidate["metrics"][name]["micro"]
                        - baseline["metrics"][name]["micro"],
                        "macro": candidate["metrics"][name]["macro"]
                        - baseline["metrics"][name]["macro"],
                    }
                pairs.append(
                    {
                        "baseline": baseline["id"],
                        "candidate": candidate["id"],
                        "metrics": metrics,
                    }
                )
            slices.append(
                {
                    "field": field,
                    "value": value,
                    "item_count": len(indices),
                    "systems": systems,
                    "pairwise": pairs,
                }
            )
    return slices
