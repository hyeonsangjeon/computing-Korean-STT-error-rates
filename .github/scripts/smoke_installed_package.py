import json
import os
import shutil
import subprocess
import tempfile
from importlib import metadata
from pathlib import Path

import nlptutti as metrics


COMPARISON_INPUT = {
    "references": ["오늘 날씨가 맑습니다", "서울은 따뜻합니다"],
    "systems": {
        "baseline": ["오늘 날씨는 맑습니다", "서울은 춥습니다"],
        "candidate": ["오늘 날씨가 맑습니다", "서울은 따뜻합니다"],
    },
}


def _verify_imported_from_installation():
    workspace = os.environ.get("GITHUB_WORKSPACE")
    if not workspace:
        return
    try:
        Path(metrics.__file__).resolve().relative_to(Path(workspace).resolve())
    except ValueError:
        return
    raise AssertionError(
        f"nlptutti was imported from the source tree: {metrics.__file__}"
    )


def _verify_readme_fixture():
    workspace = os.environ.get("GITHUB_WORKSPACE")
    if not workspace:
        return
    fixture = Path(workspace) / "examples" / "comparison_input.json"
    assert json.loads(fixture.read_text(encoding="utf-8")) == COMPARISON_INPUT


def _verify_compare_api():
    report = metrics.compare_systems(
        COMPARISON_INPUT["references"],
        COMPARISON_INPUT["systems"],
        rate_mode="standard",
    )
    baseline, candidate = report["systems"]
    assert round(baseline["metrics"]["cer"]["micro"], 4) == 0.2353
    assert baseline["metrics"]["wer"]["micro"] == 0.4
    assert baseline["metrics"]["crr"]["micro"] == 0.76
    assert candidate["metrics"]["cer"]["micro"] == 0.0
    assert candidate["metrics"]["wer"]["micro"] == 0.0
    assert candidate["metrics"]["crr"]["micro"] == 1.0


def _verify_console_script():
    executable = shutil.which("nlptutti")
    assert executable is not None, "wheel did not install the nlptutti console script"
    help_result = subprocess.run(
        [executable, "--help"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "compare" in help_result.stdout

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        input_path = root / "comparison_input.json"
        output_dir = root / "comparison-report"
        input_path.write_text(
            json.dumps(COMPARISON_INPUT, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        subprocess.run(
            [
                executable,
                "compare",
                str(input_path),
                "--rate-mode",
                "standard",
                "--output-dir",
                str(output_dir),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        json_report = json.loads(
            (output_dir / "report.json").read_text(encoding="utf-8")
        )
        markdown_report = (output_dir / "report.md").read_text(encoding="utf-8")

    assert json_report["schema"] == "nlptutti.comparison/1.0"
    assert json_report["systems"][1]["metrics"]["cer"]["micro"] == 0.0
    assert "| candidate | 0.000000 |" in markdown_report


def main():
    _verify_imported_from_installation()
    _verify_readme_fixture()

    package_path = Path(metrics.__file__).resolve().parent
    assert (package_path / "py.typed").is_file()

    reference = "오늘 날씨가 맑습니다"
    hypothesis = "오늘 날씨는 맑습니다"
    cer = metrics.get_cer(reference, hypothesis, rate_mode="standard")
    wer = metrics.get_wer(reference, hypothesis, rate_mode="standard")
    crr = metrics.get_crr(reference, hypothesis, rate_mode="standard")

    assert set(cer) == {"cer", "substitutions", "deletions", "insertions"}
    assert set(wer) == {"wer", "substitutions", "deletions", "insertions"}
    assert set(crr) == {"crr", "substitutions", "deletions", "insertions"}
    assert round(cer["cer"], 4) == 0.1111
    assert round(wer["wer"], 4) == 0.3333
    assert crr["crr"] == 0.89
    assert cer["substitutions"] == 1
    assert wer["substitutions"] == 1
    assert crr["substitutions"] == 1

    transcript = metrics.parse_transcript(
        {"text": hypothesis, "language": "ko"},
        "json",
    )
    report = metrics.evaluate_transcript(
        reference,
        transcript,
        rate_mode="standard",
    )

    assert round(report["metrics"]["cer"]["value"], 4) == 0.1111
    assert round(report["metrics"]["wer"]["value"], 4) == 0.3333
    assert report["evaluator"]["version"] == metadata.version("nlptutti")
    assert report["provenance"]["source"]["format"] == "json"
    _verify_compare_api()
    _verify_console_script()
    print(f"verified installed nlptutti {report['evaluator']['version']}")


if __name__ == "__main__":
    main()
