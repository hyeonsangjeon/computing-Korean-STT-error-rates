import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from nlptutti.cli import main


class TestCli(unittest.TestCase):
    def test_compare_prints_json_for_ordered_collections(self):
        document = {
            "references": ["가", "나"],
            "systems": {"a": ["가", "다"], "b": ["가", "나"]},
        }
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "input.json"
            input_path.write_text(
                json.dumps(document, ensure_ascii=False), encoding="utf-8"
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exit_code = main(
                    ["compare", str(input_path), "--rate-mode", "standard"]
                )

        report = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(report["systems"][1]["metrics"]["wer"]["micro"], 0)

    def test_compare_accepts_id_text_objects_and_writes_output(self):
        document = {
            "references": [{"id": "u1", "text": "가"}],
            "systems": {
                "a": [{"id": "u1", "text": "나"}],
                "b": [{"id": "u1", "text": "가"}],
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "input.json"
            output_path = Path(directory) / "report.json"
            input_path.write_text(
                json.dumps(document, ensure_ascii=False), encoding="utf-8"
            )

            exit_code = main(["compare", str(input_path), "--output", str(output_path)])
            report = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(report["dataset"]["item_count"], 1)

    def test_compare_writes_json_and_markdown_bundle(self):
        document = {
            "references": ["가"],
            "systems": {"a": ["나"], "b": ["가"]},
        }
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "input.json"
            output_dir = Path(directory) / "bundle"
            input_path.write_text(
                json.dumps(document, ensure_ascii=False), encoding="utf-8"
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exit_code = main(
                    ["compare", str(input_path), "--output-dir", str(output_dir)]
                )

            json_report = json.loads(
                (output_dir / "report.json").read_text(encoding="utf-8")
            )
            markdown_report = (output_dir / "report.md").read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertEqual(json_report["schema"], "nlptutti.comparison/1.0")
        self.assertIn("Nlptutti comparison report", markdown_report)

    def test_compare_enables_korean_diagnostics_explicitly(self):
        document = {
            "references": ["부산 바다"],
            "systems": {"a": ["부산바다"], "b": ["부산 바다"]},
        }
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "input.json"
            input_path.write_text(
                json.dumps(document, ensure_ascii=False), encoding="utf-8"
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exit_code = main(
                    [
                        "compare",
                        str(input_path),
                        "--diagnostic-profile",
                        "korean-v1",
                    ]
                )

        report = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(report["options"]["diagnostic_profile"], "korean-v1")
        self.assertEqual(
            report["systems"][0]["diagnostics"]["spacing_boundary"][
                "missing_boundaries"
            ],
            1,
        )


if __name__ == "__main__":
    unittest.main()
