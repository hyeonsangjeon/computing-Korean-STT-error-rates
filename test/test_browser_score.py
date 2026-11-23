"""Exercise the exact offline page kernel against the public Python metrics."""

import itertools
import json
import shutil
import subprocess
from pathlib import Path

import pytest

import nlptutti as nt


def page_kernel():
    page = (Path(__file__).resolve().parents[1] / "docs" / "index.html").read_text(encoding="utf-8")
    return page.split('<script id="score-kernel">', 1)[1].split("</script>", 1)[0]


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is needed for browser parity")
def test_offline_calculator_agrees_with_python():
    pairs = [
        ("오늘 날씨가 맑습니다", "오늘 날씨는 맑습니다"), ("부산 바다", "부산바다"),
        ("3.5만 원", "35만 원"), ("수수료 1.5%", "수수료 15%"), ("1. .5!", "1.5"),
        ("𝟙.٢😀", "𝟙٢😀"), ("３．５", "35"), ("가.나.", "가나"),
        ("\u00a0가\u001c나\ufeff", "가 나"), ("1.2.3", "1..2.3."),
        ("", ""), ("", "가 나 다"), ("가", ""), ("가나", "나가"),
        ("가" * 8, "가" + "나" * 7), ("가" * 8, "가" * 3 + "나" * 5),
    ]
    cases = [[ref, hyp, mode, keep, norm] for (ref, hyp), mode, keep, norm in itertools.product(
        pairs, ("standard", "normalized"), (True, False), ("", "NFC", "NFD", "NFKC", "NFKD")
    )]
    runner = page_kernel() + """
const cases = JSON.parse(require('fs').readFileSync(0, 'utf8'));
process.stdout.write(JSON.stringify(cases.map(args => scorePair(...args))));
"""
    result = subprocess.run(["node", "-e", runner], input=json.dumps(cases),
                            capture_output=True, text=True, check=True, timeout=30)
    browser = json.loads(result.stdout)
    assert len(browser) == len(cases)
    for actual, (ref, hyp, mode, keep, norm) in zip(browser, cases):
        opts = dict(rate_mode=mode, rm_punctuation=not keep, unicode_normalization=norm or None)
        assert actual["crr"] == nt.get_crr(ref, hyp, **opts)["crr"]
        for name, metric in (("cer", nt.get_cer), ("wer", nt.get_wer)):
            py = metric(ref, hyp, **opts)
            assert actual[name] == {
                "rate": py[name], "insertions": py["insertions"],
                "deletions": py["deletions"], "substitutions": py["substitutions"],
            }


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is needed for browser explanations")
def test_first_screen_distinguishes_unscored_spaces_from_character_edits():
    pairs = [("부산 바다", "부산바다"), ("부산에", "부산은"), ("3.5만 원", "35만 원"),
             ("안녕.", "안녕"), ("a😀 b c", "a😀b c ")]
    runner = page_kernel() + """
const pairs = JSON.parse(require('fs').readFileSync(0, 'utf8'));
process.stdout.write(JSON.stringify(pairs.map(([a,b]) => describe(a,b,scorePair(a,b)))));
"""
    result = subprocess.run(["node", "-e", runner], input=json.dumps(pairs),
                            check=True, capture_output=True, text=True, timeout=30)
    spacing, particle, decimal, punctuation, astral = json.loads(result.stdout)
    assert "4글자" in spacing and "공백 차이 1곳" in spacing
    assert "에 → 은" in particle and "치환" in particle
    assert "‘.’ 한 글자가 빠졌습니다" in decimal
    assert "공백 차이" not in punctuation
    assert "공백 차이 2곳" in astral
