"""Deterministic renderers for comparison reports."""

import json
import os
import tempfile
from pathlib import Path
from typing import Dict, Mapping, Union, cast

from nlptutti.comparison_types import COMPARISON_SCHEMA, ComparisonReport


def _validate_report(report: Mapping[str, object]) -> None:
    if not isinstance(report, Mapping):
        raise TypeError("report must be a comparison report mapping")
    if report.get("schema") != COMPARISON_SCHEMA:
        raise ValueError(f"report schema must be {COMPARISON_SCHEMA!r}")
    if not isinstance(report.get("systems"), list):
        raise ValueError("report systems must be a list")
    if not isinstance(report.get("pairwise"), list):
        raise ValueError("report pairwise must be a list")


def render_comparison_json(report: ComparisonReport) -> str:
    """Render a comparison report as canonical, human-readable JSON."""

    _validate_report(report)
    try:
        return (
            json.dumps(
                report,
                ensure_ascii=False,
                allow_nan=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
    except (TypeError, ValueError) as error:
        raise TypeError("report must contain only finite JSON values") from error


def _format_number(value: Union[int, float]) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("metric values must be numbers")
    if isinstance(value, int):
        return str(value)
    return format(value, ".6f")


def _table_text(value: object) -> str:
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("\r", " ")
        .replace("\n", " ")
    )


def _inline_code(value: object) -> str:
    text = str(value).replace("\r", " ").replace("\n", " ")
    fence = "`"
    while fence in text:
        fence += "`"
    padding = " " if text.startswith("`") or text.endswith("`") else ""
    return "{fence}{padding}{text}{padding}{fence}".format(
        fence=fence,
        padding=padding,
        text=text,
    )


def _system_table(report: ComparisonReport) -> str:
    lines = [
        "| System | CER micro | CER macro | WER micro | WER macro | CRR micro | CRR macro |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for system in report["systems"]:
        metrics = system["metrics"]
        lines.append(
            "| {system_id} | {cer_micro} | {cer_macro} | {wer_micro} | "
            "{wer_macro} | {crr_micro} | {crr_macro} |".format(
                system_id=_table_text(system["id"]),
                cer_micro=_format_number(metrics["cer"]["micro"]),
                cer_macro=_format_number(metrics["cer"]["macro"]),
                wer_micro=_format_number(metrics["wer"]["micro"]),
                wer_macro=_format_number(metrics["wer"]["macro"]),
                crr_micro=_format_number(metrics["crr"]["micro"]),
                crr_macro=_format_number(metrics["crr"]["macro"]),
            )
        )
    return "\n".join(lines)


def _pairwise_table(report: ComparisonReport) -> str:
    lines = [
        "| Baseline | Candidate | Metric | Micro delta | Macro delta | Micro CI |",
        "| --- | --- | --- | ---: | ---: | --- |",
    ]
    for comparison in report["pairwise"]:
        for metric_name in ("cer", "wer", "crr"):
            delta = comparison["metrics"][metric_name]
            interval = delta.get("confidence_interval")
            interval_text = (
                "[{lower}, {upper}] ({confidence})".format(
                    lower=_format_number(interval["lower"]),
                    upper=_format_number(interval["upper"]),
                    confidence=_format_number(interval["confidence"]),
                )
                if interval is not None
                else "-"
            )
            lines.append(
                "| {baseline} | {candidate} | {metric} | {micro} | {macro} | {interval} |".format(
                    baseline=_table_text(comparison["baseline"]),
                    candidate=_table_text(comparison["candidate"]),
                    metric=metric_name.upper(),
                    micro=_format_number(delta["micro"]),
                    macro=_format_number(delta["macro"]),
                    interval=interval_text,
                )
            )
    if len(lines) == 2:
        lines.append("| - | - | - | - | - | - |")
    return "\n".join(lines)


def _optional_summaries(report: ComparisonReport) -> str:
    lines = []
    for system in report["systems"]:
        if "keywords" in system:
            summary = cast(Mapping[str, object], system["keywords"])["summary"]
            summary = cast(Mapping[str, Union[int, float]], summary)
            lines.append(
                "- {} keywords: recall={}, false positives={}".format(
                    _inline_code(system["id"]),
                    _format_number(summary["recall"]),
                    _format_number(summary["false_positives"]),
                )
            )
        if "entities" in system:
            entities = cast(Mapping[str, object], system["entities"])
            summary = cast(Mapping[str, Union[int, float]], entities["summary"])
            entity_cer = cast(Mapping[str, Union[int, float]], entities["entity_cer"])
            lines.append(
                "- {} entities: F1={}, entity CER micro={}".format(
                    _inline_code(system["id"]),
                    _format_number(summary["f1"]),
                    _format_number(entity_cer["micro"]),
                )
            )
    return "\n".join(lines) if lines else "- No keyword or entity evaluation requested."


def _top_substitutions(diagnostics: Mapping[str, object]) -> str:
    top_edits = cast(Mapping[str, object], diagnostics["top_character_edits"])
    rows = cast(list, top_edits["substitutions"])
    if not rows:
        return "-"
    return ", ".join(
        "{}->{} ({})".format(
            _table_text(row["reference"]),
            _table_text(row["hypothesis"]),
            row["count"],
        )
        for row in rows[:3]
    )


def _diagnostic_section(report: ComparisonReport) -> str:
    systems = [system for system in report["systems"] if "diagnostics" in system]
    if not systems:
        return ""
    lines = [
        "## Korean diagnostics",
        "",
        "Number/unit and josa/eomi-adjacent rows are experimental heuristics, not morphological analysis.",
        "",
        "| System | Spacing missing/extra | Number-unit missing/unexpected | Josa/eomi adjacent | Top substitutions |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for system in systems:
        diagnostics = cast(Mapping[str, object], system["diagnostics"])
        spacing = cast(Mapping[str, int], diagnostics["spacing_boundary"])
        number_unit = cast(Mapping[str, int], diagnostics["number_unit"])
        suffix = cast(Mapping[str, int], diagnostics["josa_eomi_adjacent"])
        lines.append(
            "| {system} | {spacing_missing}/{spacing_extra} | "
            "{number_missing}/{number_extra} | {suffix} | {top} |".format(
                system=_table_text(system["id"]),
                spacing_missing=spacing["missing_boundaries"],
                spacing_extra=spacing["extra_boundaries"],
                number_missing=number_unit["missing_mentions"],
                number_extra=number_unit["unexpected_mentions"],
                suffix=suffix["substitutions"],
                top=_top_substitutions(diagnostics),
            )
        )
    return "\n".join(lines) + "\n\n"


def render_comparison_markdown(report: ComparisonReport) -> str:
    """Render a comparison report without reading any external state."""

    _validate_report(report)
    evaluator = report["evaluator"]
    options = report["options"]
    dataset = report["dataset"]
    evaluation_config = report["evaluation_config"]
    warnings = report["warnings"]
    warning_lines = (
        "\n".join(f"- {warning}" for warning in warnings) if warnings else "- None."
    )
    privacy = (
        "Raw transcripts are included by explicit opt-in."
        if "raw_inputs" in report
        else "Raw transcripts are excluded; only fingerprints and aggregate results are stored."
    )
    return """# Nlptutti comparison report

- Schema: `{schema}`
- Evaluator: `{evaluator_name} {evaluator_version}`
- Items: {item_count}
- Rate mode: `{rate_mode}`
- Remove punctuation: `{rm_punctuation}`
- Unicode normalization: `{unicode_normalization}`
- Paired bootstrap: `{bootstrap_resamples}` resamples, seed `{bootstrap_seed}`, confidence `{confidence}`

## Systems

{system_table}

## Pairwise deltas

Positive CER/WER deltas mean the candidate has a higher error rate. Positive
CRR deltas mean the candidate has a higher recognition rate.

{pairwise_table}

## Keyword and entity summaries

{optional_summaries}

{diagnostic_section}## Provenance

- IDs SHA-256: `{ids_sha256}`
- References SHA-256: `{references_sha256}`
- Evaluation config SHA-256: `{evaluation_config_sha256}`
- Privacy: {privacy}

## Warnings

{warning_lines}
""".format(
        schema=report["schema"],
        evaluator_name=evaluator["name"],
        evaluator_version=evaluator["version"],
        item_count=dataset["item_count"],
        rate_mode=options["rate_mode"],
        rm_punctuation=str(options["rm_punctuation"]).lower(),
        unicode_normalization=(options["unicode_normalization"] or "none"),
        bootstrap_resamples=options["bootstrap_resamples"],
        bootstrap_seed=options["bootstrap_seed"],
        confidence=_format_number(options["confidence"]),
        system_table=_system_table(report),
        pairwise_table=_pairwise_table(report),
        optional_summaries=_optional_summaries(report),
        diagnostic_section=_diagnostic_section(report),
        ids_sha256=dataset["ids_sha256"],
        references_sha256=dataset["references_sha256"],
        evaluation_config_sha256=(evaluation_config["sha256"] or "none"),
        privacy=privacy,
        warning_lines=warning_lines,
    )


def _write_atomic(path: Path, content: str) -> None:
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=".{}-".format(path.name),
            suffix=".tmp",
            dir=str(path.parent),
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
        os.replace(str(temporary), str(path))
    except BaseException:
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
        raise


def write_comparison_bundle(
    report: ComparisonReport,
    output_dir: Union[str, Path],
) -> Dict[str, Path]:
    """Write deterministic ``report.json`` and ``report.md`` files."""

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    json_path = destination / "report.json"
    markdown_path = destination / "report.md"
    _write_atomic(json_path, render_comparison_json(report))
    _write_atomic(markdown_path, render_comparison_markdown(report))
    return {"json": json_path, "markdown": markdown_path}


__all__ = [
    "render_comparison_json",
    "render_comparison_markdown",
    "write_comparison_bundle",
]
