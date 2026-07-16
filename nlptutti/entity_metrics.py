import re
import string
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
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

from nlptutti.asr_metrics import (
    COMPLEX_EOMI,
    COMPLEX_JOSA,
    _KOREAN_TOKEN_CHAR,
    _build_keyword_statistics,
    _calculate_error_rate,
    _coerce_sentence_pairs,
    _make_suffix_pattern,
    _normalize_unicode,
    _preprocess_cer_text,
    _prepare_keyword_entries,
    _resolve_rate_mode,
    _resolve_unicode_normalization,
)


_MENTION_COUNT_NAMES = (
    "reference_count",
    "hypothesis_count",
    "true_positives",
    "false_positives",
    "false_negatives",
)
_CHARACTER_COUNT_NAMES = (
    "hits",
    "substitutions",
    "deletions",
    "insertions",
)


def _empty_mention_counts() -> Dict[str, int]:
    return {name: 0 for name in _MENTION_COUNT_NAMES}


def _empty_character_counts() -> Dict[str, int]:
    return {name: 0 for name in _CHARACTER_COUNT_NAMES}


@dataclass(frozen=True)
class _EntityDefinition:
    name: str
    label: Optional[str]
    canonical_text: str
    aliases: Tuple[str, ...]
    pattern: Pattern


@dataclass(frozen=True)
class _EntityOccurrence:
    name: str
    label: Optional[str]
    surface: str
    start: int
    end: int


@dataclass
class _OccurrenceScore:
    counts: Dict[str, int] = field(default_factory=_empty_character_counts)
    alignment: List[Dict[str, object]] = field(default_factory=list)


def _compact_surface(surface: str) -> str:
    return re.sub(r"\s+", "", surface)


def _coerce_affixes(values: Sequence[str], name: str) -> List[str]:
    if isinstance(values, (str, bytes)):
        raise TypeError(f"{name} must be a sequence of strings")
    resolved = list(values)
    if not all(isinstance(value, str) for value in resolved):
        raise TypeError(f"every value in {name} must be a string")
    return resolved


def _coerce_alias_values(
    aliases: Union[str, Sequence[str]], entity_name: str
) -> List[str]:
    if isinstance(aliases, str):
        values = [aliases]
    elif isinstance(aliases, bytes) or isinstance(aliases, Mapping):
        raise TypeError(f"aliases for {entity_name!r} must be strings")
    else:
        try:
            values = list(aliases)
        except TypeError as error:
            raise TypeError(f"aliases for {entity_name!r} must be strings") from error
    if not all(isinstance(value, str) for value in values):
        raise TypeError(f"aliases for {entity_name!r} must be strings")
    return values


def _prepare_aliases(
    entries: Sequence[Tuple[str, Optional[str]]],
    aliases: Optional[Mapping[str, Union[str, Sequence[str]]]],
    unicode_normalization: Optional[str],
) -> Dict[str, List[str]]:
    aliases_by_entity = {name: [] for name, _ in entries}
    if aliases is None:
        return aliases_by_entity
    if not isinstance(aliases, Mapping):
        raise TypeError("aliases must be a mapping from entity names to strings")

    for raw_name, raw_aliases in aliases.items():
        if not isinstance(raw_name, str):
            raise TypeError("every aliases key must be an entity name string")
        name = raw_name.strip()
        if name not in aliases_by_entity:
            raise ValueError(f"aliases contains an unknown entity: {raw_name!r}")
        for raw_alias in _coerce_alias_values(raw_aliases, name):
            alias = _normalize_unicode(raw_alias.strip(), unicode_normalization)
            if not alias:
                raise ValueError(f"aliases for {name!r} must not contain empty values")
            aliases_by_entity[name].append(alias)
    return aliases_by_entity


def _validate_surface_ownership(
    canonical_texts: Mapping[str, str],
    aliases_by_entity: Mapping[str, Sequence[str]],
) -> None:
    owners = {}
    for name, canonical_text in canonical_texts.items():
        key = _compact_surface(canonical_text)
        if key in owners:
            raise ValueError(
                "entities must remain unique after Unicode and whitespace normalization"
            )
        owners[key] = name

    for name, aliases in aliases_by_entity.items():
        canonical_key = _compact_surface(canonical_texts[name])
        seen = set()
        for alias in aliases:
            alias_key = _compact_surface(alias)
            if alias_key == canonical_key:
                raise ValueError(
                    f"alias {alias!r} for {name!r} duplicates its canonical form"
                )
            owner = owners.get(alias_key)
            if owner is not None and owner != name:
                raise ValueError(
                    f"alias {alias!r} is ambiguous between {name!r} and {owner!r}"
                )
            if alias_key in seen:
                raise ValueError(f"aliases for {name!r} must be unique")
            seen.add(alias_key)
            owners[alias_key] = name


def _make_entity_pattern(
    surfaces: Sequence[str],
    josa_list: Sequence[str],
    eomi_list: Sequence[str],
) -> Pattern:
    variants = [
        r"\s*".join(re.escape(char) for char in _compact_surface(surface))
        for surface in sorted(
            surfaces,
            key=lambda value: (-len(_compact_surface(value)), value),
        )
    ]
    entity_pattern = "|".join(variants)
    suffix_pattern = _make_suffix_pattern(josa_list, eomi_list)
    suffix = rf"(?:\s*(?:{suffix_pattern}))?" if suffix_pattern else ""
    return re.compile(
        rf"(?<![{_KOREAN_TOKEN_CHAR}])"
        rf"(?P<entity>{entity_pattern})"
        rf"{suffix}"
        rf"(?![{_KOREAN_TOKEN_CHAR}])"
    )


def _prepare_definitions(
    entities: Union[str, Sequence[str], Mapping[str, Union[str, Sequence[str]]]],
    aliases: Optional[Mapping[str, Union[str, Sequence[str]]]],
    josa_list: Sequence[str],
    eomi_list: Sequence[str],
    unicode_normalization: Optional[str],
) -> Tuple[List[_EntityDefinition], bool]:
    entries, is_labeled = _prepare_keyword_entries(entities)
    canonical_texts = {
        name: _normalize_unicode(name, unicode_normalization) for name, _ in entries
    }
    aliases_by_entity = _prepare_aliases(entries, aliases, unicode_normalization)
    _validate_surface_ownership(canonical_texts, aliases_by_entity)

    definitions = [
        _EntityDefinition(
            name=name,
            label=label,
            canonical_text=canonical_texts[name],
            aliases=tuple(aliases_by_entity[name]),
            pattern=_make_entity_pattern(
                (canonical_texts[name],) + tuple(aliases_by_entity[name]),
                josa_list,
                eomi_list,
            ),
        )
        for name, label in entries
    ]
    return definitions, is_labeled


def _select_entity_candidates(
    text: str, definitions: Sequence[_EntityDefinition]
) -> List[Tuple[int, int, int, str]]:
    candidates = []
    for definition_index, definition in enumerate(definitions):
        for match in definition.pattern.finditer(text):
            start, end = match.span("entity")
            candidates.append((start, end, definition_index, match.group("entity")))

    selected = []
    previous_end = -1
    for candidate in sorted(
        candidates,
        key=lambda item: (item[0], -(item[1] - item[0]), item[2]),
    ):
        if candidate[0] >= previous_end:
            selected.append(candidate)
            previous_end = candidate[1]
    return selected


def _canonicalize_mentions(
    text: str,
    definitions: Sequence[_EntityDefinition],
    unicode_normalization: Optional[str],
) -> Tuple[str, List[_EntityOccurrence]]:
    normalized_text = _normalize_unicode(text, unicode_normalization)
    candidates = _select_entity_candidates(normalized_text, definitions)
    pieces = []
    occurrences = []
    source_cursor = 0
    output_length = 0

    for start, end, definition_index, surface in candidates:
        definition = definitions[definition_index]
        prefix = normalized_text[source_cursor:start]
        pieces.extend((prefix, definition.canonical_text))
        output_length += len(prefix)
        occurrence_start = output_length
        output_length += len(definition.canonical_text)
        occurrences.append(
            _EntityOccurrence(
                name=definition.name,
                label=definition.label,
                surface=surface,
                start=occurrence_start,
                end=output_length,
            )
        )
        source_cursor = end

    pieces.append(normalized_text[source_cursor:])
    return "".join(pieces), occurrences


def _preprocess_with_offsets(text: str, rm_punctuation: bool) -> Tuple[str, List[int]]:
    characters = []
    offsets = []
    for offset, character in enumerate(text):
        if character in string.whitespace:
            continue
        if rm_punctuation and unicodedata.category(character).startswith("P"):
            continue
        characters.append(character)
        offsets.append(offset)
    return "".join(characters), offsets


def _align_with_indices(
    reference: Sequence[str], hypothesis: Sequence[str]
) -> List[Dict[str, object]]:
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
                    "reference_index": ref_index - 1,
                    "reference_position": ref_index - 1,
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
                    "reference_index": None,
                    "reference_position": ref_index,
                }
            )
            hyp_index -= 1
        else:
            alignment.append(
                {
                    "type": "delete",
                    "reference": reference[ref_index - 1],
                    "hypothesis": "",
                    "reference_index": ref_index - 1,
                    "reference_position": ref_index - 1,
                }
            )
            ref_index -= 1

    alignment.reverse()
    return alignment


def _map_occurrence_tokens(
    occurrences: Sequence[_EntityOccurrence], offsets: Sequence[int]
) -> Tuple[Dict[int, int], List[Tuple[int, int, int]]]:
    token_to_occurrence = {}
    intervals = []
    for occurrence_index, occurrence in enumerate(occurrences):
        token_indices = [
            token_index
            for token_index, offset in enumerate(offsets)
            if occurrence.start <= offset < occurrence.end
        ]
        if token_indices:
            for token_index in token_indices:
                token_to_occurrence[token_index] = occurrence_index
            intervals.append(
                (min(token_indices), max(token_indices) + 1, occurrence_index)
            )
    return token_to_occurrence, intervals


def _find_insertion_occurrence(
    reference_position: int, intervals: Sequence[Tuple[int, int, int]]
) -> Optional[int]:
    for start, end, occurrence_index in intervals:
        # Boundary insertions stay outside the entity span, as in NE-WER alignment.
        if start < reference_position < end:
            return occurrence_index
    return None


def _group_occurrences(
    definitions: Sequence[_EntityDefinition],
    occurrences: Sequence[_EntityOccurrence],
) -> Dict[str, List[_EntityOccurrence]]:
    grouped = {definition.name: [] for definition in definitions}
    for occurrence in occurrences:
        grouped[occurrence.name].append(occurrence)
    return grouped


def _measure_mentions(
    definitions: Sequence[_EntityDefinition],
    reference_groups: Mapping[str, Sequence[_EntityOccurrence]],
    hypothesis_groups: Mapping[str, Sequence[_EntityOccurrence]],
) -> Dict[str, Dict[str, int]]:
    result = {}
    for definition in definitions:
        name = definition.name
        reference_count = len(reference_groups[name])
        hypothesis_count = len(hypothesis_groups[name])
        true_positives = min(reference_count, hypothesis_count)
        result[name] = {
            "reference_count": reference_count,
            "hypothesis_count": hypothesis_count,
            "true_positives": true_positives,
            "false_positives": max(hypothesis_count - reference_count, 0),
            "false_negatives": max(reference_count - hypothesis_count, 0),
        }
    return result


def _assign_alignment_to_occurrences(
    processed_reference: str,
    processed_hypothesis: str,
    reference_occurrences: Sequence[_EntityOccurrence],
    reference_offsets: Sequence[int],
) -> List[_OccurrenceScore]:
    token_to_occurrence, intervals = _map_occurrence_tokens(
        reference_occurrences, reference_offsets
    )
    scores = [_OccurrenceScore() for _ in reference_occurrences]
    if not scores:
        return scores

    for item in _align_with_indices(
        list(processed_reference), list(processed_hypothesis)
    ):
        reference_index = item["reference_index"]
        if reference_index is not None:
            occurrence_index = token_to_occurrence.get(reference_index)
        elif item["type"] == "insert":
            occurrence_index = _find_insertion_occurrence(
                item["reference_position"], intervals
            )
        else:
            occurrence_index = None
        if occurrence_index is None:
            continue

        score = scores[occurrence_index]
        count_name = {
            "equal": "hits",
            "substitute": "substitutions",
            "delete": "deletions",
            "insert": "insertions",
        }[item["type"]]
        score.counts[count_name] += 1
        score.alignment.append(item)
    return scores


def _make_reference_error(
    sentence_index: int,
    occurrence: _EntityOccurrence,
    score: _OccurrenceScore,
) -> Dict[str, object]:
    reference = "".join(item["reference"] for item in score.alignment)
    hypothesis = "".join(item["hypothesis"] for item in score.alignment)
    result = {
        "sentence_index": sentence_index,
        "type": "omission" if not hypothesis else "misrecognition",
        "entity": occurrence.name,
        "reference": reference,
        "hypothesis": hypothesis,
        "substitutions": score.counts["substitutions"],
        "deletions": score.counts["deletions"],
        "insertions": score.counts["insertions"],
    }
    if occurrence.label is not None:
        result["label"] = occurrence.label
    return result


def _score_reference_occurrences(
    sentence_index: int,
    definitions: Sequence[_EntityDefinition],
    canonical_reference: str,
    canonical_hypothesis: str,
    reference_occurrences: Sequence[_EntityOccurrence],
    rm_punctuation: bool,
    rate_mode: str,
) -> Tuple[
    Dict[str, Dict[str, int]],
    List[float],
    List[Tuple[int, int, Dict[str, object]]],
    Counter,
]:
    processed_reference, reference_offsets = _preprocess_with_offsets(
        canonical_reference, rm_punctuation
    )
    processed_hypothesis, _ = _preprocess_with_offsets(
        canonical_hypothesis, rm_punctuation
    )
    scores = _assign_alignment_to_occurrences(
        processed_reference,
        processed_hypothesis,
        reference_occurrences,
        reference_offsets,
    )
    character_counts = {
        definition.name: _empty_character_counts() for definition in definitions
    }
    occurrence_rates = []
    errors = []
    reported_errors = Counter()

    for occurrence, score in zip(reference_occurrences, scores):
        _merge_counts(character_counts[occurrence.name], score.counts)
        occurrence_rates.append(_character_rate(score.counts, rate_mode))
        if _incorrect_characters(score.counts) == 0:
            continue
        error = _make_reference_error(sentence_index, occurrence, score)
        errors.append((sentence_index, occurrence.start, error))
        reported_errors[occurrence.name] += 1
    return character_counts, occurrence_rates, errors, reported_errors


def _make_unmatched_errors(
    sentence_index: int,
    definitions: Sequence[_EntityDefinition],
    reference_groups: Mapping[str, Sequence[_EntityOccurrence]],
    hypothesis_groups: Mapping[str, Sequence[_EntityOccurrence]],
    reported_errors: Mapping[str, int],
    scorable_texts: Mapping[str, str],
) -> List[Tuple[int, int, Dict[str, object]]]:
    errors = []
    for definition in definitions:
        name = definition.name
        references = reference_groups[name]
        hypotheses = hypothesis_groups[name]
        missing = max(len(references) - len(hypotheses) - reported_errors[name], 0)
        for occurrence in references[-missing:] if missing else []:
            error = {
                "sentence_index": sentence_index,
                "type": "omission",
                "entity": name,
                "reference": scorable_texts[name],
                "hypothesis": "",
                "substitutions": 0,
                "deletions": len(scorable_texts[name]),
                "insertions": 0,
            }
            if definition.label is not None:
                error["label"] = definition.label
            errors.append((sentence_index, occurrence.start, error))

        additions = max(len(hypotheses) - len(references), 0)
        for occurrence in hypotheses[-additions:] if additions else []:
            error = {
                "sentence_index": sentence_index,
                "type": "addition",
                "entity": name,
                "reference": "",
                "hypothesis": occurrence.surface,
                "substitutions": 0,
                "deletions": 0,
                "insertions": len(scorable_texts[name]),
            }
            if definition.label is not None:
                error["label"] = definition.label
            errors.append((sentence_index, occurrence.start, error))
    return errors


def _evaluate_sentence(
    sentence_index: int,
    reference: str,
    hypothesis: str,
    definitions: Sequence[_EntityDefinition],
    scorable_texts: Mapping[str, str],
    rm_punctuation: bool,
    rate_mode: str,
    unicode_normalization: Optional[str],
) -> Tuple[
    Dict[str, Dict[str, int]],
    Dict[str, Dict[str, int]],
    List[float],
    List[Tuple[int, int, Dict[str, object]]],
]:
    canonical_reference, reference_occurrences = _canonicalize_mentions(
        reference, definitions, unicode_normalization
    )
    canonical_hypothesis, hypothesis_occurrences = _canonicalize_mentions(
        hypothesis, definitions, unicode_normalization
    )
    reference_groups = _group_occurrences(definitions, reference_occurrences)
    hypothesis_groups = _group_occurrences(definitions, hypothesis_occurrences)
    mentions = _measure_mentions(definitions, reference_groups, hypothesis_groups)
    characters, rates, errors, reported = _score_reference_occurrences(
        sentence_index,
        definitions,
        canonical_reference,
        canonical_hypothesis,
        reference_occurrences,
        rm_punctuation,
        rate_mode,
    )
    errors.extend(
        _make_unmatched_errors(
            sentence_index,
            definitions,
            reference_groups,
            hypothesis_groups,
            reported,
            scorable_texts,
        )
    )
    return mentions, characters, rates, errors


def _merge_counts(target: Dict[str, int], source: Mapping[str, int]) -> None:
    for name in target:
        target[name] += source[name]


def _incorrect_characters(counts: Mapping[str, int]) -> int:
    return counts["substitutions"] + counts["deletions"] + counts["insertions"]


def _character_rate(counts: Mapping[str, int], rate_mode: str) -> float:
    return _calculate_error_rate(
        counts["substitutions"],
        counts["deletions"],
        counts["insertions"],
        counts["hits"],
        rate_mode,
    )


def _character_statistics(
    counts: Mapping[str, int], rate_mode: str
) -> Dict[str, Union[float, int]]:
    return {
        "cer": _character_rate(counts, rate_mode),
        "hits": counts["hits"],
        "substitutions": counts["substitutions"],
        "deletions": counts["deletions"],
        "insertions": counts["insertions"],
        "reference_characters": (
            counts["hits"] + counts["substitutions"] + counts["deletions"]
        ),
    }


def _aggregate_nested_counts(
    target: Mapping[str, Dict[str, int]],
    source: Mapping[str, Mapping[str, int]],
) -> None:
    for name, counts in source.items():
        _merge_counts(target[name], counts)


def _build_entity_results(
    definitions: Sequence[_EntityDefinition],
    mention_counts: Mapping[str, Mapping[str, int]],
    character_counts: Mapping[str, Mapping[str, int]],
    rate_mode: str,
    is_labeled: bool,
) -> Dict[str, Dict[str, object]]:
    results = {}
    for definition in definitions:
        statistics = _build_keyword_statistics(**mention_counts[definition.name])
        statistics.update(
            _character_statistics(character_counts[definition.name], rate_mode)
        )
        statistics["aliases"] = list(definition.aliases)
        if is_labeled:
            statistics["label"] = definition.label
        results[definition.name] = statistics
    return results


def _sum_nested_counts(
    values: Iterable[Mapping[str, int]], names: Sequence[str]
) -> Dict[str, int]:
    total = {name: 0 for name in names}
    for counts in values:
        _merge_counts(total, counts)
    return total


def _build_label_results(
    definitions: Sequence[_EntityDefinition],
    mention_counts: Mapping[str, Mapping[str, int]],
    character_counts: Mapping[str, Mapping[str, int]],
    rate_mode: str,
) -> Dict[str, Dict[str, object]]:
    label_mentions = {}
    label_characters = {}
    for definition in definitions:
        label = definition.label
        label_mentions.setdefault(label, _empty_mention_counts())
        label_characters.setdefault(label, _empty_character_counts())
        _merge_counts(label_mentions[label], mention_counts[definition.name])
        _merge_counts(label_characters[label], character_counts[definition.name])

    results = {}
    for label, counts in label_mentions.items():
        statistics = _build_keyword_statistics(**counts)
        statistics.update(_character_statistics(label_characters[label], rate_mode))
        results[label] = statistics
    return results


def _build_final_result(
    definitions: Sequence[_EntityDefinition],
    is_labeled: bool,
    mention_counts: Mapping[str, Mapping[str, int]],
    character_counts: Mapping[str, Mapping[str, int]],
    occurrence_rates: Sequence[float],
    error_records: Sequence[Tuple[int, int, Dict[str, object]]],
    rate_mode: str,
    rm_punctuation: bool,
    unicode_normalization: Optional[str],
) -> Dict[str, object]:
    entity_results = _build_entity_results(
        definitions, mention_counts, character_counts, rate_mode, is_labeled
    )
    total_mentions = _sum_nested_counts(mention_counts.values(), _MENTION_COUNT_NAMES)
    total_characters = _sum_nested_counts(
        character_counts.values(), _CHARACTER_COUNT_NAMES
    )
    character_statistics = _character_statistics(total_characters, rate_mode)
    entity_cer = {
        "micro": character_statistics["cer"],
        "macro": (
            sum(occurrence_rates) / len(occurrence_rates) if occurrence_rates else 0.0
        ),
        **{name: character_statistics[name] for name in _CHARACTER_COUNT_NAMES},
        "reference_characters": character_statistics["reference_characters"],
    }
    result = {
        "rate_mode": rate_mode,
        "rm_punctuation": rm_punctuation,
        "unicode_normalization": unicode_normalization,
        "aliases_enabled": any(definition.aliases for definition in definitions),
        "entity_cer": entity_cer,
        "entities": entity_results,
        "summary": _build_keyword_statistics(**total_mentions),
        "errors": [
            record
            for _, _, record in sorted(
                error_records,
                key=lambda item: (item[0], item[1], item[2]["type"]),
            )
        ],
    }
    if is_labeled:
        result["labels"] = _build_label_results(
            definitions, mention_counts, character_counts, rate_mode
        )
    return result


def evaluate_entities(
    reference_sentences: Iterable[str],
    hypothesis_sentences: Iterable[str],
    entities: Union[str, Sequence[str], Mapping[str, Union[str, Sequence[str]]]],
    josa_list: Optional[Sequence[str]] = None,
    eomi_list: Optional[Sequence[str]] = None,
    rm_punctuation: bool = True,
    *,
    aliases: Optional[Mapping[str, Union[str, Sequence[str]]]] = None,
    rate_mode: str = "normalized",
    unicode_normalization: Optional[str] = None,
) -> Dict[str, object]:
    """Evaluate supplied entity names with mention F1 and entity-span CER.

    This function locates supplied entity names; it does not run an NER model.
    Entity CER adapts named-entity WER to characters by counting edits aligned
    to reference entity spans. False-positive mentions outside those spans are
    represented by mention precision/F1 and the ``errors`` list.

    ``rate_mode="normalized"`` preserves the package default. Use
    ``rate_mode="standard"`` for the paper-style denominator: the number of
    reference entity characters.

    Configured aliases are exact accepted forms, not fuzzy matches. They are
    canonicalized before character alignment so an accepted alias is scored as
    a correct entity mention.
    """
    references, hypotheses = _coerce_sentence_pairs(
        reference_sentences, hypothesis_sentences
    )
    rate_mode = _resolve_rate_mode(rate_mode)
    unicode_normalization = _resolve_unicode_normalization(unicode_normalization)
    resolved_josa = _coerce_affixes(
        COMPLEX_JOSA if josa_list is None else josa_list, "josa_list"
    )
    resolved_eomi = _coerce_affixes(
        COMPLEX_EOMI if eomi_list is None else eomi_list, "eomi_list"
    )
    definitions, is_labeled = _prepare_definitions(
        entities,
        aliases,
        resolved_josa,
        resolved_eomi,
        unicode_normalization,
    )
    scorable_texts = {
        definition.name: _preprocess_cer_text(
            definition.canonical_text, rm_punctuation, unicode_normalization=None
        )
        for definition in definitions
    }
    for name, text in scorable_texts.items():
        if not text:
            raise ValueError(
                f"entity {name!r} has no scorable characters after preprocessing"
            )

    mention_counts = {
        definition.name: _empty_mention_counts() for definition in definitions
    }
    character_counts = {
        definition.name: _empty_character_counts() for definition in definitions
    }
    occurrence_rates = []
    error_records = []
    for sentence_index, (reference, hypothesis) in enumerate(
        zip(references, hypotheses)
    ):
        mentions, characters, rates, errors = _evaluate_sentence(
            sentence_index,
            reference,
            hypothesis,
            definitions,
            scorable_texts,
            rm_punctuation,
            rate_mode,
            unicode_normalization,
        )
        _aggregate_nested_counts(mention_counts, mentions)
        _aggregate_nested_counts(character_counts, characters)
        occurrence_rates.extend(rates)
        error_records.extend(errors)

    return _build_final_result(
        definitions,
        is_labeled,
        mention_counts,
        character_counts,
        occurrence_rates,
        error_records,
        rate_mode,
        rm_punctuation,
        unicode_normalization,
    )


__all__ = ["evaluate_entities"]
