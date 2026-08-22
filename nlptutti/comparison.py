"""Offline comparison of two or more STT system outputs."""

import hashlib
import json
from importlib import metadata
from itertools import combinations
from typing import (
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Union,
    cast,
)

from nlptutti.asr_metrics import (
    _resolve_rate_mode,
    _resolve_unicode_normalization,
    evaluate_corpus,
    evaluate_keywords,
    get_crr,
)
from nlptutti.bootstrap import (
    MetricStatistics,
    build_item_statistics,
    paired_bootstrap_intervals,
)
from nlptutti.comparison_types import (
    COMPARISON_SCHEMA,
    AggregateMetric,
    ComparisonReport,
    ComparisonSystem,
    EvaluationConfig,
    MetricDelta,
    PairwiseDelta,
    RecognitionMetric,
    SystemMetrics,
)
from nlptutti.diagnostics import KOREAN_DIAGNOSTIC_PROFILE, diagnose_korean_errors
from nlptutti.entity_metrics import evaluate_entities

TextCollection = Union[Iterable[str], Mapping[str, str]]
KeywordInput = Union[str, Sequence[str], Mapping[str, Union[str, Sequence[str]]]]


def _package_version() -> str:
    try:
        return metadata.version("nlptutti")
    except metadata.PackageNotFoundError:
        return "unknown"


def _validate_ids(values: Sequence[object], field_name: str) -> List[str]:
    resolved = []
    seen = set()
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"every {field_name} value must be a non-empty string")
        if value in seen:
            raise ValueError(f"{field_name} values must be unique")
        seen.add(value)
        resolved.append(value)
    return resolved


def _coerce_text_values(values: object, field_name: str) -> List[str]:
    if isinstance(values, (str, bytes)) or isinstance(values, Mapping):
        raise TypeError(f"{field_name} must be an iterable of strings")
    try:
        resolved = list(cast(Iterable[object], values))
    except TypeError as error:
        raise TypeError(f"{field_name} must be an iterable of strings") from error
    if not resolved:
        raise ValueError(f"{field_name} must not be empty")
    if not all(isinstance(value, str) for value in resolved):
        raise TypeError(f"every value in {field_name} must be a string")
    return cast(List[str], resolved)


def _coerce_references(
    references: TextCollection,
    ids: Optional[Iterable[str]],
) -> Tuple[List[str], List[str], bool]:
    if isinstance(references, Mapping):
        if ids is not None:
            raise ValueError("ids must be omitted when references is a mapping")
        reference_ids = sorted(_validate_ids(list(references.keys()), "reference ID"))
        if not reference_ids:
            raise ValueError("references must not be empty")
        reference_values = [references[item_id] for item_id in reference_ids]
        if not all(isinstance(value, str) for value in reference_values):
            raise TypeError("every reference value must be a string")
        return reference_ids, cast(List[str], reference_values), True

    reference_values = _coerce_text_values(references, "references")
    if ids is None:
        reference_ids = [str(index) for index in range(len(reference_values))]
    else:
        if isinstance(ids, (str, bytes)):
            raise TypeError("ids must be an iterable of strings")
        reference_ids = _validate_ids(list(ids), "ID")
        if len(reference_ids) != len(reference_values):
            raise ValueError("ids and references must have the same length")
    return reference_ids, reference_values, False


def _coerce_hypotheses(
    values: object,
    system_id: str,
    reference_ids: Sequence[str],
    references_use_ids: bool,
) -> List[str]:
    field_name = f"systems[{system_id!r}]"
    if isinstance(values, Mapping):
        hypothesis_ids = _validate_ids(list(values.keys()), f"{field_name} ID")
        if set(hypothesis_ids) != set(reference_ids):
            missing = sorted(set(reference_ids) - set(hypothesis_ids))
            extra = sorted(set(hypothesis_ids) - set(reference_ids))
            raise ValueError(
                f"{field_name} IDs must exactly match references; "
                f"missing={missing}, extra={extra}"
            )
        hypotheses = [values[item_id] for item_id in reference_ids]
        if not all(isinstance(value, str) for value in hypotheses):
            raise TypeError(f"every value in {field_name} must be a string")
        return cast(List[str], hypotheses)

    if references_use_ids:
        raise TypeError(
            f"{field_name} must be an ID-to-text mapping when references is a mapping"
        )
    hypotheses = _coerce_text_values(values, field_name)
    if len(hypotheses) != len(reference_ids):
        raise ValueError(f"{field_name} and references must have the same length")
    return hypotheses


def _coerce_systems(
    systems: Mapping[str, TextCollection],
    reference_ids: Sequence[str],
    references_use_ids: bool,
) -> List[Tuple[str, List[str]]]:
    if not isinstance(systems, Mapping):
        raise TypeError("systems must be a mapping from system ID to transcripts")
    if len(systems) < 2:
        raise ValueError("systems must contain at least two STT systems")

    system_ids = _validate_ids(list(systems.keys()), "system ID")
    return [
        (
            system_id,
            _coerce_hypotheses(
                systems[system_id],
                system_id,
                reference_ids,
                references_use_ids,
            ),
        )
        for system_id in system_ids
    ]


def _fingerprint(value: object) -> str:
    serialized = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def _canonical_config_value(value: object, field_name: str) -> object:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        result = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"every key in {field_name} must be a string")
            result[key] = _canonical_config_value(item, field_name)
        return result
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [_canonical_config_value(item, field_name) for item in value]
    raise TypeError(
        f"{field_name} must contain only strings, ordered sequences, and mappings"
    )


def _evaluation_config(
    keywords: Optional[KeywordInput],
    entities: Optional[KeywordInput],
    entity_aliases: Optional[Mapping[str, Union[str, Sequence[str]]]],
) -> EvaluationConfig:
    if entity_aliases is not None and entities is None:
        raise ValueError("entity_aliases requires entities")
    configured = any(
        value is not None for value in (keywords, entities, entity_aliases)
    )
    fingerprint = None
    if configured:
        fingerprint = _fingerprint(
            {
                "keywords": (
                    None
                    if keywords is None
                    else _canonical_config_value(keywords, "keywords")
                ),
                "entities": (
                    None
                    if entities is None
                    else _canonical_config_value(entities, "entities")
                ),
                "entity_aliases": (
                    None
                    if entity_aliases is None
                    else _canonical_config_value(entity_aliases, "entity_aliases")
                ),
            }
        )
    return {
        "keywords": keywords is not None,
        "entities": entities is not None,
        "entity_aliases": entity_aliases is not None,
        "sha256": fingerprint,
    }


def _aggregate_metric(value: Mapping[str, object]) -> AggregateMetric:
    return {
        "micro": cast(float, value["micro"]),
        "macro": cast(float, value["macro"]),
        "hits": cast(int, value["hits"]),
        "substitutions": cast(int, value["substitutions"]),
        "deletions": cast(int, value["deletions"]),
        "insertions": cast(int, value["insertions"]),
    }


def _system_metrics(
    references: Sequence[str],
    hypotheses: Sequence[str],
    rm_punctuation: bool,
    rate_mode: str,
    unicode_normalization: Optional[str],
) -> SystemMetrics:
    corpus = evaluate_corpus(
        references,
        hypotheses,
        rm_punctuation=rm_punctuation,
        rate_mode=rate_mode,
        unicode_normalization=unicode_normalization,
    )
    cer = _aggregate_metric(cast(Mapping[str, object], corpus["cer"]))
    wer = _aggregate_metric(cast(Mapping[str, object], corpus["wer"]))
    crr_values = [
        cast(
            float,
            get_crr(
                reference,
                hypothesis,
                rm_punctuation=rm_punctuation,
                rate_mode=rate_mode,
                unicode_normalization=unicode_normalization,
            )["crr"],
        )
        for reference, hypothesis in zip(references, hypotheses)
    ]
    crr: RecognitionMetric = {
        "micro": round(1 - cer["micro"], 2),
        "macro": sum(crr_values) / len(crr_values),
    }
    return {"cer": cer, "wer": wer, "crr": crr}


def _metric_delta(
    baseline: Union[AggregateMetric, RecognitionMetric],
    candidate: Union[AggregateMetric, RecognitionMetric],
) -> MetricDelta:
    return {
        "micro": float(candidate["micro"]) - float(baseline["micro"]),
        "macro": float(candidate["macro"]) - float(baseline["macro"]),
    }


def _pairwise_results(
    systems: Sequence[ComparisonSystem],
    item_statistics: Mapping[str, MetricStatistics],
    rate_mode: str,
    bootstrap: int,
    seed: int,
    confidence: float,
) -> List[PairwiseDelta]:
    results: List[PairwiseDelta] = []
    for baseline, candidate in combinations(systems, 2):
        metrics: Dict[str, MetricDelta] = {
            "cer": _metric_delta(
                baseline["metrics"]["cer"], candidate["metrics"]["cer"]
            ),
            "wer": _metric_delta(
                baseline["metrics"]["wer"], candidate["metrics"]["wer"]
            ),
            "crr": _metric_delta(
                baseline["metrics"]["crr"], candidate["metrics"]["crr"]
            ),
        }
        if bootstrap:
            intervals = paired_bootstrap_intervals(
                item_statistics[baseline["id"]],
                item_statistics[candidate["id"]],
                rate_mode=rate_mode,
                resamples=bootstrap,
                seed=seed,
                confidence=confidence,
            )
            for metric_name, interval in intervals.items():
                metrics[metric_name]["confidence_interval"] = interval
        results.append(
            {
                "baseline": baseline["id"],
                "candidate": candidate["id"],
                "metrics": metrics,
            }
        )
    return results


def compare_systems(
    references: TextCollection,
    systems: Mapping[str, TextCollection],
    *,
    ids: Optional[Iterable[str]] = None,
    rm_punctuation: bool = True,
    rate_mode: str = "normalized",
    unicode_normalization: Optional[str] = None,
    keywords: Optional[KeywordInput] = None,
    entities: Optional[KeywordInput] = None,
    entity_aliases: Optional[Mapping[str, Union[str, Sequence[str]]]] = None,
    bootstrap: int = 0,
    seed: int = 42,
    confidence: float = 0.95,
    diagnostic_profile: Optional[str] = None,
    include_transcripts: bool = False,
) -> ComparisonReport:
    """Compare two or more aligned STT outputs without running an STT model.

    ``references`` and every system may be ordered string iterables. For an
    ID-aligned corpus, pass mappings with exactly the same ID set. Raw text is
    excluded from the returned report unless ``include_transcripts=True`` is
    explicitly requested.
    """

    if not isinstance(rm_punctuation, bool):
        raise TypeError("rm_punctuation must be a boolean")
    if not isinstance(include_transcripts, bool):
        raise TypeError("include_transcripts must be a boolean")
    if diagnostic_profile not in (None, KOREAN_DIAGNOSTIC_PROFILE):
        raise ValueError("diagnostic_profile must be None or 'korean-v1'")
    if isinstance(bootstrap, bool) or not isinstance(bootstrap, int) or bootstrap < 0:
        raise ValueError("bootstrap must be a non-negative integer")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise ValueError("confidence must be a number between 0 and 1")
    confidence = float(confidence)
    if not 0 < confidence < 1:
        raise ValueError("confidence must be a number between 0 and 1")
    resolved_rate_mode = _resolve_rate_mode(rate_mode)
    resolved_unicode_normalization = _resolve_unicode_normalization(
        unicode_normalization
    )
    reference_ids, reference_values, references_use_ids = _coerce_references(
        references, ids
    )
    system_values = _coerce_systems(systems, reference_ids, references_use_ids)
    evaluation_config = _evaluation_config(keywords, entities, entity_aliases)

    system_results: List[ComparisonSystem] = []
    item_statistics: Dict[str, MetricStatistics] = {}
    for system_id, hypotheses in system_values:
        result: ComparisonSystem = {
            "id": system_id,
            "metrics": _system_metrics(
                reference_values,
                hypotheses,
                rm_punctuation,
                resolved_rate_mode,
                resolved_unicode_normalization,
            ),
            "provenance": {
                "hypothesis_sha256": _fingerprint(hypotheses),
                "item_count": len(hypotheses),
            },
        }
        if keywords is not None:
            result["keywords"] = evaluate_keywords(
                reference_values, hypotheses, keywords
            )
        if entities is not None:
            result["entities"] = evaluate_entities(
                reference_values,
                hypotheses,
                entities,
                aliases=entity_aliases,
                rm_punctuation=rm_punctuation,
                rate_mode=resolved_rate_mode,
                unicode_normalization=resolved_unicode_normalization,
            )
        if diagnostic_profile is not None:
            result["diagnostics"] = diagnose_korean_errors(
                reference_values,
                hypotheses,
                rm_punctuation=rm_punctuation,
                rate_mode=resolved_rate_mode,
                unicode_normalization=resolved_unicode_normalization,
                keyword_result=result.get("keywords"),
                entity_result=result.get("entities"),
            )
        system_results.append(result)
        item_statistics[system_id] = build_item_statistics(
            reference_values,
            hypotheses,
            rm_punctuation,
            resolved_unicode_normalization,
        )

    warnings: List[str] = []
    report: ComparisonReport = {
        "schema": COMPARISON_SCHEMA,
        "evaluator": {"name": "nlptutti", "version": _package_version()},
        "options": {
            "rate_mode": resolved_rate_mode,
            "rm_punctuation": rm_punctuation,
            "unicode_normalization": resolved_unicode_normalization,
            "bootstrap_resamples": bootstrap,
            "bootstrap_seed": seed,
            "confidence": confidence,
            "diagnostic_profile": diagnostic_profile,
        },
        "dataset": {
            "item_count": len(reference_values),
            "ids_sha256": _fingerprint(reference_ids),
            "references_sha256": _fingerprint(reference_values),
        },
        "evaluation_config": evaluation_config,
        "systems": system_results,
        "pairwise": _pairwise_results(
            system_results,
            item_statistics,
            resolved_rate_mode,
            bootstrap,
            seed,
            confidence,
        ),
        "warnings": warnings,
    }
    if diagnostic_profile is not None:
        warnings.append(
            "diagnostics can include observed character edit tokens; "
            "review the bundle before sharing"
        )
    if include_transcripts:
        warnings.append(
            "raw_inputs contains transcript text because include_transcripts=True"
        )
        report["raw_inputs"] = {
            "ids": list(reference_ids),
            "references": list(reference_values),
            "systems": [
                {"id": system_id, "hypotheses": list(hypotheses)}
                for system_id, hypotheses in system_values
            ],
        }

    json.dumps(report, ensure_ascii=False, allow_nan=False, sort_keys=True)
    return report


__all__ = ["compare_systems"]
