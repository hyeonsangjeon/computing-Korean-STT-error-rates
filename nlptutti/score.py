"""Single-system, offline scoring for aligned UTF-8 files."""

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, NamedTuple, Optional, TextIO

from nlptutti._json import load_json
from nlptutti.asr_metrics import evaluate_corpus
from nlptutti.comparison import _fingerprint, _package_version
from nlptutti.diagnostics import diagnose_korean_errors

_SUFFIXES = {".txt": "text", ".csv": "csv", ".jsonl": "jsonl"}


class ScoreInputs(NamedTuple):
    source_format: str
    ids: List[str]
    references: List[str]
    hypotheses: List[str]


def _add_record(records: Dict[str, str], record: object, where: str) -> None:
    if not isinstance(record, dict) or set(record) != {"id", "text"}:
        raise ValueError(where + ": 문자열 id와 text 두 필드가 필요합니다.")
    item_id, text = record["id"], record["text"]
    if not isinstance(item_id, str) or not item_id.strip() or not isinstance(text, str):
        raise ValueError(where + ": id는 빈 문자열일 수 없고 text는 문자열이어야 합니다.")
    if item_id in records:
        raise ValueError(where + ": 중복된 id입니다.")
    if any(ch in value for ch in ("\0", "\r", "\n") for value in (item_id, text)):
        raise ValueError(where + ": id와 text에 줄바꿈이나 NUL 문자를 넣지 마세요.")
    try:
        item_id.encode("utf-8")
        text.encode("utf-8")
    except UnicodeEncodeError as error:
        raise ValueError(where + ": 올바른 유니코드 문자열이 아닙니다.") from error
    records[item_id] = text


def _read_records(stream: TextIO, fmt: str, source: str) -> Dict[str, str]:
    records: Dict[str, str] = {}
    if fmt == "csv":
        reader = csv.reader(stream, strict=True)
        try:
            header = next(reader, [])
            if sorted(header) != ["id", "text"]:
                raise ValueError(source + ": CSV 첫 줄에 중복 없이 id,text 열을 지정하세요.")
            for row in reader:
                where = "{} {}행".format(source, reader.line_num)
                if len(row) != 2:
                    raise ValueError(where + ": CSV 열 수가 헤더와 다릅니다.")
                _add_record(records, dict(zip(header, row)), where)
        except csv.Error as error:
            raise ValueError("{} {}행: 잘못된 CSV입니다 ({}).".format(source, reader.line_num, error)) from error
    else:
        for index, line in enumerate(stream, 1):
            where = "{} {}행".format(source, index)
            if fmt == "text":
                if "\0" in line:
                    raise ValueError(where + ": 텍스트 파일에 NUL 문자가 있습니다.")
                # Universal newlines; do not trim whitespace or skip empty utterances.
                records[str(index)] = line.rstrip("\n")
            else:
                try:
                    record = load_json(line)
                except (ValueError, RecursionError) as error:
                    raise ValueError(where + ": JSONL 한 줄에 객체 하나가 필요합니다 ({}).".format(error)) from error
                _add_record(records, record, where)
    return records


def _read_file(path: Path, fmt: str, role: str) -> Dict[str, str]:
    source = "{} 파일 {}".format(role, path.name)
    try:
        with path.open(encoding="utf-8-sig", newline=None) as stream:
            return _read_records(stream, fmt, source)
    except UnicodeDecodeError as error:
        raise ValueError(source + ": UTF-8 인코딩으로 저장하세요.") from error
    except OSError as error:
        raise ValueError(source + ": 파일을 읽을 수 없습니다 ({}).".format(error)) from error


def load_score_inputs(ref: Path, hyp: Path, input_format: Optional[str]) -> ScoreInputs:
    formats = [_SUFFIXES.get(path.suffix.lower()) for path in (ref, hyp)]
    if input_format is None:
        if formats[0] is None or formats[0] != formats[1]:
            raise ValueError("참조와 가설은 같은 형식(.txt, .csv, .jsonl)이어야 합니다. "
                             "확장자가 없다면 --input-format을 지정하세요.")
        input_format = formats[0]
    elif any(fmt is not None and fmt != input_format for fmt in formats):
        raise ValueError("파일 확장자가 --input-format과 일치하지 않습니다.")

    references = _read_file(ref, input_format, "참조")
    hypotheses = _read_file(hyp, input_format, "가설")
    if len(references) != len(hypotheses):
        raise ValueError("발화 수가 다릅니다: 참조 {}개, 가설 {}개. "
                         "전사가 없으면 해당 발화를 빈 줄(TXT) 또는 빈 text로 남겨 주세요."
                         .format(len(references), len(hypotheses)))
    if not references:
        raise ValueError("평가할 발화가 없습니다. 두 파일에 적어도 한 발화를 넣어 주세요.")
    if references.keys() != hypotheses.keys():
        raise ValueError("참조와 가설의 id가 다릅니다: 가설에서 누락 {}개, 추가 {}개."
                         .format(len(references.keys() - hypotheses.keys()),
                                 len(hypotheses.keys() - references.keys())))
    ids = list(references) if input_format == "text" else sorted(references)
    return ScoreInputs(input_format, ids, [references[i] for i in ids], [hypotheses[i] for i in ids])


def build_score_report(
    inputs: ScoreInputs, *, rm_punctuation: bool, rate_mode: str,
    unicode_normalization: Optional[str], diagnostic_profile: Optional[str], include_items: bool,
) -> Dict[str, Any]:
    corpus = evaluate_corpus(inputs.references, inputs.hypotheses, rm_punctuation,
                             rate_mode=rate_mode, unicode_normalization=unicode_normalization,
                             include_items=include_items)
    report: Dict[str, Any] = {
        "schema": "nlptutti.score/1.0",
        "evaluator": {"name": "nlptutti", "version": _package_version()},
        "score_unit": "ratio",
        "input_format": inputs.source_format,
        "provenance": {"ids_sha256": _fingerprint(inputs.ids),
                       "references_sha256": _fingerprint(inputs.references),
                       "hypotheses_sha256": _fingerprint(inputs.hypotheses)},
        "corpus": corpus,
    }
    if include_items:
        rows = corpus.pop("items")
        assert isinstance(rows, list)
        report["items"] = [dict(id=i, **row) for i, row in zip(inputs.ids, rows)]
    if diagnostic_profile is not None:
        report["diagnostics"] = diagnose_korean_errors(
            inputs.references, inputs.hypotheses, rm_punctuation=rm_punctuation,
            rate_mode=rate_mode, unicode_normalization=unicode_normalization,
        )
    return report


def render_score_text(report: Mapping[str, Any]) -> str:
    corpus = report["corpus"]
    lines = [
        "발화 {utterances}개 · {rate_mode} · 문장부호: {policy} · Unicode: {unicode}".format(
            policy="숫자 사이 점만 보존" if corpus["rm_punctuation"] else "모두 유지",
            unicode=corpus["unicode_normalization"] or "원문", **corpus),
        "지표    전체(micro)    문장 평균(macro)  [비율, 1 = 100%]",
    ]
    for name in ("cer", "wer", "crr"):
        lines.append("{:3}     {:10.6f}    {:10.6f}".format(
            name.upper(), corpus[name]["micro"], corpus[name]["macro"]))
    lines.append("문자 오류: 치환 {substitutions} · 삭제 {deletions} · 삽입 {insertions}".format(**corpus["cer"]))
    if "items" in report:
        lines.append("\n발화 ID\tCER\tWER\tCRR")
        for row in report["items"]:
            lines.append("{}\t{:.6f}\t{:.6f}\t{:.6f}".format(
                json.dumps(row["id"], ensure_ascii=False), row["cer"], row["wer"], row["crr"]))
    if "diagnostics" in report:
        units = report["diagnostics"]["number_unit"]
        lines.append("\n선택 진단(korean-v1) · 숫자·단위 표기: 누락 {missing_mentions}, 추가 {unexpected_mentions}".format(**units))
        lines.append("양쪽 검출 {both_detected_items}/{items}발화 · 미판정 {unknown_items}발화 "
                     "(의미가 같은지 판정하지 않습니다).".format(**units["coverage"]))
        lines.append("띄어쓰기 경계: 누락 {missing_boundaries}, 추가 {extra_boundaries}".format(
            **report["diagnostics"]["spacing_boundary"]))
    return "\n".join(lines) + "\n"
