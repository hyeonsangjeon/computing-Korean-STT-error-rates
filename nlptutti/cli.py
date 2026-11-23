"""Command-line interface for Nlptutti."""

import argparse
import json
import pkgutil
import sys
from pathlib import Path
from typing import Dict, Mapping, NoReturn, Optional, Sequence, Tuple

from nlptutti._json import load_json
from nlptutti.comparison import TextCollection, compare_systems
from nlptutti.manifest import load_comparison_manifest, load_evaluation_config, read_json_file
from nlptutti.quality_gate import evaluate_quality_gate
from nlptutti.reporting import _write_atomic, render_comparison_json, write_comparison_bundle
from nlptutti.score import build_score_report, load_score_inputs, render_score_text


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


def _add_metric_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--rate-mode", choices=("normalized", "standard"), default="normalized",
                        help="분모: normalized(기본, 삽입 포함) 또는 standard(참조 길이)")
    parser.add_argument("--unicode-normalization", choices=("NFC", "NFD", "NFKC", "NFKD"),
                        help="선택 시에만 유니코드 정규화")
    parser.add_argument("--keep-punctuation", action="store_true",
                        help="모든 문장부호를 유지 (기본: 숫자 사이의 점만 보존하고 나머지 문장부호 제거)")
    parser.add_argument("--diagnostic-profile", choices=("korean-v1",),
                        help="선택 진단 추가 (JSON에 오류 문자 조각이 포함될 수 있음)")


class _CommandParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        if self.prog == "nlptutti score":
            message = "참조·가설 파일과 옵션을 확인하세요. 예: nlptutti score ref.txt hyp.txt\n" + message
        super().error(message)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nlptutti",
        description="Evaluate and compare Korean STT transcripts offline.",
    )
    subparsers = parser.add_subparsers(dest="command", parser_class=_CommandParser)
    score = subparsers.add_parser("score", help="참조와 STT 결과 한 쌍의 CER·WER·CRR 계산",
                                  description="참조 파일과 가설 파일을 로컬에서 평가합니다. TXT는 한 줄에 한 발화입니다.")
    score.add_argument("reference", type=Path, metavar="참조파일")
    score.add_argument("hypothesis", type=Path, metavar="가설파일")
    score.add_argument("--input-format", choices=("text", "csv", "jsonl"),
                       help="기본: 두 파일의 확장자. CSV·JSONL은 id와 text 두 필드로 ID 정렬")
    score.add_argument("--format", choices=("text", "json"), help="출력 형식 (기본: 한국어 요약, .json에 저장할 때는 JSON)")
    score.add_argument("--output", type=Path, help="표준 출력 대신 UTF-8 파일에 저장")
    score.add_argument("--include-items", action="store_true", help="발화별 ID와 점수 포함 (원문 제외)")
    _add_metric_options(score)
    sample = subparsers.add_parser("sample", help="emit the installed version's offline example corpus")
    sample.add_argument("--output", type=Path, help="write UTF-8 JSON instead of standard output")
    gate = subparsers.add_parser("gate", help="check an existing report against explicit quality limits")
    gate.add_argument("input", type=Path, help="comparison report JSON")
    gate.add_argument("--policy", type=Path, required=True)
    gate.add_argument("--output", type=Path, help="write decision JSON; exit 3 means regression")
    compare = subparsers.add_parser(
        "compare",
        help="compare two or more systems from a JSON corpus",
    )
    compare.add_argument("input", type=Path, help="UTF-8 comparison corpus JSON")
    compare.add_argument("--input-format", choices=("corpus", "manifest"), default="corpus")
    compare.add_argument("--evaluation-config", type=Path, help="JSON keywords, entities and entity_aliases")
    compare.add_argument("--include-items", action="store_true", help="include per-item scores and source IDs (detailed mode only)")
    compare.add_argument("--labels", type=Path, help="JSON mapping from item ID to user-defined labels")
    compare.add_argument("--top-n", type=int, default=10, help="maximum item IDs per improvement/regression list")
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
    _add_metric_options(compare)
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
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    # argparse can print Korean help or errors before it returns a namespace.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors=stream.errors)
    parser = _build_parser()
    arguments, extra = parser.parse_known_args(argv)
    if extra:
        prefix = "알 수 없는 score 인자: " if arguments.command == "score" else "unrecognized arguments: "
        parser.error(prefix + " ".join(extra))
    if arguments.command is None:
        parser.print_help()
        return 2

    try:
        if arguments.command == "score":
            inputs = load_score_inputs(arguments.reference, arguments.hypothesis, arguments.input_format)
            output = arguments.output
            if output is not None and output.exists() and any(
                output.samefile(path) for path in (arguments.reference, arguments.hypothesis)
            ):
                raise ValueError("결과를 입력 파일에 덮어쓸 수 없습니다. 다른 --output 경로를 지정하세요.")
            result = build_score_report(
                inputs, rm_punctuation=not arguments.keep_punctuation, rate_mode=arguments.rate_mode,
                unicode_normalization=arguments.unicode_normalization,
                diagnostic_profile=arguments.diagnostic_profile, include_items=arguments.include_items,
            )
            fmt = arguments.format or ("json" if output is not None and output.suffix.lower() == ".json" else "text")
            serialized = (json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2, sort_keys=True) + "\n"
                          if fmt == "json" else render_score_text(result))
            if output is None:
                sys.stdout.write(serialized)
            else:
                output.parent.mkdir(parents=True, exist_ok=True)
                _write_atomic(output, serialized)
            return 0
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
        if arguments.command == "gate":
            decision = evaluate_quality_gate(read_json_file(arguments.input), read_json_file(arguments.policy))
            serialized = json.dumps(decision, ensure_ascii=False, allow_nan=False, indent=2, sort_keys=True) + "\n"
            if arguments.output is not None:
                arguments.output.parent.mkdir(parents=True, exist_ok=True)
                _write_atomic(arguments.output, serialized)
            else:
                sys.stdout.write(serialized)
            return 0 if decision["passed"] else 3
        if arguments.output is not None and arguments.output_dir is not None:
            raise ValueError("--output and --output-dir cannot be used together")
        sources = None
        references: TextCollection
        systems: Dict[str, TextCollection]
        if arguments.input_format == "manifest":
            references, file_systems, sources = load_comparison_manifest(arguments.input)
            systems = dict(file_systems)
        else:
            references, systems = _load_comparison_input(arguments.input)
        config = load_evaluation_config(arguments.evaluation_config) if arguments.evaluation_config is not None else {}
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
            include_items=arguments.include_items,
            labels=read_json_file(arguments.labels) if arguments.labels is not None else None,
            top_n=arguments.top_n,
            **config,
        )
        if sources is not None:
            for source, system in zip(sources["systems"], report["systems"]):
                source["id"] = system["id"]
            report["input_sources"] = sources
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
        parser.error(("단일 평가 오류: " if arguments.command == "score" else "") + str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
