from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
from importlib import metadata
from typing import Dict, List, Mapping, Optional, Tuple, Union

from nlptutti.asr_metrics import (
    _resolve_rate_mode,
    _resolve_unicode_normalization,
    get_cer,
    get_crr,
    get_wer,
)

ParsedTranscript = Dict[str, object]
TranscriptInput = Union[str, bytes, Mapping[str, object]]

_FORMAT_ALIASES = {
    "text": "text",
    "txt": "text",
    "json": "json",
    "srt": "srt",
    "tsv": "tsv",
}
_JSON_TEXT_POLICIES = ("text", "segments_fallback")
_JSON_METADATA_FIELDS = ("file", "model", "language", "duration_s")
_SRT_TIMESTAMP = re.compile(
    r"^(?P<start>\d{2,}:\d{2}:\d{2},\d{3})\s*-->\s*"
    r"(?P<end>\d{2,}:\d{2}:\d{2},\d{3})$"
)


class TranscriptFormatError(ValueError):
    """Raised when a structured transcript violates its input contract."""


def _resolve_source_format(source_format: str) -> str:
    if not isinstance(source_format, str):
        raise TypeError("source_format must be a string")
    resolved = _FORMAT_ALIASES.get(source_format.lower())
    if resolved is None:
        raise ValueError("source_format must be text, txt, json, srt, or tsv")
    return resolved


def _decode_text(data: Union[str, bytes], source_format: str) -> str:
    if isinstance(data, str):
        return data.lstrip("\ufeff")
    if isinstance(data, bytes):
        try:
            return data.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise TranscriptFormatError(
                f"{source_format} transcript must be valid UTF-8"
            ) from error
    raise TypeError(f"{source_format} transcript must be str or bytes")


def _normalize_segment_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _validate_number(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TranscriptFormatError(f"{field_name} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise TranscriptFormatError(f"{field_name} must be a finite number")
    if number < 0:
        raise TranscriptFormatError(f"{field_name} must not be negative")
    return number


def _validate_json_metadata(document: Mapping[str, object]) -> Dict[str, object]:
    result = {}
    for field_name in _JSON_METADATA_FIELDS:
        if field_name not in document:
            continue
        value = document[field_name]
        if field_name == "duration_s":
            _validate_number(value, "JSON duration_s")
        elif not isinstance(value, str):
            raise TranscriptFormatError(f"JSON {field_name} must be a string")
        result[field_name] = value
    return result


def _parse_json_segments(
    segments: object,
) -> Tuple[List[str], List[Dict[str, object]]]:
    if not isinstance(segments, list):
        raise TranscriptFormatError("JSON segments must be a list")

    texts = []
    timestamps = []
    timed_segments = 0
    for index, segment in enumerate(segments):
        if not isinstance(segment, Mapping):
            raise TranscriptFormatError(f"JSON segments[{index}] must be an object")
        segment_text = segment.get("text")
        if not isinstance(segment_text, str):
            raise TranscriptFormatError(f"JSON segments[{index}].text must be a string")
        texts.append(_normalize_segment_text(segment_text))

        has_start = "start" in segment
        has_end = "end" in segment
        if has_start != has_end:
            raise TranscriptFormatError(
                f"JSON segments[{index}] must provide start and end together"
            )
        if has_start:
            start = _validate_number(segment["start"], f"JSON segments[{index}].start")
            end = _validate_number(segment["end"], f"JSON segments[{index}].end")
            if end < start:
                raise TranscriptFormatError(
                    f"JSON segments[{index}].end must not precede start"
                )
            timestamps.append({"start": segment["start"], "end": segment["end"]})
            timed_segments += 1

    if timed_segments not in (0, len(segments)):
        raise TranscriptFormatError(
            "JSON segments must either all include timestamps or all omit them"
        )
    return texts, timestamps


def _parse_json(
    data: TranscriptInput,
    json_text_policy: str,
) -> ParsedTranscript:
    if json_text_policy not in _JSON_TEXT_POLICIES:
        raise ValueError("json_text_policy must be 'text' or 'segments_fallback'")

    if isinstance(data, Mapping):
        document = data
    else:
        serialized = _decode_text(data, "JSON")
        try:
            document = json.loads(serialized)
        except json.JSONDecodeError as error:
            raise TranscriptFormatError(
                f"invalid JSON transcript at line {error.lineno}, column {error.colno}"
            ) from error

    if not isinstance(document, Mapping):
        raise TranscriptFormatError("JSON transcript must be an object")

    has_text = "text" in document
    if has_text and not isinstance(document["text"], str):
        raise TranscriptFormatError("JSON text must be a string")

    segment_texts = []
    timestamps = []
    segments = document.get("segments")
    if "segments" in document:
        segment_texts, timestamps = _parse_json_segments(segments)

    if has_text:
        transcript_text = document["text"]
        text_source = "top_level_text"
    elif json_text_policy == "segments_fallback" and "segments" in document:
        transcript_text = " ".join(text for text in segment_texts if text)
        text_source = "segments"
    else:
        raise TranscriptFormatError(
            "JSON transcript requires a top-level text string; use "
            "json_text_policy='segments_fallback' to join segment text explicitly"
        )

    provenance = {
        "json_text_policy": json_text_policy,
        "text_source": text_source,
    }
    metadata_fields = _validate_json_metadata(document)
    if metadata_fields:
        provenance["metadata"] = metadata_fields
    if "segments" in document:
        provenance["segment_count"] = len(segments)
    if timestamps:
        # FunASR's JSON example does not state the timestamp unit, so values stay raw.
        provenance["timestamps"] = timestamps

    return {
        "source_format": "json",
        "text": transcript_text,
        "provenance": provenance,
    }


def _srt_timecode_milliseconds(value: str) -> int:
    hours, minutes, remainder = value.split(":")
    seconds, milliseconds = remainder.split(",")
    minute_value = int(minutes)
    second_value = int(seconds)
    if minute_value >= 60 or second_value >= 60:
        raise TranscriptFormatError(f"invalid SRT timestamp: {value}")
    return (
        int(hours) * 3_600_000
        + minute_value * 60_000
        + second_value * 1_000
        + int(milliseconds)
    )


def _parse_srt(data: Union[str, bytes]) -> ParsedTranscript:
    serialized = _decode_text(data, "SRT")
    lines = serialized.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    position = 0
    cue_texts = []
    timestamps = []

    while position < len(lines):
        while position < len(lines) and not lines[position].strip():
            position += 1
        if position >= len(lines):
            break

        if lines[position].strip().isdigit():
            position += 1
            if position >= len(lines):
                raise TranscriptFormatError(
                    "SRT cue index must be followed by timestamps"
                )

        timestamp_line = lines[position].strip()
        timestamp_match = _SRT_TIMESTAMP.fullmatch(timestamp_line)
        if timestamp_match is None:
            raise TranscriptFormatError(
                f"invalid SRT timestamp line: {timestamp_line!r}"
            )
        start = timestamp_match.group("start")
        end = timestamp_match.group("end")
        if _srt_timecode_milliseconds(end) < _srt_timecode_milliseconds(start):
            raise TranscriptFormatError("SRT cue end must not precede start")
        position += 1

        text_lines = []
        while position < len(lines) and lines[position].strip():
            if _SRT_TIMESTAMP.fullmatch(lines[position].strip()):
                raise TranscriptFormatError(
                    "SRT cues must be separated by a blank line"
                )
            text_lines.append(lines[position])
            position += 1
        cue_text = _normalize_segment_text(" ".join(text_lines))
        if not cue_text:
            raise TranscriptFormatError("SRT cue text must not be empty")
        cue_texts.append(cue_text)
        timestamps.append({"start": start, "end": end})

    if not cue_texts:
        raise TranscriptFormatError("SRT transcript must contain at least one cue")

    return {
        "source_format": "srt",
        "text": " ".join(cue_texts),
        "provenance": {
            "segment_count": len(cue_texts),
            "text_source": "cue_text",
            "timestamp_unit": "srt_timecode",
            "timestamps": timestamps,
        },
    }


def _parse_tsv_time(value: str, field_name: str) -> float:
    try:
        number = float(value)
    except ValueError as error:
        raise TranscriptFormatError(f"{field_name} must be a finite number") from error
    if not math.isfinite(number):
        raise TranscriptFormatError(f"{field_name} must be a finite number")
    if number < 0:
        raise TranscriptFormatError(f"{field_name} must not be negative")
    return number


def _parse_tsv(data: Union[str, bytes]) -> ParsedTranscript:
    serialized = _decode_text(data, "TSV")
    try:
        reader = csv.DictReader(
            io.StringIO(serialized, newline=""),
            delimiter="\t",
            strict=True,
        )
        fieldnames = reader.fieldnames
        if fieldnames is None:
            raise TranscriptFormatError("TSV transcript requires a header row")
        if len(fieldnames) != len(set(fieldnames)):
            raise TranscriptFormatError("TSV transcript headers must be unique")
        missing = [name for name in ("start", "end", "text") if name not in fieldnames]
        if missing:
            raise TranscriptFormatError(
                "TSV transcript is missing required header(s): " + ", ".join(missing)
            )

        segment_texts = []
        timestamps = []
        for row_number, row in enumerate(reader, start=2):
            if all(value in (None, "") for value in row.values()):
                continue
            if None in row or any(row[name] is None for name in fieldnames):
                raise TranscriptFormatError(
                    f"TSV row {row_number} has the wrong number of columns"
                )
            start_text = row["start"].strip()
            end_text = row["end"].strip()
            start = _parse_tsv_time(start_text, f"TSV row {row_number} start")
            end = _parse_tsv_time(end_text, f"TSV row {row_number} end")
            if end < start:
                raise TranscriptFormatError(
                    f"TSV row {row_number} end must not precede start"
                )
            segment_texts.append(_normalize_segment_text(row["text"]))
            timestamps.append({"start": start_text, "end": end_text})
    except csv.Error as error:
        raise TranscriptFormatError(f"invalid TSV transcript: {error}") from error

    if not timestamps:
        raise TranscriptFormatError("TSV transcript must contain at least one data row")

    return {
        "source_format": "tsv",
        "text": " ".join(text for text in segment_texts if text),
        "provenance": {
            "segment_count": len(segment_texts),
            "text_source": "text_column",
            "timestamp_unit": "seconds",
            "timestamps": timestamps,
        },
    }


def parse_transcript(
    data: TranscriptInput,
    source_format: str,
    *,
    json_text_policy: str = "text",
) -> ParsedTranscript:
    """Parse text or a structured STT result without running an STT model.

    ``source_format`` accepts ``text``/``txt``, ``json``, ``srt``, or ``tsv``.
    JSON uses its top-level ``text`` field by default. Segment joining is only
    enabled with ``json_text_policy="segments_fallback"``. SRT and TSV segment
    text is joined with one ASCII space, while timestamps are kept in
    provenance and never included in the evaluated text.
    """

    resolved_format = _resolve_source_format(source_format)
    if resolved_format == "json":
        return _parse_json(data, json_text_policy)
    if isinstance(data, Mapping):
        raise TypeError(f"{resolved_format} transcript must be str or bytes")
    if resolved_format == "srt":
        return _parse_srt(data)
    if resolved_format == "tsv":
        return _parse_tsv(data)
    return {
        "source_format": "text",
        "text": _decode_text(data, "text"),
        "provenance": {},
    }


def _copy_json_value(value: object, field_name: str) -> object:
    try:
        serialized = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
        )
    except (TypeError, ValueError) as error:
        raise TypeError(
            f"{field_name} must contain JSON-serializable values"
        ) from error
    return json.loads(serialized)


def _text_fingerprint(text: str) -> Dict[str, object]:
    encoded = text.encode("utf-8")
    return {
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "character_count": len(text),
        "byte_count": len(encoded),
    }


def _metric_entry(
    result: Mapping[str, Union[float, int]], value_key: str
) -> Dict[str, object]:
    return {
        "value": result[value_key],
        "substitutions": result["substitutions"],
        "deletions": result["deletions"],
        "insertions": result["insertions"],
    }


def _package_version() -> str:
    try:
        return metadata.version("nlptutti")
    except metadata.PackageNotFoundError:
        return "unknown"


def evaluate_transcript(
    reference: str,
    transcript: Mapping[str, object],
    rm_punctuation: bool = True,
    *,
    rate_mode: str = "normalized",
    unicode_normalization: Optional[str] = None,
) -> Dict[str, object]:
    """Evaluate a parsed transcript and return a versioned, JSON-safe report."""

    if not isinstance(reference, str):
        raise TypeError("reference must be a string")
    if not isinstance(transcript, Mapping):
        raise TypeError("transcript must be the mapping returned by parse_transcript")
    if not isinstance(rm_punctuation, bool):
        raise TypeError("rm_punctuation must be a boolean")

    source_format = _resolve_source_format(transcript.get("source_format"))
    hypothesis = transcript.get("text")
    if not isinstance(hypothesis, str):
        raise TypeError("transcript text must be a string")
    raw_provenance = transcript.get("provenance", {})
    if not isinstance(raw_provenance, Mapping):
        raise TypeError("transcript provenance must be a mapping")
    source_provenance = _copy_json_value(dict(raw_provenance), "transcript provenance")

    resolved_rate_mode = _resolve_rate_mode(rate_mode)
    resolved_unicode_normalization = _resolve_unicode_normalization(
        unicode_normalization
    )
    metric_arguments = {
        "rm_punctuation": rm_punctuation,
        "rate_mode": resolved_rate_mode,
        "unicode_normalization": resolved_unicode_normalization,
    }
    cer = get_cer(reference, hypothesis, **metric_arguments)
    wer = get_wer(reference, hypothesis, **metric_arguments)
    crr = get_crr(reference, hypothesis, **metric_arguments)

    source = {"format": source_format}
    if source_provenance:
        source["details"] = source_provenance

    return {
        "schema_version": "1.0",
        "evaluator": {"name": "nlptutti", "version": _package_version()},
        "options": {
            "rate_mode": resolved_rate_mode,
            "rm_punctuation": rm_punctuation,
            "unicode_normalization": resolved_unicode_normalization,
        },
        "metrics": {
            "cer": _metric_entry(cer, "cer"),
            "wer": _metric_entry(wer, "wer"),
            "crr": _metric_entry(crr, "crr"),
        },
        "provenance": {
            "source": source,
            "reference": _text_fingerprint(reference),
            "hypothesis": _text_fingerprint(hypothesis),
        },
    }
