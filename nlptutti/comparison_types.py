"""Public type contracts for reproducible STT system comparisons."""

from typing import Dict, List, Optional, TypedDict, Union

COMPARISON_SCHEMA = "nlptutti.comparison/1.0"

JSONScalar = Union[str, int, float, bool, None]


class EvaluatorInfo(TypedDict):
    name: str
    version: str


class ComparisonOptionsRequired(TypedDict):
    rate_mode: str
    rm_punctuation: bool
    unicode_normalization: Optional[str]
    bootstrap_resamples: int
    bootstrap_seed: int
    confidence: float
    diagnostic_profile: Optional[str]


class ComparisonOptions(ComparisonOptionsRequired, total=False):
    privacy_mode: str


class DatasetInfo(TypedDict):
    item_count: int
    ids_sha256: str
    references_sha256: str


class EvaluationConfig(TypedDict):
    keywords: bool
    entities: bool
    entity_aliases: bool
    sha256: Optional[str]


class AggregateMetric(TypedDict):
    micro: float
    macro: float
    hits: int
    substitutions: int
    deletions: int
    insertions: int


class RecognitionMetric(TypedDict):
    micro: float
    macro: float


class SystemMetrics(TypedDict):
    cer: AggregateMetric
    wer: AggregateMetric
    crr: RecognitionMetric


class SystemProvenance(TypedDict):
    hypothesis_sha256: str
    item_count: int


class ComparisonSystemRequired(TypedDict):
    id: str
    metrics: SystemMetrics
    provenance: SystemProvenance


class ComparisonSystem(ComparisonSystemRequired, total=False):
    keywords: Dict[str, object]
    entities: Dict[str, object]
    diagnostics: Dict[str, object]


class ConfidenceInterval(TypedDict):
    confidence: float
    lower: float
    upper: float
    method: str
    resamples: int
    seed: int
    sampling_unit: str


class MetricDeltaRequired(TypedDict):
    micro: float
    macro: float


class MetricDelta(MetricDeltaRequired, total=False):
    confidence_interval: ConfidenceInterval


class PairwiseDelta(TypedDict):
    baseline: str
    candidate: str
    metrics: Dict[str, MetricDelta]


class RawSystemInput(TypedDict):
    id: str
    hypotheses: List[str]


class RawInputs(TypedDict):
    ids: List[str]
    references: List[str]
    systems: List[RawSystemInput]


class ItemResult(TypedDict):
    id: str
    metrics: SystemMetrics


class DetailSystem(TypedDict):
    id: str
    items: List[ItemResult]


class ItemDelta(TypedDict):
    id: str
    deltas: Dict[str, float]


class PairwiseDetail(TypedDict):
    baseline: str
    candidate: str
    items: List[ItemDelta]
    top_regressions: Dict[str, List[str]]
    top_improvements: Dict[str, List[str]]


class ComparisonDetails(TypedDict):
    schema: str
    top_n: int
    systems: List[DetailSystem]
    pairwise: List[PairwiseDetail]


class SliceSystem(TypedDict):
    id: str
    metrics: SystemMetrics


class SliceReport(TypedDict):
    field: str
    value: str
    item_count: int
    systems: List[SliceSystem]
    pairwise: List[PairwiseDelta]


class ComparisonReportRequired(TypedDict):
    schema: str
    evaluator: EvaluatorInfo
    options: ComparisonOptions
    dataset: DatasetInfo
    evaluation_config: EvaluationConfig
    systems: List[ComparisonSystem]
    pairwise: List[PairwiseDelta]
    warnings: List[str]


class ComparisonReport(ComparisonReportRequired, total=False):
    raw_inputs: RawInputs
    input_sources: Dict[str, object]
    details: ComparisonDetails
    slices: List[SliceReport]
    labels_sha256: str


__all__ = [
    "AggregateMetric",
    "COMPARISON_SCHEMA",
    "ComparisonOptions",
    "ComparisonReport",
    "ComparisonSystem",
    "ConfidenceInterval",
    "DatasetInfo",
    "EvaluationConfig",
    "EvaluatorInfo",
    "MetricDelta",
    "PairwiseDelta",
    "RecognitionMetric",
    "SystemMetrics",
]
