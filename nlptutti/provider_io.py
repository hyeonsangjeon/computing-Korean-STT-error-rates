"""Strict, dependency-free adapters for stored STT provider output."""

from __future__ import annotations

import json
import math
from typing import Dict, List, Mapping, Union

from nlptutti.transcript_io import TranscriptFormatError


ProviderInput = Union[str, bytes, Mapping[str, object]]

_SUPPORTED_SCHEMAS = {
    "azure-speech": ("short-audio-simple-v1",),
    "openai-whisper": ("transcribe-v1",),
}


def _load_document(payload: ProviderInput, provider: str) -> Mapping[str, object]:
    if isinstance(payload, Mapping):
        return payload
    if isinstance(payload, bytes):
        try:
            serialized = payload.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise TranscriptFormatError(
                "{} payload must be valid UTF-8".format(provider)
            ) from error
    elif isinstance(payload, str):
        serialized = payload.lstrip("\ufeff")
    else:
        raise TypeError("provider payload must be a mapping, str, or bytes")

    try:
        document = json.loads(serialized)
    except json.JSONDecodeError as error:
        raise TranscriptFormatError(
            "invalid {} JSON at line {}, column {}".format(
                provider, error.lineno, error.colno
            )
        ) from error
    if not isinstance(document, Mapping):
        raise TranscriptFormatError("{} payload must be a JSON object".format(provider))
    return document


def _non_negative_number(value: object, field_name: str) -> Union[int, float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TranscriptFormatError("{} must be a finite number".format(field_name))
    if not math.isfinite(float(value)):
        raise TranscriptFormatError("{} must be a finite number".format(field_name))
    if value < 0:
        raise TranscriptFormatError("{} must not be negative".format(field_name))
    return value


def _non_negative_integer(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TranscriptFormatError("{} must be an integer".format(field_name))
    if value < 0:
        raise TranscriptFormatError("{} must not be negative".format(field_name))
    return value


def _parse_azure_short_audio(document: Mapping[str, object]) -> Dict[str, object]:
    status = document.get("RecognitionStatus")
    if not isinstance(status, str):
        raise TranscriptFormatError("azure-speech RecognitionStatus must be a string")
    if status != "Success":
        raise TranscriptFormatError(
            "azure-speech recognition did not succeed: {}".format(status)
        )

    text = document.get("DisplayText")
    if not isinstance(text, str):
        raise TranscriptFormatError(
            "azure-speech successful response requires DisplayText"
        )

    has_offset = "Offset" in document
    has_duration = "Duration" in document
    if has_offset != has_duration:
        raise TranscriptFormatError(
            "azure-speech Offset and Duration must be provided together"
        )

    provenance: Dict[str, object] = {
        "provider": "azure-speech",
        "provider_schema": "short-audio-simple-v1",
        "recognition_status": status,
        "text_source": "DisplayText",
    }
    if has_offset:
        provenance["timing"] = {
            "offset": _non_negative_integer(document["Offset"], "azure-speech Offset"),
            "duration": _non_negative_integer(
                document["Duration"], "azure-speech Duration"
            ),
            "unit": "100ns_tick",
        }

    return {"source_format": "json", "text": text, "provenance": provenance}


def _parse_whisper(document: Mapping[str, object]) -> Dict[str, object]:
    text = document.get("text")
    if not isinstance(text, str):
        raise TranscriptFormatError("openai-whisper text must be a string")

    language = document.get("language")
    if not isinstance(language, str) or not language:
        raise TranscriptFormatError(
            "openai-whisper language must be a non-empty string"
        )

    segments = document.get("segments")
    if not isinstance(segments, list):
        raise TranscriptFormatError("openai-whisper segments must be a list")

    timestamps: List[Dict[str, object]] = []
    for index, segment in enumerate(segments):
        if not isinstance(segment, Mapping):
            raise TranscriptFormatError(
                "openai-whisper segments[{}] must be an object".format(index)
            )
        if not isinstance(segment.get("text"), str):
            raise TranscriptFormatError(
                "openai-whisper segments[{}].text must be a string".format(index)
            )
        start = _non_negative_number(
            segment.get("start"),
            "openai-whisper segments[{}].start".format(index),
        )
        end = _non_negative_number(
            segment.get("end"),
            "openai-whisper segments[{}].end".format(index),
        )
        if end < start:
            raise TranscriptFormatError(
                "openai-whisper segments[{}].end must not precede start".format(index)
            )
        timestamps.append({"start": start, "end": end})

    metadata: Dict[str, object] = {"language": language}
    if "model" in document:
        if not isinstance(document["model"], str):
            raise TranscriptFormatError("openai-whisper model must be a string")
        metadata["model"] = document["model"]
    if "duration_s" in document:
        metadata["duration_s"] = _non_negative_number(
            document["duration_s"], "openai-whisper duration_s"
        )

    provenance: Dict[str, object] = {
        "provider": "openai-whisper",
        "provider_schema": "transcribe-v1",
        "text_source": "text",
        "segment_count": len(segments),
        "metadata": metadata,
    }
    if timestamps:
        provenance["timestamps"] = timestamps
        provenance["timestamp_unit"] = "seconds"

    return {"source_format": "json", "text": text, "provenance": provenance}


def parse_provider_transcript(
    payload: ProviderInput,
    provider: str,
    *,
    schema_version: str,
) -> Dict[str, object]:
    """Convert one explicitly selected provider schema to a parsed transcript.

    This function reads an already stored JSON response. It does not call a
    provider SDK, use credentials, run a model, or infer the provider/schema.
    """

    if not isinstance(provider, str):
        raise TypeError("provider must be a string")
    if not isinstance(schema_version, str):
        raise TypeError("schema_version must be a string")
    schemas = _SUPPORTED_SCHEMAS.get(provider)
    if schemas is None:
        raise ValueError(
            "provider must be one of: {}".format(", ".join(_SUPPORTED_SCHEMAS))
        )
    if schema_version not in schemas:
        raise ValueError(
            "unsupported schema_version for {}: {}; expected {}".format(
                provider, schema_version, ", ".join(schemas)
            )
        )

    document = _load_document(payload, provider)
    if provider == "azure-speech":
        return _parse_azure_short_audio(document)
    return _parse_whisper(document)


__all__ = ["ProviderInput", "parse_provider_transcript"]
