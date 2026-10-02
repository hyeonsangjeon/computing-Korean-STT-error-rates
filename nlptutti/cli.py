"""Command-line interface for Nlptutti."""

import argparse
import json
import pkgutil
import sys
from pathlib import Path
from typing import Dict, Mapping, Optional, Sequence, Tuple

from nlptutti._json import load_json
from nlptutti.comparison import TextCollection, compare_systems
from nlptutti.reporting import _write_atomic, render_comparison_json, write_comparison_bundle


def _item_list_to_mapping(values: object, field_name: str) -> Dict[str, str]:
    if not isinstance(values, list) or not values:
        raise ValueError(f"{field_name} must be a non-empty list")
    result = {}
    for index, item in enumerate(values):
        if not isinstance(item, Mapping):
            raise ValueError(f"{field_name}[{index}] must be an object")
        item_id = item.get("id")
        text = item.get("text")
        if not isinstance(item_id, str) or not item_id.strip():
            raise ValueError(f"{field_name}[{index}].id must be a non-empty string")
        if not isinstance(text, str):
            raise ValueError(f"{field_name}[{index}].text must be a string")
        if item_id in result:
            raise ValueError(f"{field_name} contains duplicate ID {item_id!r}")
        result[item_id] = text
    return result


def _coerce_cli_collection(values: object, field_name: str) -> TextCollection:
    if isinstance(values, Mapping):
        return dict(values)
    if isinstance(values, list) and values and isinstance(values[0], Mapping):
        return _item_list_to_mapping(values, field_name)
    if isinstance(values, list):
        return list(values)
    raise ValueError(f"{field_name} must be an object or list")


def _load_comparison_input(
    path: Path,
) -> Tuple[TextCollection, Dict[str, TextCollection]]:
    try:
        document = load_json(path.read_text(encoding="utf-8-sig"))
    except OSError as error:
        raise ValueError(f"could not read input file: {error}") from error
    except UnicodeDecodeError as error:
        raise ValueError("comparison input must be valid UTF-8") from error
    if not isinstance(document, Mapping):
        raise ValueError("comparison input must be a JSON object")
    if "references" not in document or "systems" not in document:
        raise ValueError("comparison input requires references and systems")
    references = _coerce_cli_collection(document["references"], "references")
    systems_document = document["systems"]
    if not isinstance(systems_document, Mapping):
        raise ValueError("systems must be an object keyed by system ID")
    systems = {
        system_id: _coerce_cli_collection(values, f"systems[{system_id!r}]")
        for system_id, values in systems_document.items()
    }
    return references, systems


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nlptutti",
        description="Evaluate and compare Korean STT transcripts offline.",
    )
    subparsers = parser.add_subparsers(dest="command")
    sample = subparsers.add_parser("sample", help="emit the installed version's offline example corpus")
    sample.add_argument("--output", type=Path, help="write UTF-8 JSON instead of standard output")
    compare = subparsers.add_parser(
        "compare",
        help="compare two or more systems from a JSON corpus",
    )
    compare.add_argument("input", type=Path, help="UTF-8 comparison corpus JSON")
    compare.add_argument(
        "--output",
        type=Path,
        help="write JSON to this path instead of standard output",
    )
    compare.add_argument(
        "--output-dir",
        type=Path,
        help="write report.json and report.md to this directory",
    )
    compare.add_argument(
        "--rate-mode",
        choices=("normalized", "standard"),
        default="normalized",
    )
    compare.add_argument(
        "--unicode-normalization",
        choices=("NFC", "NFD", "NFKC", "NFKD"),
    )
    compare.add_argument(
        "--keep-punctuation",
        action="store_true",
        help="keep punctuation during metric preprocessing",
    )
    compare.add_argument(
        "--privacy-mode",
        choices=("aggregate", "detailed"),
        default="detailed",
        help="aggregate removes text details and replaces system IDs; detailed preserves compatibility",
    )
    compare.add_argument(
        "--include-transcripts",
        action="store_true",
        help="include raw reference and hypothesis text in the JSON report",
    )
    compare.add_argument(
        "--bootstrap",
        type=int,
        default=0,
        metavar="N",
        help="paired bootstrap resamples; 0 disables confidence intervals",
    )
    compare.add_argument("--seed", type=int, default=42)
    compare.add_argument("--confidence", type=float, default=0.95)
    compare.add_argument(
        "--diagnostic-profile",
        choices=("korean-v1",),
        help="add deterministic Korean diagnostic breakdowns",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    arguments = parser.parse_args(argv)
    if arguments.command is None:
        parser.print_help()
        return 2

    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if arguments.command == "sample":
            data = pkgutil.get_data("nlptutti", "comparison_sample.json")
            if data is None:
                raise ValueError("installed sample data is missing")
            serialized = json.dumps(load_json(data.decode("utf-8")), ensure_ascii=False, indent=2) + "\n"
            if arguments.output is not None:
                arguments.output.parent.mkdir(parents=True, exist_ok=True)
                _write_atomic(arguments.output, serialized)
            else:
                sys.stdout.write(serialized)
            return 0
        if arguments.output is not None and arguments.output_dir is not None:
            raise ValueError("--output and --output-dir cannot be used together")
        references, systems = _load_comparison_input(arguments.input)
        report = compare_systems(
            references,
            systems,
            rm_punctuation=not arguments.keep_punctuation,
            rate_mode=arguments.rate_mode,
            unicode_normalization=arguments.unicode_normalization,
            bootstrap=arguments.bootstrap,
            seed=arguments.seed,
            confidence=arguments.confidence,
            diagnostic_profile=arguments.diagnostic_profile,
            include_transcripts=arguments.include_transcripts,
            privacy_mode=arguments.privacy_mode,
        )
        serialized = render_comparison_json(report)
        if arguments.output_dir is not None:
            paths = write_comparison_bundle(report, arguments.output_dir)
            sys.stdout.write(
                "wrote {} and {}\n".format(paths["json"], paths["markdown"])
            )
        elif arguments.output is not None:
            arguments.output.parent.mkdir(parents=True, exist_ok=True)
            _write_atomic(arguments.output, serialized)
        else:
            sys.stdout.write(serialized)
    except (TypeError, ValueError, OSError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
