import re
import unicodedata
from collections import Counter
from typing import (
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Pattern,
    Sequence,
    Tuple,
    Union,
)

import jiwer


def levenshtein(u, v):
    prev = None
    curr = [0, *range(1, len(v) + 1)]
    # Operations: (SUB, DEL, INS)
    prev_ops = None
    curr_ops = [(0, 0, i) for i in range(len(v) + 1)]
    for x in range(1, len(u) + 1):
        prev, curr = curr, [x] + ([None] * len(v))
        prev_ops, curr_ops = curr_ops, [(0, x, 0)] + ([None] * len(v))
        for y in range(1, len(v) + 1):
            delcost = prev[y] + 1
            addcost = curr[y - 1] + 1
            subcost = prev[y - 1] + int(u[x - 1] != v[y - 1])
            curr[y] = min(subcost, delcost, addcost)
            if curr[y] == subcost:
                (n_s, n_d, n_i) = prev_ops[y - 1]
                curr_ops[y] = (n_s + int(u[x - 1] != v[y - 1]), n_d, n_i)
            elif curr[y] == delcost:
                (n_s, n_d, n_i) = prev_ops[y]
                curr_ops[y] = (n_s, n_d + 1, n_i)
            else:
                (n_s, n_d, n_i) = curr_ops[y - 1]
                curr_ops[y] = (n_s, n_d, n_i + 1)
    return curr[len(v)], curr_ops[len(v)]


MetricResult = Dict[str, Union[float, int]]

_KOREAN_TOKEN_CHAR = "0-9A-Za-z가-힣"
_RATE_MODES = ("normalized", "standard")
_UNICODE_NORMALIZATION_FORMS = ("NFC", "NFD", "NFKC", "NFKD")


def get_unicode_code(text):
    result = "".join(
        char if ord(char) < 128 else "\\u" + format(ord(char), "x") for char in text
    )
    return result


def _measure_cer(reference: str, transcription: str) -> Tuple[int, int, int, int]:
    """문자열 변환에 필요한 치환, 삭제, 삽입 횟수를 계산합니다.

    :param transcription: 대상 단어로 변환할 소스 문자열
    :param reference: 소스 단어
    :return: a tuple of #hits, #substitutions, #deletions, #insertions
    """

    ref, hyp = [], []

    ref.append(reference)
    hyp.append(transcription)

    cer_s, cer_i, cer_d, cer_n = 0, 0, 0, 0
    sen_err = 0

    for n in range(len(ref)):
        # update CER statistics
        _, (s, i, d) = levenshtein(hyp[n], ref[n])
        cer_s += s
        cer_i += i
        cer_d += d
        cer_n += len(ref[n])

        # update SER statistics
        if s + i + d > 0:
            sen_err += 1

    substitutions = cer_s
    deletions = cer_d
    insertions = cer_i
    hits = len(reference) - (substitutions + deletions)  # correct characters

    return hits, substitutions, deletions, insertions


def _measure_wer(reference: str, transcription: str) -> Tuple[int, int, int, int]:
    """단어열 변환에 필요한 치환, 삭제, 삽입 횟수를 계산합니다.

    :param transcription: 대상 단어
    :param reference: 소스 단어
    :return: a tuple of #hits, #substitutions, #deletions, #insertions
    """

    ref, hyp = [], []

    ref.append(reference)
    hyp.append(transcription)

    wer_s, wer_i, wer_d, wer_n = 0, 0, 0, 0
    sen_err = 0

    for n in range(len(ref)):
        # update WER statistics
        _, (s, i, d) = levenshtein(hyp[n].split(), ref[n].split())
        wer_s += s
        wer_i += i
        wer_d += d
        wer_n += len(ref[n].split())
        # update SER statistics
        if s + i + d > 0:
            sen_err += 1

    substitutions = wer_s
    deletions = wer_d
    insertions = wer_i
    hits = len(reference.split()) - (
        substitutions + deletions
    )  # correct words between refs and trans

    return hits, substitutions, deletions, insertions


def _resolve_rate_mode(rate_mode: str) -> str:
    if not isinstance(rate_mode, str) or rate_mode.lower() not in _RATE_MODES:
        raise ValueError("rate_mode must be 'normalized' or 'standard'")
    return rate_mode.lower()


def _resolve_unicode_normalization(
    unicode_normalization: Optional[str],
) -> Optional[str]:
    if unicode_normalization is None:
        return None
    if not isinstance(unicode_normalization, str):
        raise ValueError("unicode_normalization must be None, NFC, NFD, NFKC, or NFKD")

    normalization_form = unicode_normalization.upper()
    if normalization_form not in _UNICODE_NORMALIZATION_FORMS:
        raise ValueError("unicode_normalization must be None, NFC, NFD, NFKC, or NFKD")
    return normalization_form


def _normalize_unicode(text: str, unicode_normalization: Optional[str]) -> str:
    normalization_form = _resolve_unicode_normalization(unicode_normalization)
    if normalization_form is None:
        return text
    return unicodedata.normalize(normalization_form, text)


def _calculate_error_rate(
    substitutions: int,
    deletions: int,
    insertions: int,
    hits: int,
    rate_mode: str = "normalized",
) -> float:
    rate_mode = _resolve_rate_mode(rate_mode)
    incorrect = substitutions + deletions + insertions
    if rate_mode == "normalized":
        denominator = substitutions + deletions + insertions + hits
    else:
        denominator = substitutions + deletions + hits

    if denominator == 0:
        # Standard CER/WER treats every hypothesis token as an insertion when
        # the reference is empty. The normalized mode already has I in its denominator.
        if rate_mode == "standard" and insertions:
            return float(insertions)
        return 0.0
    return incorrect / denominator


def _calculate_normalized_error_rate(
    substitutions: int, deletions: int, insertions: int, hits: int
) -> float:
    return _calculate_error_rate(
        substitutions, deletions, insertions, hits, rate_mode="normalized"
    )


def _preprocess_cer_text(
    text: str,
    rm_punctuation: bool,
    unicode_normalization: Optional[str] = None,
) -> str:
    text = _normalize_unicode(text, unicode_normalization)
    text = jiwer.RemoveWhiteSpace(replace_by_space=False)(text)
    if rm_punctuation:
        text = jiwer.RemovePunctuation()(text)
    return text


def _preprocess_wer_text(
    text: str,
    rm_punctuation: bool,
    unicode_normalization: Optional[str] = None,
) -> str:
    text = _normalize_unicode(text, unicode_normalization)
    if rm_punctuation:
        text = jiwer.RemovePunctuation()(text)
    return text


def get_cer(
    reference: str,
    transcription: str,
    rm_punctuation: bool = True,
    *,
    rate_mode: str = "normalized",
    unicode_normalization: Optional[str] = None,
) -> MetricResult:
    """Calculate character error rate for one reference/hypothesis pair.

    ``rate_mode="normalized"`` is the historical Nlptutti behavior and remains
    the default for backward compatibility. Use ``rate_mode="standard"`` to
    divide by the reference length, which can produce a value greater than 1.
    """
    rate_mode = _resolve_rate_mode(rate_mode)
    unicode_normalization = _resolve_unicode_normalization(unicode_normalization)
    refs = _preprocess_cer_text(reference, rm_punctuation, unicode_normalization)
    trans = _preprocess_cer_text(transcription, rm_punctuation, unicode_normalization)

    [hits, cer_s, cer_d, cer_i] = _measure_cer(refs, trans)

    substitutions = cer_s
    deletions = cer_d
    insertions = cer_i
    cer = _calculate_error_rate(
        substitutions, deletions, insertions, hits, rate_mode=rate_mode
    )
    result = {
        "cer": cer,
        "substitutions": substitutions,
        "deletions": deletions,
        "insertions": insertions,
    }

    return result


def get_wer(
    reference: str,
    transcription: str,
    rm_punctuation: bool = True,
    *,
    rate_mode: str = "normalized",
    unicode_normalization: Optional[str] = None,
) -> MetricResult:
    """Calculate word error rate for one reference/hypothesis pair."""
    rate_mode = _resolve_rate_mode(rate_mode)
    unicode_normalization = _resolve_unicode_normalization(unicode_normalization)
    refs = _preprocess_wer_text(reference, rm_punctuation, unicode_normalization)
    trans = _preprocess_wer_text(transcription, rm_punctuation, unicode_normalization)
    [hits, wer_s, wer_d, wer_i] = _measure_wer(refs, trans)

    substitutions = wer_s
    deletions = wer_d
    insertions = wer_i

    wer = _calculate_error_rate(
        substitutions, deletions, insertions, hits, rate_mode=rate_mode
    )
    result = {
        "wer": wer,
        "substitutions": substitutions,
        "deletions": deletions,
        "insertions": insertions,
    }

    return result


def get_crr(
    reference: str,
    transcription: str,
    rm_punctuation: bool = True,
    *,
    rate_mode: str = "normalized",
    unicode_normalization: Optional[str] = None,
) -> MetricResult:
    """
    1 - CER 으로, Character의 error율이 아닌 정답률을 계산
    :param transcription: 대상 단어로 변환할 소스 문자열
    :param reference: 소스 단어
    :return: Boolean
    """
    rate_mode = _resolve_rate_mode(rate_mode)
    unicode_normalization = _resolve_unicode_normalization(unicode_normalization)
    refs = _preprocess_cer_text(reference, rm_punctuation, unicode_normalization)
    trans = _preprocess_cer_text(transcription, rm_punctuation, unicode_normalization)

    [hits, cer_s, cer_d, cer_i] = _measure_cer(refs, trans)

    substitutions = cer_s
    deletions = cer_d
    insertions = cer_i
    cer = _calculate_error_rate(
        substitutions, deletions, insertions, hits, rate_mode=rate_mode
    )
    crr = round(1 - cer, 2)
    result = {
        "crr": crr,
        "substitutions": substitutions,
        "deletions": deletions,
        "insertions": insertions,
    }
    return result


def _coerce_sentence_pairs(
    reference_sentences: Iterable[str],
    hypothesis_sentences: Iterable[str],
) -> Tuple[List[str], List[str]]:
    if isinstance(reference_sentences, (str, bytes)) or isinstance(
        hypothesis_sentences, (str, bytes)
    ):
        raise TypeError(
            "reference_sentences and hypothesis_sentences must be iterables of strings"
        )

    references = list(reference_sentences)
    hypotheses = list(hypothesis_sentences)
    if len(references) != len(hypotheses):
        raise ValueError(
            "reference_sentences and hypothesis_sentences must have the same length"
        )
    if not references:
        raise ValueError(
            "reference_sentences and hypothesis_sentences must not be empty"
        )
    if not all(isinstance(sentence, str) for sentence in references + hypotheses):
        raise TypeError("every reference and hypothesis sentence must be a string")
    return references, hypotheses


def _summarize_measurements(
    measurements: Sequence[Tuple[int, int, int, int]],
    rate_mode: str,
) -> Dict[str, Union[float, int]]:
    hits = sum(measurement[0] for measurement in measurements)
    substitutions = sum(measurement[1] for measurement in measurements)
    deletions = sum(measurement[2] for measurement in measurements)
    insertions = sum(measurement[3] for measurement in measurements)
    rates = [
        _calculate_error_rate(s, d, i, h, rate_mode) for h, s, d, i in measurements
    ]
    return {
        "micro": _calculate_error_rate(
            substitutions, deletions, insertions, hits, rate_mode
        ),
        "macro": sum(rates) / len(rates),
        "hits": hits,
        "substitutions": substitutions,
        "deletions": deletions,
        "insertions": insertions,
    }


def evaluate_corpus(
    reference_sentences: Iterable[str],
    hypothesis_sentences: Iterable[str],
    rm_punctuation: bool = True,
    *,
    rate_mode: str = "normalized",
    unicode_normalization: Optional[str] = None,
) -> Dict[str, object]:
    """Evaluate CER and WER over aligned sentence collections.

    ``micro`` aggregates edit counts before calculating the rate. ``macro`` is
    the unweighted average of sentence-level rates. The normalized historical
    Nlptutti rate remains the default.
    """
    references, hypotheses = _coerce_sentence_pairs(
        reference_sentences, hypothesis_sentences
    )
    rate_mode = _resolve_rate_mode(rate_mode)
    unicode_normalization = _resolve_unicode_normalization(unicode_normalization)

    cer_measurements = []
    wer_measurements = []
    sentence_errors = 0
    for reference, hypothesis in zip(references, hypotheses):
        cer_reference = _preprocess_cer_text(
            reference, rm_punctuation, unicode_normalization
        )
        cer_hypothesis = _preprocess_cer_text(
            hypothesis, rm_punctuation, unicode_normalization
        )
        cer_measurement = _measure_cer(cer_reference, cer_hypothesis)
        cer_measurements.append(cer_measurement)
        if sum(cer_measurement[1:]) > 0:
            sentence_errors += 1

        wer_reference = _preprocess_wer_text(
            reference, rm_punctuation, unicode_normalization
        )
        wer_hypothesis = _preprocess_wer_text(
            hypothesis, rm_punctuation, unicode_normalization
        )
        wer_measurements.append(_measure_wer(wer_reference, wer_hypothesis))

    utterances = len(references)
    return {
        "utterances": utterances,
        "rate_mode": rate_mode,
        "unicode_normalization": unicode_normalization,
        "cer": _summarize_measurements(cer_measurements, rate_mode),
        "wer": _summarize_measurements(wer_measurements, rate_mode),
        "perfect_sentences": utterances - sentence_errors,
        "sentence_error_rate": sentence_errors / utterances,
    }


def _align_sequences(
    reference: Sequence[str], hypothesis: Sequence[str]
) -> List[Dict[str, str]]:
    """Return an edit path using the same tie-breaking order as ``levenshtein``."""
    reference_length = len(reference)
    hypothesis_length = len(hypothesis)
    costs = [[0] * (hypothesis_length + 1) for _ in range(reference_length + 1)]
    backtrace = [[None] * (hypothesis_length + 1) for _ in range(reference_length + 1)]

    for ref_index in range(1, reference_length + 1):
        costs[ref_index][0] = ref_index
        backtrace[ref_index][0] = "delete"
    for hyp_index in range(1, hypothesis_length + 1):
        costs[0][hyp_index] = hyp_index
        backtrace[0][hyp_index] = "insert"

    for ref_index in range(1, reference_length + 1):
        for hyp_index in range(1, hypothesis_length + 1):
            is_equal = reference[ref_index - 1] == hypothesis[hyp_index - 1]
            candidates = [
                (
                    costs[ref_index - 1][hyp_index - 1] + int(not is_equal),
                    "equal" if is_equal else "substitute",
                ),
                (costs[ref_index][hyp_index - 1] + 1, "insert"),
                (costs[ref_index - 1][hyp_index] + 1, "delete"),
            ]
            costs[ref_index][hyp_index], backtrace[ref_index][hyp_index] = min(
                candidates, key=lambda candidate: candidate[0]
            )

    alignment = []
    ref_index = reference_length
    hyp_index = hypothesis_length
    while ref_index > 0 or hyp_index > 0:
        operation = backtrace[ref_index][hyp_index]
        if operation in ("equal", "substitute"):
            alignment.append(
                {
                    "type": operation,
                    "reference": reference[ref_index - 1],
                    "hypothesis": hypothesis[hyp_index - 1],
                }
            )
            ref_index -= 1
            hyp_index -= 1
        elif operation == "insert":
            alignment.append(
                {
                    "type": operation,
                    "reference": "",
                    "hypothesis": hypothesis[hyp_index - 1],
                }
            )
            hyp_index -= 1
        else:
            alignment.append(
                {
                    "type": "delete",
                    "reference": reference[ref_index - 1],
                    "hypothesis": "",
                }
            )
            ref_index -= 1

    alignment.reverse()
    return alignment


def _build_error_frequencies(
    alignment: Sequence[Mapping[str, str]],
) -> Dict[str, List[Dict[str, Union[str, int]]]]:
    substitutions = Counter()
    deletions = Counter()
    insertions = Counter()

    for item in alignment:
        if item["type"] == "substitute":
            substitutions[(item["reference"], item["hypothesis"])] += 1
        elif item["type"] == "delete":
            deletions[item["reference"]] += 1
        elif item["type"] == "insert":
            insertions[item["hypothesis"]] += 1

    return {
        "substitutions": [
            {"reference": reference, "hypothesis": hypothesis, "count": count}
            for (reference, hypothesis), count in sorted(
                substitutions.items(), key=lambda item: (-item[1], item[0])
            )
        ],
        "deletions": [
            {"reference": reference, "count": count}
            for reference, count in sorted(
                deletions.items(), key=lambda item: (-item[1], item[0])
            )
        ],
        "insertions": [
            {"hypothesis": hypothesis, "count": count}
            for hypothesis, count in sorted(
                insertions.items(), key=lambda item: (-item[1], item[0])
            )
        ],
    }


def explain_errors(
    reference: str,
    transcription: str,
    unit: str = "character",
    rm_punctuation: bool = True,
    *,
    rate_mode: str = "normalized",
    unicode_normalization: Optional[str] = None,
) -> Dict[str, object]:
    """Explain substitutions, deletions, and insertions for one text pair."""
    rate_mode = _resolve_rate_mode(rate_mode)
    unicode_normalization = _resolve_unicode_normalization(unicode_normalization)
    normalized_unit = unit.lower() if isinstance(unit, str) else ""

    if normalized_unit in ("character", "char", "cer"):
        metric = "cer"
        resolved_unit = "character"
        processed_reference = _preprocess_cer_text(
            reference, rm_punctuation, unicode_normalization
        )
        processed_hypothesis = _preprocess_cer_text(
            transcription, rm_punctuation, unicode_normalization
        )
        reference_tokens = list(processed_reference)
        hypothesis_tokens = list(processed_hypothesis)
    elif normalized_unit in ("word", "wer"):
        metric = "wer"
        resolved_unit = "word"
        processed_reference = _preprocess_wer_text(
            reference, rm_punctuation, unicode_normalization
        )
        processed_hypothesis = _preprocess_wer_text(
            transcription, rm_punctuation, unicode_normalization
        )
        reference_tokens = processed_reference.split()
        hypothesis_tokens = processed_hypothesis.split()
    else:
        raise ValueError("unit must be 'character' or 'word'")

    alignment = _align_sequences(reference_tokens, hypothesis_tokens)
    hits = sum(item["type"] == "equal" for item in alignment)
    substitutions = sum(item["type"] == "substitute" for item in alignment)
    deletions = sum(item["type"] == "delete" for item in alignment)
    insertions = sum(item["type"] == "insert" for item in alignment)
    rate = _calculate_error_rate(substitutions, deletions, insertions, hits, rate_mode)

    return {
        "metric": metric,
        "unit": resolved_unit,
        "rate_mode": rate_mode,
        "rate": rate,
        "processed_reference": processed_reference,
        "processed_hypothesis": processed_hypothesis,
        "counts": {
            "hits": hits,
            "substitutions": substitutions,
            "deletions": deletions,
            "insertions": insertions,
        },
        "alignment": alignment,
        "error_frequencies": _build_error_frequencies(alignment),
    }


COMPLEX_JOSA = [
    # 단일 조사
    "의",
    "에",
    "에서",
    "도",
    "만",
    "를",
    "을",
    "은",
    "는",
    "이",
    "가",
    "과",
    "와",
    "으로",
    "로",
    "부터",
    "까지",
    "에게",
    "께",
    "한테",
    "밖에",
    "마저",
    "이나",
    "나",
    "며",
    "든지",
    "라도",
    "조차",
    # 복합/결합 조사
    "에서부터",
    "에게서",
    "으로부터",
    "까지도",
    "밖에도",
    "이라도",
    "이나마",
    "라도나",
    "와도",
    "도만",
    "까지도",
    "에도",
    "이나마",
    "라도나",
    "조차도",
    "치고는",
]
COMPLEX_EOMI = [
    "다",
    "니다",
    "합니다",
    "했다",
    "한다",
    "하고",
    "하는데",
    "했었다",
    "한다면",
    "한다니까",
    "하니",
    "하더니",
    "하여도",
    "하더라도",
    "했었지",
    "하려면",
]


def _make_suffix_pattern(
    josa_list: Sequence[str], eomi_list: Optional[Sequence[str]] = None
) -> str:
    suffixes = list(josa_list)
    if eomi_list:
        suffixes.extend(eomi_list)
    escaped_suffixes = [
        re.escape(suffix)
        for suffix in sorted(
            {suffix for suffix in suffixes if suffix}, key=lambda value: -len(value)
        )
    ]
    return "|".join(escaped_suffixes)


def make_keyword_pattern(
    keyword: str,
    josa_list: Optional[Sequence[str]] = None,
    eomi_list: Optional[Sequence[str]] = None,
) -> Pattern:
    """키워드와 조사·어미 목록으로 안전한 정규식 패턴을 생성합니다.

    Args:
        keyword (str): 키워드 문자열
        josa_list (list of str, optional): 조사 리스트. 생략하면 COMPLEX_JOSA 사용
        eomi_list (list of str, optional): 어미 리스트

    Returns:
        re.Pattern: 생성된 정규 표현식 패턴

    1. 키워드의 각 글자 사이에 optional space (\\s*)를 허용합니다.
    2. 조사와 어미를 길이순으로 정렬한 선택 패턴을 붙입니다.
    3. 정규식 특수문자가 포함된 키워드와 접미사도 안전하게 처리합니다.
    4. 긴 단어 내부의 부분문자열은 키워드로 세지 않습니다.
    """
    if not isinstance(keyword, str):
        raise TypeError("keyword must be a string")

    compact_keyword = re.sub(r"\s+", "", keyword)
    if not compact_keyword:
        raise ValueError("keyword must not be empty")

    # 키워드의 각 글자 사이에 optional space (\\s*) 허용
    keyword_pattern = r"\s*".join(re.escape(char) for char in compact_keyword)
    if josa_list is None:
        josa_list = COMPLEX_JOSA
    suffix_pattern = _make_suffix_pattern(josa_list, eomi_list)

    if suffix_pattern:
        full_pattern = (
            rf"(?<![{_KOREAN_TOKEN_CHAR}])"
            rf"{keyword_pattern}"
            rf"(?:\s*(?:{suffix_pattern}))?"
            rf"(?![{_KOREAN_TOKEN_CHAR}])"
        )
    else:
        full_pattern = (
            rf"(?<![{_KOREAN_TOKEN_CHAR}]){keyword_pattern}(?![{_KOREAN_TOKEN_CHAR}])"
        )
    return re.compile(full_pattern)


def _classification_metrics(
    true_positives: int,
    false_positives: int,
    false_negatives: int,
) -> Dict[str, float]:
    precision_denominator = true_positives + false_positives
    recall_denominator = true_positives + false_negatives
    precision = true_positives / precision_denominator if precision_denominator else 0.0
    recall = true_positives / recall_denominator if recall_denominator else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "preservation_rate": recall,
    }


def _prepare_keyword_entries(
    keywords: Union[str, Sequence[str], Mapping[str, Union[str, Sequence[str]]]],
) -> Tuple[List[Tuple[str, Optional[str]]], bool]:
    entries = []
    is_labeled = isinstance(keywords, Mapping)

    if isinstance(keywords, Mapping):
        for label, label_keywords in keywords.items():
            if not isinstance(label, str) or not label.strip():
                raise ValueError("keyword labels must be non-empty strings")
            values = (
                [label_keywords]
                if isinstance(label_keywords, str)
                else list(label_keywords)
            )
            entries.extend((keyword, label.strip()) for keyword in values)
    else:
        values = [keywords] if isinstance(keywords, str) else list(keywords)
        entries.extend((keyword, None) for keyword in values)

    if not entries:
        raise ValueError("keywords must not be empty")

    prepared_entries = []
    canonical_keywords = set()
    for keyword, label in entries:
        if not isinstance(keyword, str):
            raise TypeError("every keyword must be a string")
        display_keyword = keyword.strip()
        canonical_keyword = re.sub(r"\s+", "", display_keyword)
        if not canonical_keyword:
            raise ValueError("keywords must not contain empty values")
        if canonical_keyword in canonical_keywords:
            raise ValueError("keywords must be unique after whitespace normalization")
        canonical_keywords.add(canonical_keyword)
        prepared_entries.append((display_keyword, label))
    return prepared_entries, is_labeled


def _build_keyword_statistics(
    reference_count: int,
    hypothesis_count: int,
    true_positives: int,
    false_positives: int,
    false_negatives: int,
) -> Dict[str, Union[float, int]]:
    statistics = {
        "reference_count": reference_count,
        "hypothesis_count": hypothesis_count,
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
    }
    statistics.update(
        _classification_metrics(true_positives, false_positives, false_negatives)
    )
    return statistics


def evaluate_keywords(
    reference_sentences: Iterable[str],
    hypothesis_sentences: Iterable[str],
    keywords: Union[str, Sequence[str], Mapping[str, Union[str, Sequence[str]]]],
    josa_list: Optional[Sequence[str]] = None,
    eomi_list: Optional[Sequence[str]] = None,
) -> Dict[str, object]:
    """Evaluate keyword mention preservation with optional entity labels.

    Mentions are counted per aligned sentence. Matching counts become true
    positives, missing reference mentions become false negatives, and extra
    hypothesis mentions become false positives. This evaluates a supplied
    keyword list; it does not run an NER model.
    """
    references, hypotheses = _coerce_sentence_pairs(
        reference_sentences, hypothesis_sentences
    )
    entries, is_labeled = _prepare_keyword_entries(keywords)
    resolved_josa = COMPLEX_JOSA if josa_list is None else josa_list
    resolved_eomi = COMPLEX_EOMI if eomi_list is None else eomi_list
    patterns = {
        keyword: make_keyword_pattern(keyword, resolved_josa, resolved_eomi)
        for keyword, _ in entries
    }

    keyword_counts = {
        keyword: {
            "reference_count": 0,
            "hypothesis_count": 0,
            "true_positives": 0,
            "false_positives": 0,
            "false_negatives": 0,
        }
        for keyword, _ in entries
    }

    for reference, hypothesis in zip(references, hypotheses):
        for keyword, pattern in patterns.items():
            reference_count = sum(1 for _ in pattern.finditer(reference))
            hypothesis_count = sum(1 for _ in pattern.finditer(hypothesis))
            true_positives = min(reference_count, hypothesis_count)

            counts = keyword_counts[keyword]
            counts["reference_count"] += reference_count
            counts["hypothesis_count"] += hypothesis_count
            counts["true_positives"] += true_positives
            counts["false_positives"] += max(hypothesis_count - reference_count, 0)
            counts["false_negatives"] += max(reference_count - hypothesis_count, 0)

    keyword_results = {}
    for keyword, label in entries:
        counts = keyword_counts[keyword]
        statistics = _build_keyword_statistics(**counts)
        if is_labeled:
            statistics["label"] = label
        keyword_results[keyword] = statistics

    total_reference = sum(
        result["reference_count"] for result in keyword_results.values()
    )
    total_hypothesis = sum(
        result["hypothesis_count"] for result in keyword_results.values()
    )
    total_true_positives = sum(
        result["true_positives"] for result in keyword_results.values()
    )
    total_false_positives = sum(
        result["false_positives"] for result in keyword_results.values()
    )
    total_false_negatives = sum(
        result["false_negatives"] for result in keyword_results.values()
    )
    summary = _build_keyword_statistics(
        total_reference,
        total_hypothesis,
        total_true_positives,
        total_false_positives,
        total_false_negatives,
    )

    final_result = {"keywords": keyword_results, "summary": summary}
    if is_labeled:
        label_counts = {}
        for keyword, label in entries:
            if label not in label_counts:
                label_counts[label] = {
                    "reference_count": 0,
                    "hypothesis_count": 0,
                    "true_positives": 0,
                    "false_positives": 0,
                    "false_negatives": 0,
                }
            for count_name in label_counts[label]:
                label_counts[label][count_name] += keyword_results[keyword][count_name]
        final_result["labels"] = {
            label: _build_keyword_statistics(**counts)
            for label, counts in label_counts.items()
        }
    return final_result


def calculate_keyword_error_rate_with_pattern(
    reference_sentences, hypothesis_sentences, keywords, josa_list, eomi_list=None
):
    """
    각 키워드별로 등장한 횟수와 오류 횟수를 집계하고, 정확도와 에러율을 계산합니다.
    전체 키워드 통계도 함께 제공합니다.

    Args:
        reference_sentences (list of str): 정답 문장 리스트
        hypothesis_sentences (list of str): STT 결과 문장 리스트
        keywords (list of str): 추적할 키워드 리스트
        josa_list (list of str): 조사 리스트
        eomi_list (list of str, optional): 어미 리스트

    Returns:
        dict: 키워드별 등장·정확·오류 횟수와 전체 오류율
    """
    if len(reference_sentences) != len(hypothesis_sentences):
        raise ValueError(
            "reference_sentences and hypothesis_sentences must have the same length"
        )

    result = {
        kw: {"total": 0, "correct": 0, "errors": 0, "accuracy": 0.0, "error_rate": 0.0}
        for kw in keywords
    }
    patterns = {kw: make_keyword_pattern(kw, josa_list, eomi_list) for kw in keywords}

    for ref, hyp in zip(reference_sentences, hypothesis_sentences):
        for kw, pattern in patterns.items():
            if pattern.search(ref):
                result[kw]["total"] += 1
                if pattern.search(hyp):
                    result[kw]["correct"] += 1
                else:
                    result[kw]["errors"] += 1

    # 개별 키워드 정확도와 에러율 계산
    for kw in keywords:
        if result[kw]["total"] > 0:
            result[kw]["accuracy"] = round(
                result[kw]["correct"] / result[kw]["total"], 4
            )
            result[kw]["error_rate"] = round(
                result[kw]["errors"] / result[kw]["total"], 4
            )
        else:
            result[kw]["accuracy"] = 0.0
            result[kw]["error_rate"] = 0.0

    # 전체 통계 계산
    total_keywords = sum(kw_stats["total"] for kw_stats in result.values())
    correct_keywords = sum(kw_stats["correct"] for kw_stats in result.values())
    incorrect_keywords = sum(kw_stats["errors"] for kw_stats in result.values())
    keyword_error_rate = (
        round(incorrect_keywords / total_keywords, 4) if total_keywords > 0 else 0.0
    )

    # 결과 구조화
    final_result = {
        "keywords": result,
        "summary": {
            "total_keywords": total_keywords,
            "correct_keywords": correct_keywords,
            "incorrect_keywords": incorrect_keywords,
            "keyword_error_rate": keyword_error_rate,
        },
    }

    return final_result
