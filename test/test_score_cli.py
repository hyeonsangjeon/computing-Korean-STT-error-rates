import json
import os
import subprocess
import sys
from unittest.mock import patch

import pytest

import nlptutti as nt
from nlptutti import asr_metrics
from nlptutti.cli import main


def write_pair(directory, ref, hyp, suffix=".txt"):
    paths = [directory / (role + suffix) for role in ("참조", "전사")]
    for path, content in zip(paths, (ref, hyp)):
        path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
    return [str(path) for path in paths]


@pytest.mark.parametrize("args,code", [(["--help"], 0), (["score", "--help"], 0), (["score"], 2)])
def test_korean_help_and_errors_on_legacy_encoded_pipes(args, code):
    result = subprocess.run(
        [sys.executable, "-m", "nlptutti.cli", *args],
        env=dict(os.environ, PYTHONIOENCODING="cp1252"),
        capture_output=True, timeout=30,
    )
    assert result.returncode == code
    assert "참조" in (result.stdout if code == 0 else result.stderr).decode("utf-8")


def test_txt_summary_json_and_empty_utterances(tmp_path, capsys):
    paths = write_pair(tmp_path, "\ufeff3.5만 원\r\n부산 바다\r\n\r\n안녕!\r\n",
                      "35만 원\n부산바다\n하나 둘\n\n")
    opts = ["--rate-mode", "standard", "--unicode-normalization", "NFC", "--keep-punctuation"]
    assert main(["score", *paths, *opts]) == 0
    summary = capsys.readouterr().out
    assert "발화 4개" in summary and "CER" in summary and "CRR" in summary
    out = tmp_path / "결과" / "결과.json"
    ref = ["3.5만 원", "부산 바다", "", "안녕!"]
    hyp = ["35만 원", "부산바다", "하나 둘", ""]
    assert main(["score", *paths, *opts, "--output", str(out)]) == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["corpus"] == nt.evaluate_corpus(ref, hyp, False, rate_mode="standard", unicode_normalization="NFC")
    assert report["schema"] == "nlptutti.score/1.0"
    assert {"systems", "pairwise", "items", "diagnostics"}.isdisjoint(report)
    assert not any(value in out.read_text(encoding="utf-8") for value in ref if value)
    with patch.object(asr_metrics, "levenshtein", wraps=asr_metrics.levenshtein) as measure:
        assert main(["score", *paths, *opts, "--format", "json", "--include-items"]) == 0
    assert measure.call_count == 8
    rows = json.loads(capsys.readouterr().out)["items"]
    assert [r["id"] for r in rows] == ["1", "2", "3", "4"]
    assert rows[1]["cer"] == 0 and rows[1]["wer"] > 0
    assert rows[2]["cer"] == 3 and rows[2]["wer"] == 2 and rows[2]["crr"] == -2
    assert rows[3]["cer"] == rows[3]["wer"] == 1


@pytest.mark.parametrize("suffix,ref,hyp", [
    (".csv", 'id,text\nb,"부산, 바다"\na,3.5만 원\n', 'text,id\n35만 원,a\n"부산,바다",b\n'),
    (".jsonl", '{"id":"b","text":"부산, 바다"}\n{"id":"a","text":"3.5만 원"}\n',
               '{"id":"a","text":"35만 원"}\n{"id":"b","text":"부산,바다"}'),
])
def test_id_pairs_reorder_and_opt_in_diagnostics(tmp_path, capsys, suffix, ref, hyp):
    paths = write_pair(tmp_path, ref, hyp, suffix)
    assert main(["score", *paths, "--include-items", "--format", "json",
                 "--diagnostic-profile", "korean-v1"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["corpus"] == nt.evaluate_corpus(["3.5만 원", "부산, 바다"], ["35만 원", "부산,바다"])
    assert [i["id"] for i in report["items"]] == ["a", "b"]
    diag = report["diagnostics"]["number_unit"]
    assert diag["missing_mentions"] == diag["unexpected_mentions"] == 1
    assert diag["coverage"]["unknown_items"] == 1


@pytest.mark.parametrize("suffix,ref,hyp,message", [
    (".txt", "기준\n", "", "참조 1개, 가설 0개"), (".txt", "", "", "발화가 없습니다"),
    (".txt", "가", b"\xff", "UTF-8"), (".txt", "\0한글", "한글", "NUL"),
    (".csv", "id,text,text\na,가,가", "id,text\na,가", "id,text"),
    (".csv", "id,text\na,가\na,나", "id,text\na,가", "중복"),
    (".csv", "id,text\na,가", "id,text\nb,가", "id가 다릅니다"),
    (".csv", "id,text\na,가", "id,text\na,나,다", "열 수"),
    (".jsonl", '{"text":"","id":"a"}', '{"id":"a","text":null}', "문자열"),
    (".jsonl", '{"text":"","id":"a"}', '{"id":"a","text":"가","text":"나"}', "JSONL"),
    (".jsonl", '{"text":"","id":"a"}', '{"text":""}', "두 필드"),
    (".jsonl", '{"text":"","id":"a"}', '{"id":"","text":"가"}', "빈 문자열"),
    (".jsonl", '{"text":"","id":"a"}', '{"id":"\\ud800","text":"가"}', "유니코드"),
    (".jsonl", '{"text":"","id":"a"}', '{"text":"","id":"a"}\n\n', "2행"),
    (".json", '{"references":["가"]}', '{"text":"가"}', "같은 형식"),
])
def test_malformed_files_exit_two_in_korean_and_preserve_output(tmp_path, capsys, suffix, ref, hyp, message):
    paths = write_pair(tmp_path, ref, hyp, suffix)
    out = tmp_path / "report.json"
    out.write_bytes(b"old")
    with pytest.raises(SystemExit) as caught:
        main(["score", *paths, "--output", str(out)])
    assert caught.value.code == 2
    captured = capsys.readouterr()
    assert message in captured.err and not captured.out
    assert out.read_bytes() == b"old"


def test_single_empty_hypothesis_and_extensionless_txt(tmp_path, capsys):
    paths = write_pair(tmp_path, "부산 바다\n", "\n", "")
    assert main(["score", *paths, "--input-format", "text", "--format", "json"]) == 0
    corpus = json.loads(capsys.readouterr().out)["corpus"]
    assert corpus["utterances"] == 1 and corpus["cer"]["deletions"] == 4
    assert corpus["wer"]["deletions"] == 2


def test_invalid_arguments_and_input_overwrite(tmp_path, capsys):
    ref, hyp = write_pair(tmp_path, "가", "나")
    for args, message in (([ref], "참조·가설"), ([ref, hyp, "--rate-mode", "wrong"], "확인하세요"),
                          ([ref, hyp, "--unknown"], "알 수 없는"),
                          ([ref, hyp, "--output", ref], "덮어쓸"),
                          ([ref, hyp, "--input-format", "csv"], "확장자"),
                          ([ref, str(tmp_path / "missing.txt")], "파일을 읽을 수 없습니다")):
        with pytest.raises(SystemExit) as caught:
            main(["score", *args])
        assert caught.value.code == 2 and message in capsys.readouterr().err
    assert (tmp_path / "참조.txt").read_text(encoding="utf-8") == "가"
    with pytest.raises(ValueError, match="at least two"):
        nt.compare_systems(["가"], {"one": ["나"]})
