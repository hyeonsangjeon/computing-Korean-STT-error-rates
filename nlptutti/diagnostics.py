"""Deterministic, opt-in Korean STT error diagnostics."""

from __future__ import annotations

import re
from collections import Counter
from typing import (
    Counter as CounterType,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Union,
    cast,
)

from nlptutti.asr_metrics import (
    COMPLEX_EOMI,
    COMPLEX_JOSA,
    _preprocess_wer_text,
    explain_errors,
)


DIAGNOSTIC_SCHEMA = "nlptutti.diagnostics/1.0"
KOREAN_DIAGNOSTIC_PROFILE = "korean-v1"

_TOKEN_CHAR = "0-9A-Za-z가-힣"
_NUMBER_UNITS = (
    "킬로그램",
    "센티미터",
    "밀리미터",
    "킬로미터",
    "퍼센트",
    "시간",
    "만원",
    "억원",
    "kg",
    "cm",
    "mm",
    "km",
    "%",
    "명",
    "개",
    "원",
    "초",
    "분",
    "회",
    "대",
    "층",
)


def _alternation(values: Sequence[str]) -> str:
    return "|".join(
        re.escape(value)
        for value in sorted(set(values), key=lambda item: (-len(item), item))
    )


_NUMBER_UNIT_PATTERN = re.compile(
    r"(?<![{token}])"
    r"(?P<number>\d+(?:,\d{{3}})*(?:\.\d+)?)\s*"
    r"(?P<unit>{units})"
    r"(?:{josa})?"
    r"(?![{token}])".format(
        token=_TOKEN_CHAR,
        units=_alternation(_NUMBER_UNITS),
        josa=_alternation(COMPLEX_JOSA),
    ),
    re.IGNORECASE,
)

_SUFFIXES = sorted(
    [(suffix, "josa") for suffix in set(COMPLEX_JOSA)]
    + [(suffix, "eomi") for suffix in set(COMPLEX_EOMI)],
    key=lambda item: (-len(item[0]), item[0], item[1]),
)

_RULES = (
    {
        "name": "spacing-boundary-difference",
        "version": "1.0",
        "status": "stable",
    },
    {
        "name": "number-unit-mention-difference",
        "version": "1.0",
        "status": "experimental",
    },
    {
        "name": "josa-eomi-adjacent-substitution",
        "version": "1.0",
        "status": "experimental",
    },
    {
        "name": "top-character-edits",
        "version": "1.0",
        "status": "stable",
        "limit": 10,
    },
)


def _spacing_signature(
    text: str,
    rm_punctuation: bool,
    unicode_normalization: Optional[str],
) -> Tuple[str, set]:
    processed = _preprocess_wer_text(text, rm_punctuation, unicode_normalization)
    chunks = re.findall(r"\S+", processed)
    boundaries = set()
    position = 0
    for chunk in chunks[:-1]:
        position += len(chunk)
        boundaries.add(position)
    return "".join(chunks), boundaries


def _spacing_differences(
    references: Sequence[str],
    hypotheses: Sequence[str],
    rm_punctuation: bool,
    unicode_normalization: Optional[str],
) -> Dict[str, int]:
    result = {
        "eligible_items": 0,
        "skipped_lexical_items": 0,
        "affected_items": 0,
        "missing_boundaries": 0,
        "extra_boundaries": 0,
    }
    for reference, hypothesis in zip(references, hypotheses):
        reference_compact, reference_boundaries = _spacing_signature(
            reference, rm_punctuation, unicode_normalization
        )
        hypothesis_compact, hypothesis_boundaries = _spacing_signature(
            hypothesis, rm_punctuation, unicode_normalization
        )
        if reference_compact != hypothesis_compact:
            result["skipped_lexical_items"] += 1
            continue
        result["eligible_items"] += 1
        missing = len(reference_boundaries - hypothesis_boundaries)
        extra = len(hypothesis_boundaries - reference_boundaries)
        result["missing_boundaries"] += missing
        result["extra_boundaries"] += extra
        if missing or extra:
            result["affected_items"] += 1
    return result


def _number_unit_mentions(text: str) -> Counter:
    return Counter(
        (
            match.group("number").replace(",", ""),
            match.group("unit").lower(),
        )
        for match in _NUMBER_UNIT_PATTERN.finditer(text)
    )


def _number_unit_differences(
    references: Sequence[str], hypotheses: Sequence[str]
) -> Dict[str, int]:
    result = {
        "reference_mentions": 0,
        "hypothesis_mentions": 0,
        "matched_mentions": 0,
        "missing_mentions": 0,
        "unexpected_mentions": 0,
        "affected_items": 0,
    }
    for reference, hypothesis in zip(references, hypotheses):
        reference_mentions = _number_unit_mentions(reference)
        hypothesis_mentions = _number_unit_mentions(hypothesis)
        matched = reference_mentions & hypothesis_mentions
        missing = reference_mentions - hypothesis_mentions
        unexpected = hypothesis_mentions - reference_mentions
        result["reference_mentions"] += sum(reference_mentions.values())
        result["hypothesis_mentions"] += sum(hypothesis_mentions.values())
        result["matched_mentions"] += sum(matched.values())
        result["missing_mentions"] += sum(missing.values())
        result["unexpected_mentions"] += sum(unexpected.values())
        if missing or unexpected:
            result["affected_items"] += 1
    return result


def _split_suffix(token: str) -> Optional[Tuple[str, str, str]]:
    for suffix, category in _SUFFIXES:
        if token.endswith(suffix) and len(token) > len(suffix):
            return token[: -len(suffix)], suffix, category
    return None


def _suffix_adjacent_differences(
    references: Sequence[str],
    hypotheses: Sequence[str],
    rm_punctuation: bool,
    rate_mode: str,
    unicode_normalization: Optional[str],
) -> Dict[str, int]:
    result = {
        "substitutions": 0,
        "josa_substitutions": 0,
        "eomi_substitutions": 0,
        "affected_items": 0,
    }
    for reference, hypothesis in zip(references, hypotheses):
        explanation = explain_errors(
            reference,
            hypothesis,
            unit="word",
            rm_punctuation=rm_punctuation,
            rate_mode=rate_mode,
            unicode_normalization=unicode_normalization,
        )
        item_count = 0
        for edit in cast(List[Mapping[str, str]], explanation["alignment"]):
            if edit["type"] != "substitute":
                continue
            reference_suffix = _split_suffix(edit["reference"])
            hypothesis_suffix = _split_suffix(edit["hypothesis"])
            if reference_suffix is None or hypothesis_suffix is None:
                continue
            ref_stem, ref_suffix, ref_category = reference_suffix
            hyp_stem, hyp_suffix, hyp_category = hypothesis_suffix
            if (
                ref_stem != hyp_stem
                or ref_suffix == hyp_suffix
                or ref_category != hyp_category
            ):
                continue
            result["substitutions"] += 1
            result["{}_substitutions".format(ref_category)] += 1
            item_count += 1
        if item_count:
            result["affected_items"] += 1
    return result


def _ranked(counter: Counter, kind: str, limit: int) -> List[Dict[str, object]]:
    rows = []
    for value, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))[
        :limit
    ]:
        if kind == "substitutions":
            reference, hypothesis = value
            rows.append(
                {
                    "reference": reference,
                    "hypothesis": hypothesis,
                    "count": count,
                }
            )
        elif kind == "deletions":
            rows.append({"reference": value, "count": count})
        else:
            rows.append({"hypothesis": value, "count": count})
    return rows


def _top_character_edits(
    references: Sequence[str],
    hypotheses: Sequence[str],
    rm_punctuation: bool,
    rate_mode: str,
    unicode_normalization: Optional[str],
    limit: int = 10,
) -> Dict[str, object]:
    substitutions: CounterType[Tuple[str, str]] = Counter()
    deletions: CounterType[str] = Counter()
    insertions: CounterType[str] = Counter()
    for reference, hypothesis in zip(references, hypotheses):
        explanation = explain_errors(
            reference,
            hypothesis,
            unit="character",
            rm_punctuation=rm_punctuation,
            rate_mode=rate_mode,
            unicode_normalization=unicode_normalization,
        )
        frequencies = cast(
            Mapping[str, List[Mapping[str, Union[str, int]]]],
            explanation["error_frequencies"],
        )
        for row in frequencies["substitutions"]:
            substitution = (
                cast(str, row["reference"]),
                cast(str, row["hypothesis"]),
            )
            substitutions[substitution] += cast(int, row["count"])
        for row in frequencies["deletions"]:
            deletions[cast(str, row["reference"])] += cast(int, row["count"])
        for row in frequencies["insertions"]:
            insertions[cast(str, row["hypothesis"])] += cast(int, row["count"])
    return {
        "limit": limit,
        "substitutions": _ranked(substitutions, "substitutions", limit),
        "deletions": _ranked(deletions, "deletions", limit),
        "insertions": _ranked(insertions, "insertions", limit),
    }


def _metric_breakdowns(
    keyword_result: Optional[Mapping[str, object]],
    entity_result: Optional[Mapping[str, object]],
) -> Dict[str, object]:
    result: Dict[str, object] = {}
    if keyword_result is not None:
        summary = cast(Mapping[str, Union[int, float]], keyword_result["summary"])
        result["keywords"] = {
            "recall": summary["recall"],
            "false_positives": summary["false_positives"],
            "false_negatives": summary["false_negatives"],
        }
    if entity_result is not None:
        summary = cast(Mapping[str, Union[int, float]], entity_result["summary"])
        entity_cer = cast(Mapping[str, Union[int, float]], entity_result["entity_cer"])
        result["entities"] = {
            "f1": summary["f1"],
            "cer_micro": entity_cer["micro"],
            "cer_macro": entity_cer["macro"],
        }
    return result


def diagnose_korean_errors(
    references: Sequence[str],
    hypotheses: Sequence[str],
    *,
    rm_punctuation: bool,
    rate_mode: str,
    unicode_normalization: Optional[str],
    keyword_result: Optional[Mapping[str, object]] = None,
    entity_result: Optional[Mapping[str, object]] = None,
) -> Dict[str, object]:
    """Build the versioned ``korean-v1`` diagnostic profile.

    Number/unit and suffix-adjacent results are explicit heuristics. They are
    not token classification or morphological analysis.
    """

    if len(references) != len(hypotheses):
        raise ValueError("references and hypotheses must have the same length")
    return {
        "schema": DIAGNOSTIC_SCHEMA,
        "profile": KOREAN_DIAGNOSTIC_PROFILE,
        "rules": [dict(rule) for rule in _RULES],
        "spacing_boundary": _spacing_differences(
            references, hypotheses, rm_punctuation, unicode_normalization
        ),
        "number_unit": _number_unit_differences(references, hypotheses),
        "josa_eomi_adjacent": _suffix_adjacent_differences(
            references,
            hypotheses,
            rm_punctuation,
            rate_mode,
            unicode_normalization,
        ),
        "top_character_edits": _top_character_edits(
            references,
            hypotheses,
            rm_punctuation,
            rate_mode,
            unicode_normalization,
        ),
        "metric_breakdowns": _metric_breakdowns(keyword_result, entity_result),
    }


__all__ = [
    "DIAGNOSTIC_SCHEMA",
    "KOREAN_DIAGNOSTIC_PROFILE",
    "diagnose_korean_errors",
]
