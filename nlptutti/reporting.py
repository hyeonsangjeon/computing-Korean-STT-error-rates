"""Deterministic renderers for comparison reports."""

import json
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
        return json.dumps(
            report,
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
            sort_keys=True,
        ) + "\n"
    except (TypeError, ValueError) as error:
        raise TypeError("report must contain only finite JSON values") from error


def _format_number(value: Union[int, float]) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("metric values must be numbers")
    if isinstance(value, int):
        return str(value)
    return format(value, ".6f")


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
                system_id=system["id"].replace("|", "\\|"),
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
        "| Baseline | Candidate | Metric | Micro delta | Macro delta |",
        "| --- | --- | --- | ---: | ---: |",
    ]
    for comparison in report["pairwise"]:
        for metric_name in ("cer", "wer", "crr"):
            delta = comparison["metrics"][metric_name]
            lines.append(
                "| {baseline} | {candidate} | {metric} | {micro} | {macro} |".format(
                    baseline=comparison["baseline"].replace("|", "\\|"),
                    candidate=comparison["candidate"].replace("|", "\\|"),
                    metric=metric_name.upper(),
                    micro=_format_number(delta["micro"]),
                    macro=_format_number(delta["macro"]),
                )
            )
    if len(lines) == 2:
        lines.append("| - | - | - | - | - |")
    return "\n".join(lines)


def _optional_summaries(report: ComparisonReport) -> str:
    lines = []
    for system in report["systems"]:
        if "keywords" in system:
            summary = cast(Mapping[str, object], system["keywords"])["summary"]
            summary = cast(Mapping[str, Union[int, float]], summary)
            lines.append(
                "- `{}` keywords: recall={}, false positives={}".format(
                    system["id"],
                    _format_number(summary["recall"]),
                    _format_number(summary["false_positives"]),
                )
            )
        if "entities" in system:
            entities = cast(Mapping[str, object], system["entities"])
            summary = cast(
                Mapping[str, Union[int, float]], entities["summary"]
            )
            entity_cer = cast(
                Mapping[str, Union[int, float]], entities["entity_cer"]
            )
            lines.append(
                "- `{}` entities: F1={}, entity CER micro={}".format(
                    system["id"],
                    _format_number(summary["f1"]),
                    _format_number(entity_cer["micro"]),
                )
            )
    return "\n".join(lines) if lines else "- No keyword or entity evaluation requested."


def render_comparison_markdown(report: ComparisonReport) -> str:
    """Render a comparison report without reading any external state."""

    _validate_report(report)
    evaluator = report["evaluator"]
    options = report["options"]
    dataset = report["dataset"]
    warnings = report["warnings"]
    warning_lines = (
        "\n".join(f"- {warning}" for warning in warnings)
        if warnings
        else "- None."
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

## Systems

{system_table}

## Pairwise deltas

Positive CER/WER deltas mean the candidate has a higher error rate. Positive
CRR deltas mean the candidate has a higher recognition rate.

{pairwise_table}

## Keyword and entity summaries

{optional_summaries}

## Provenance

- IDs SHA-256: `{ids_sha256}`
- References SHA-256: `{references_sha256}`
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
        unicode_normalization=(
            options["unicode_normalization"] or "none"
        ),
        system_table=_system_table(report),
        pairwise_table=_pairwise_table(report),
        optional_summaries=_optional_summaries(report),
        ids_sha256=dataset["ids_sha256"],
        references_sha256=dataset["references_sha256"],
        privacy=privacy,
        warning_lines=warning_lines,
    )


def _write_atomic(path: Path, content: str) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


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
