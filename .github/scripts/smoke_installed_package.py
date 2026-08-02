import os
from importlib import metadata
from pathlib import Path

import nlptutti as metrics


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


def main():
    _verify_imported_from_installation()

    reference = "오늘 날씨가 맑습니다"
    hypothesis = "오늘 날씨는 맑습니다"
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
    print(f"verified installed nlptutti {report['evaluator']['version']}")


if __name__ == "__main__":
    main()
