"""Paired bootstrap utilities for corpus-level STT metrics."""

import math
import random
from typing import Dict, List, Mapping, NamedTuple, Optional, Sequence

from nlptutti.asr_metrics import (
    _calculate_error_rate,
    _measure_cer,
    _measure_wer,
    _preprocess_cer_text,
    _preprocess_wer_text,
)
from nlptutti.comparison_types import ConfidenceInterval


class EditStatistics(NamedTuple):
    hits: int
    substitutions: int
    deletions: int
    insertions: int


MetricStatistics = Dict[str, List[EditStatistics]]


def build_item_statistics(
    references: Sequence[str],
    hypotheses: Sequence[str],
    rm_punctuation: bool,
    unicode_normalization: Optional[str],
) -> MetricStatistics:
    result: MetricStatistics = {"cer": [], "wer": []}
    for reference, hypothesis in zip(references, hypotheses):
        processed_cer_reference = _preprocess_cer_text(
            reference, rm_punctuation, unicode_normalization
        )
        processed_cer_hypothesis = _preprocess_cer_text(
            hypothesis, rm_punctuation, unicode_normalization
        )
        result["cer"].append(
            EditStatistics(
                *_measure_cer(processed_cer_reference, processed_cer_hypothesis)
            )
        )

        processed_wer_reference = _preprocess_wer_text(
            reference, rm_punctuation, unicode_normalization
        )
        processed_wer_hypothesis = _preprocess_wer_text(
            hypothesis, rm_punctuation, unicode_normalization
        )
        result["wer"].append(
            EditStatistics(
                *_measure_wer(processed_wer_reference, processed_wer_hypothesis)
            )
        )
    return result


def _sample_rate(
    statistics: Sequence[EditStatistics],
    indices: Sequence[int],
    rate_mode: str,
) -> float:
    hits = sum(statistics[index].hits for index in indices)
    substitutions = sum(statistics[index].substitutions for index in indices)
    deletions = sum(statistics[index].deletions for index in indices)
    insertions = sum(statistics[index].insertions for index in indices)
    return _calculate_error_rate(
        substitutions,
        deletions,
        insertions,
        hits,
        rate_mode,
    )


def _percentile(sorted_values: Sequence[float], probability: float) -> float:
    if not sorted_values:
        raise ValueError("percentile requires at least one value")
    position = (len(sorted_values) - 1) * probability
    lower_index = math.floor(position)
    upper_index = math.ceil(position)
    if lower_index == upper_index:
        return sorted_values[lower_index]
    weight = position - lower_index
    return (
        sorted_values[lower_index] * (1 - weight) + sorted_values[upper_index] * weight
    )


def paired_bootstrap_intervals(
    baseline: Mapping[str, Sequence[EditStatistics]],
    candidate: Mapping[str, Sequence[EditStatistics]],
    *,
    rate_mode: str,
    resamples: int,
    seed: int,
    confidence: float,
) -> Dict[str, ConfidenceInterval]:
    """Return paired percentile intervals for CER and WER micro deltas."""

    item_count = len(baseline["cer"])
    if item_count < 2:
        raise ValueError("paired bootstrap requires at least two aligned items")
    for metric_name in ("cer", "wer"):
        if (
            len(baseline[metric_name]) != item_count
            or len(candidate[metric_name]) != item_count
        ):
            raise ValueError(
                "paired bootstrap statistics must have identical item counts"
            )

    random_generator = random.Random(seed)
    deltas: Dict[str, List[float]] = {"cer": [], "wer": []}
    for _ in range(resamples):
        indices = [random_generator.randrange(item_count) for _ in range(item_count)]
        for metric_name in ("cer", "wer"):
            baseline_rate = _sample_rate(baseline[metric_name], indices, rate_mode)
            candidate_rate = _sample_rate(candidate[metric_name], indices, rate_mode)
            deltas[metric_name].append(candidate_rate - baseline_rate)

    lower_probability = (1 - confidence) / 2
    upper_probability = 1 - lower_probability
    result: Dict[str, ConfidenceInterval] = {}
    for metric_name, values in deltas.items():
        values.sort()
        result[metric_name] = {
            "confidence": confidence,
            "lower": _percentile(values, lower_probability),
            "upper": _percentile(values, upper_probability),
            "method": "paired_percentile_bootstrap",
            "resamples": resamples,
            "seed": seed,
            "sampling_unit": "utterance",
        }
    return result


__all__ = ["EditStatistics", "build_item_statistics", "paired_bootstrap_intervals"]
