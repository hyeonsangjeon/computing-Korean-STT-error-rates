"""Runtime validation shared by all comparison report consumers.

Unknown fields in the 1.x family are allowed, but must still be finite JSON.
This validates a report contract, not the truth of its source transcripts.
"""

import math
import re
from typing import Any, Mapping, Optional, Set


def _fail(path: str, message: str) -> None:
    raise ValueError("{}: {}".format(path, message))


def _object(value: Any, path: str, required: str = "") -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(path, "must be an object")
    for key in required.split():
        if key not in value:
            _fail(path + "." + key, "is required")
    return value


def _text(value: Any, path: str) -> None:
    if not isinstance(value, str) or not value.strip():
        _fail(path, "must be a non-empty string")


def _number(value: Any, path: str, minimum: Optional[float] = None) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(path, "must be a finite number")
    if isinstance(value, float) and not math.isfinite(value):
        _fail(path, "must be a finite number")
    if minimum is not None and value < minimum:
        _fail(path, "must be at least {}".format(minimum))


def _integer(value: Any, path: str, minimum: Optional[int] = 0) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        _fail(path, "must be an integer")
    if minimum is not None and value < minimum:
        _fail(path, "must be at least {}".format(minimum))


def _choice(value: Any, path: str, choices: tuple) -> None:
    if value not in choices:
        _fail(path, "unsupported value")


def _hash(value: Any, path: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        _fail(path, "must be a SHA-256 hex digest")


def _list(value: Any, path: str, minimum: int = 0) -> list:
    if not isinstance(value, list) or len(value) < minimum:
        _fail(path, "must be a list with at least {} items".format(minimum))
    return value


def _json(value: Any, path: str, ancestors: Set[int]) -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        _number(value, path)
        return
    if not isinstance(value, (Mapping, list)):
        _fail(path, "must contain only finite JSON values")
    if id(value) in ancestors:
        _fail(path, "must not contain a circular reference")
    ancestors.add(id(value))
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                _fail(path, "object keys must be strings")
            _json(item, path + "." + key, ancestors)
    else:
        for index, item in enumerate(value):
            _json(item, "{}[{}]".format(path, index), ancestors)
    ancestors.remove(id(value))


def _metrics(value: Any, path: str) -> None:
    metrics = _object(value, path, "cer wer crr")
    for name in ("cer", "wer", "crr"):
        prefix = path + "." + name
        metric = _object(metrics[name], prefix, "micro macro")
        for average in ("micro", "macro"):
            _number(
                metric[average], prefix + "." + average, None if name == "crr" else 0
            )
        if name != "crr":
            for count in ("hits", "substitutions", "deletions", "insertions"):
                _object(metric, prefix, count)
                _integer(metric[count], prefix + "." + count)


def _optional_results(system: Mapping[str, Any], path: str) -> None:
    for name, keys in (("keywords", "recall false_positives"), ("entities", "f1")):
        if name not in system:
            continue
        prefix = path + "." + name
        result = _object(system[name], prefix, "summary")
        summary = _object(result["summary"], prefix + ".summary", keys)
        for key in keys.split():
            _number(summary[key], prefix + ".summary." + key, 0)
        if name == "entities":
            _object(result, prefix, "entity_cer")
            entity_cer = _object(result["entity_cer"], prefix + ".entity_cer", "micro")
            _number(entity_cer["micro"], prefix + ".entity_cer.micro", 0)
    if "diagnostics" in system:
        prefix = path + ".diagnostics"
        diagnostic = _object(
            system["diagnostics"],
            prefix,
            "spacing_boundary number_unit josa_eomi_adjacent top_character_edits",
        )
        for section, keys in (
            ("spacing_boundary", "missing_boundaries extra_boundaries"),
            ("number_unit", "missing_mentions unexpected_mentions"),
            ("josa_eomi_adjacent", "substitutions"),
        ):
            values = _object(diagnostic[section], prefix + "." + section, keys)
            for key in keys.split():
                _integer(values[key], prefix + "." + section + "." + key)
        edits = _object(
            diagnostic["top_character_edits"],
            prefix + ".top_character_edits",
            "substitutions deletions insertions",
        )
        for name in ("substitutions", "deletions", "insertions"):
            rows = _list(edits[name], prefix + ".top_character_edits." + name)
            for index, row in enumerate(rows):
                row_path = "{}.top_character_edits.{}[{}]".format(prefix, name, index)
                _object(row, row_path, "count")
                _integer(row["count"], row_path + ".count", 1)
                for key in ("reference", "hypothesis"):
                    if (
                        name == "substitutions"
                        or (name == "deletions" and key == "reference")
                        or (name == "insertions" and key == "hypothesis")
                    ):
                        _object(row, row_path, key)
                        if not isinstance(row[key], str):
                            _fail(row_path + "." + key, "must be a string")


def validate_comparison_report(report: object) -> None:
    """Raise ValueError with a field path for an invalid 1.x comparison report."""
    root = _object(
        report,
        "report",
        "schema evaluator options dataset evaluation_config systems pairwise warnings",
    )
    _json(root, "report", set())
    if not isinstance(root["schema"], str) or not re.fullmatch(
        r"nlptutti\.comparison/1\.\d+", root["schema"]
    ):
        _fail("report.schema", "must be a supported nlptutti.comparison/1.x schema")
    evaluator = _object(root["evaluator"], "report.evaluator", "name version")
    _text(evaluator["name"], "report.evaluator.name")
    _text(evaluator["version"], "report.evaluator.version")
    options = _object(
        root["options"],
        "report.options",
        "rate_mode rm_punctuation unicode_normalization bootstrap_resamples bootstrap_seed confidence diagnostic_profile",
    )
    _choice(
        options["rate_mode"], "report.options.rate_mode", ("normalized", "standard")
    )
    if not isinstance(options["rm_punctuation"], bool):
        _fail("report.options.rm_punctuation", "must be a boolean")
    _choice(
        options["unicode_normalization"],
        "report.options.unicode_normalization",
        (None, "NFC", "NFD", "NFKC", "NFKD"),
    )
    _choice(
        options["diagnostic_profile"],
        "report.options.diagnostic_profile",
        (None, "korean-v1"),
    )
    _choice(
        options.get("privacy_mode", "detailed"),
        "report.options.privacy_mode",
        ("detailed", "aggregate"),
    )
    _integer(options["bootstrap_resamples"], "report.options.bootstrap_resamples")
    _integer(options["bootstrap_seed"], "report.options.bootstrap_seed", None)
    _number(options["confidence"], "report.options.confidence")
    if not 0 < options["confidence"] < 1:
        _fail("report.options.confidence", "must be between 0 and 1")
    dataset = _object(
        root["dataset"], "report.dataset", "item_count ids_sha256 references_sha256"
    )
    _integer(dataset["item_count"], "report.dataset.item_count", 1)
    for key in ("ids_sha256", "references_sha256"):
        _hash(dataset[key], "report.dataset." + key)
    config = _object(
        root["evaluation_config"],
        "report.evaluation_config",
        "keywords entities entity_aliases sha256",
    )
    for key in ("keywords", "entities", "entity_aliases"):
        if not isinstance(config[key], bool):
            _fail("report.evaluation_config." + key, "must be a boolean")
    if config["sha256"] is not None:
        _hash(config["sha256"], "report.evaluation_config.sha256")
    if config["entity_aliases"] and not config["entities"]:
        _fail("report.evaluation_config.entity_aliases", "requires entities")
    if any(config[key] for key in ("keywords", "entities", "entity_aliases")) != (
        config["sha256"] is not None
    ):
        _fail("report.evaluation_config.sha256", "must match configured evaluations")
    systems = _list(root["systems"], "report.systems", 2)
    system_ids = set()
    for index, value in enumerate(systems):
        path = "report.systems[{}]".format(index)
        system = _object(value, path, "id metrics provenance")
        _text(system["id"], path + ".id")
        if system["id"] in system_ids:
            _fail(path + ".id", "must be unique")
        system_ids.add(system["id"])
        _metrics(system["metrics"], path + ".metrics")
        provenance = _object(
            system["provenance"], path + ".provenance", "hypothesis_sha256 item_count"
        )
        _hash(provenance["hypothesis_sha256"], path + ".provenance.hypothesis_sha256")
        _integer(provenance["item_count"], path + ".provenance.item_count", 1)
        if provenance["item_count"] != dataset["item_count"]:
            _fail(path + ".provenance.item_count", "must match dataset.item_count")
        for name in ("keywords", "entities"):
            if config[name] != (name in system):
                _fail(path + "." + name, "must match evaluation_config")
        _optional_results(system, path)
    pairs = _list(root["pairwise"], "report.pairwise", 1)
    seen = set()
    for index, value in enumerate(pairs):
        path = "report.pairwise[{}]".format(index)
        pair = _object(value, path, "baseline candidate metrics")
        for key in ("baseline", "candidate"):
            _text(pair[key], path + "." + key)
            if pair[key] not in system_ids:
                _fail(path + "." + key, "must reference an existing system")
        identity = frozenset((pair["baseline"], pair["candidate"]))
        if len(identity) != 2 or identity in seen:
            _fail(path, "must be a unique pair of distinct systems")
        seen.add(identity)
        metrics = _object(pair["metrics"], path + ".metrics", "cer wer crr")
        for name in ("cer", "wer", "crr"):
            prefix = path + ".metrics." + name
            delta = _object(metrics[name], prefix, "micro macro")
            _number(delta["micro"], prefix + ".micro")
            _number(delta["macro"], prefix + ".macro")
            if "confidence_interval" in delta:
                prefix += ".confidence_interval"
                interval = _object(
                    delta["confidence_interval"],
                    prefix,
                    "confidence lower upper method resamples seed sampling_unit",
                )
                for key in ("lower", "upper", "confidence"):
                    _number(interval[key], prefix + "." + key)
                if interval["lower"] > interval["upper"]:
                    _fail(prefix, "lower must not exceed upper")
                _integer(interval["resamples"], prefix + ".resamples", 1)
                _integer(interval["seed"], prefix + ".seed", None)
                _choice(
                    interval["method"],
                    prefix + ".method",
                    ("paired_percentile_bootstrap",),
                )
                _choice(
                    interval["sampling_unit"], prefix + ".sampling_unit", ("utterance",)
                )
                for key, option in (
                    ("confidence", "confidence"),
                    ("resamples", "bootstrap_resamples"),
                    ("seed", "bootstrap_seed"),
                ):
                    if interval[key] != options[option]:
                        _fail(prefix + "." + key, "must match report.options." + option)
    if len(pairs) != len(systems) * (len(systems) - 1) // 2:
        _fail("report.pairwise", "must contain every system pair once")
    for index, warning in enumerate(_list(root["warnings"], "report.warnings")):
        _text(warning, "report.warnings[{}]".format(index))
    if "raw_inputs" in root:
        if options.get("privacy_mode") == "aggregate":
            _fail("report.raw_inputs", "not allowed in aggregate mode")
        raw = _object(root["raw_inputs"], "report.raw_inputs", "ids references systems")
        for key in ("ids", "references"):
            values = _list(raw[key], "report.raw_inputs." + key)
            if len(values) != dataset["item_count"] or not all(
                isinstance(v, str) for v in values
            ):
                _fail("report.raw_inputs." + key, "must contain one string per item")
        if len(set(raw["ids"])) != dataset["item_count"] or any(
            not v.strip() for v in raw["ids"]
        ):
            _fail("report.raw_inputs.ids", "must be unique non-empty IDs")
        raw_systems = _list(raw["systems"], "report.raw_inputs.systems")
        raw_ids = []
        for index, value in enumerate(raw_systems):
            path = "report.raw_inputs.systems[{}]".format(index)
            entry = _object(value, path, "id hypotheses")
            _text(entry["id"], path + ".id")
            raw_ids.append(entry["id"])
            hypotheses = _list(entry["hypotheses"], path + ".hypotheses")
            if len(hypotheses) != dataset["item_count"] or not all(
                isinstance(v, str) for v in hypotheses
            ):
                _fail(path + ".hypotheses", "must contain one string per item")
        if len(raw_ids) != len(system_ids) or set(raw_ids) != system_ids:
            _fail("report.raw_inputs.systems", "must match system IDs exactly")


__all__ = ["validate_comparison_report"]
