"""Explicit, offline file manifests for the existing comparison pipeline."""

import hashlib
from pathlib import Path
from typing import Any, Dict, Mapping, Tuple, cast

from nlptutti._json import load_json
from nlptutti.provider_io import parse_provider_transcript
from nlptutti.transcript_io import parse_transcript

MANIFEST_SCHEMA = "nlptutti.manifest/1.0"


def read_json_file(path: Path) -> Any:
    try:
        return load_json(path.read_text(encoding="utf-8-sig"))
    except UnicodeDecodeError as error:
        raise ValueError("{} must be valid UTF-8".format(path.name)) from error


def load_evaluation_config(path: Path) -> Dict[str, Any]:
    document = read_json_file(path)
    if not isinstance(document, Mapping) or not document:
        raise ValueError("evaluation config must be a non-empty object")
    allowed = {"keywords", "entities", "entity_aliases"}
    if set(document) - allowed:
        raise ValueError(
            "evaluation config only accepts keywords, entities, entity_aliases"
        )
    return dict(document)


def _files(values: object, directory: Path, field: str) -> Tuple[Dict[str, str], list]:
    if not isinstance(values, list) or not values:
        raise ValueError(field + " must be a non-empty list of files")
    texts: Dict[str, str] = {}
    sources: Dict[str, Dict[str, object]] = {}
    for index, value in enumerate(values):
        prefix = "{}[{}]".format(field, index)
        if not isinstance(value, Mapping):
            raise ValueError(prefix + " must be an object")
        allowed = {
            "id",
            "path",
            "source_format",
            "provider",
            "schema_version",
            "json_text_policy",
        }
        if set(value) - allowed:
            raise ValueError(prefix + " contains unsupported fields")
        for key in ("id", "path", "source_format"):
            if not isinstance(value.get(key), str) or not value[key].strip():
                raise ValueError(prefix + "." + key + " must be a non-empty string")
        item_id = value["id"]
        if item_id in texts:
            raise ValueError(prefix + ".id must be unique")
        path = directory / value["path"]
        if value["source_format"] not in ("text", "json", "srt", "tsv"):
            raise ValueError(prefix + ".source_format must be text, json, srt, or tsv")
        provider = value.get("provider")
        if "provider" in value:
            if not isinstance(provider, str) or not provider:
                raise ValueError(prefix + ".provider must be a non-empty string")
            if value["source_format"] != "json" or "json_text_policy" in value:
                raise ValueError(
                    prefix + " provider files require JSON without json_text_policy"
                )
            if "schema_version" not in value:
                raise ValueError(prefix + ".schema_version is required for a provider")
        elif "schema_version" in value:
            raise ValueError(prefix + ".schema_version requires provider")
        if "json_text_policy" in value and value["source_format"] != "json":
            raise ValueError(prefix + ".json_text_policy requires JSON")
        payload = path.read_bytes()
        if provider is not None:
            parsed = parse_provider_transcript(
                payload, provider, schema_version=value["schema_version"]
            )
        else:
            parsed = parse_transcript(
                payload,
                value["source_format"],
                json_text_policy=value.get("json_text_policy", "text"),
            )
        texts[item_id] = cast(str, parsed["text"])
        source: Dict[str, object] = {
            "source_format": parsed["source_format"],
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        if provider is not None:
            source.update(provider=provider, schema_version=value["schema_version"])
        elif value["source_format"] == "json":
            source["json_text_policy"] = value.get("json_text_policy", "text")
        sources[item_id] = source
    # Same sorted ID order used by compare_systems; no paths or raw IDs in provenance.
    return texts, [
        dict(item_index=index, **sources[item_id])
        for index, item_id in enumerate(sorted(texts))
    ]


def load_comparison_manifest(
    path: Path,
) -> Tuple[Dict[str, str], Dict[str, Dict[str, str]], Dict[str, Any]]:
    payload = path.read_bytes()
    try:
        document = load_json(payload.decode("utf-8-sig"))
    except UnicodeDecodeError as error:
        raise ValueError("manifest must be valid UTF-8") from error
    if not isinstance(document, Mapping) or document.get("schema") != MANIFEST_SCHEMA:
        raise ValueError("manifest.schema must be " + MANIFEST_SCHEMA)
    if set(document) != {"schema", "references", "systems"}:
        raise ValueError("manifest requires exactly schema, references, systems")
    references, reference_sources = _files(
        document["references"], path.parent, "references"
    )
    if not isinstance(document["systems"], Mapping) or len(document["systems"]) < 2:
        raise ValueError("manifest.systems must contain at least two systems")
    systems = {}
    system_sources = []
    for system_id, files in document["systems"].items():
        if not isinstance(system_id, str) or not system_id.strip():
            raise ValueError("manifest system IDs must be non-empty strings")
        hypotheses, sources = _files(
            files, path.parent, "systems[{}]".format(system_id)
        )
        if set(hypotheses) != set(references):
            raise ValueError("manifest system IDs must exactly match reference IDs")
        systems[system_id] = hypotheses
        system_sources.append({"id": system_id, "files": sources})
    return (
        references,
        systems,
        {
            "schema": MANIFEST_SCHEMA,
            "manifest_sha256": hashlib.sha256(payload).hexdigest(),
            "references": reference_sources,
            "systems": system_sources,
        },
    )
