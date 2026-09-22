import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import nlptutti as nt
from nlptutti.cli import main


class TestStrictJsonInputs(unittest.TestCase):
    def test_transcript_and_provider_reject_duplicate_and_nonfinite_fields(self):
        common_invalid = [
            '{"text":"first","text":"second"}',
            '{"text":"ok","extra":{"id":1,"id":2}}',
            '{"text":"ok","extra":[{"key":1,"key":2}]}',
        ]
        common_invalid += [
            '{"text":"ok","extra":%s}' % number
            for number in ("NaN", "Infinity", "-Infinity", "1e9999")
        ]
        for payload in common_invalid:
            for parse in (
                lambda value: nt.parse_transcript(value, "json"),
                lambda value: nt.parse_provider_transcript(
                    value, "openai-whisper", schema_version="transcribe-v1"
                ),
            ):
                for value in (payload, payload.encode("utf-8")):
                    with self.subTest(payload=payload), self.assertRaisesRegex(
                        nt.TranscriptFormatError, "duplicate JSON key|finite"
                    ):
                        parse(value)

    def test_cli_rejects_duplicate_ids_systems_text_and_nonfinite_values(self):
        invalid = [
            '{"references":{"u":"first","u":"second"},"systems":{"a":{"u":"second"},"b":{"u":"second"}}}',
            '{"references":["x"],"systems":{"a":["x"],"a":["y"],"b":["x"]}}',
            '{"references":[{"id":"u","text":"x","text":"y"}],"systems":{"a":["x"],"b":["x"]}}',
            '{"references":["x"],"systems":{"a":["x"],"b":["x"]},"unused":NaN}',
            '{"references":["x"],"systems":{"a":["x"],"b":["x"]},"unused":1e9999}',
        ]
        for payload in invalid:
            with self.subTest(
                payload=payload
            ), tempfile.TemporaryDirectory() as directory:
                source, destination = (
                    Path(directory) / "input.json",
                    Path(directory) / "result",
                )
                source.write_text(payload, encoding="utf-8")
                stderr, stdout = io.StringIO(), io.StringIO()
                with contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(
                    stdout
                ), self.assertRaises(SystemExit) as raised:
                    main(["compare", str(source), "--output-dir", str(destination)])
                self.assertEqual(raised.exception.code, 2)
                self.assertEqual(stdout.getvalue(), "")
                self.assertFalse(destination.exists())
                self.assertRegex(stderr.getvalue(), "duplicate JSON key|finite")

    def test_invalid_utf8_and_json_have_controlled_cli_errors(self):
        for payload, message in (
            (b"\xff", "valid UTF-8"),
            (b'{"references":', "line 1, column"),
        ):
            with self.subTest(
                payload=payload
            ), tempfile.TemporaryDirectory() as directory:
                source = Path(directory) / "input.json"
                source.write_bytes(payload)
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr), self.assertRaises(
                    SystemExit
                ) as raised:
                    main(["compare", str(source)])
                self.assertEqual(raised.exception.code, 2)
                self.assertIn(message, stderr.getvalue())
                self.assertNotIn("Traceback", stderr.getvalue())

    def test_normal_mapping_and_serialized_provider_results_agree(self):
        for provider, schema, payload in (
            (
                "azure-speech",
                "short-audio-simple-v1",
                {"RecognitionStatus": "Success", "DisplayText": "서울"},
            ),
            (
                "openai-whisper",
                "transcribe-v1",
                {"text": "서울", "language": "ko", "segments": []},
            ),
        ):
            self.assertEqual(
                nt.parse_provider_transcript(payload, provider, schema_version=schema),
                nt.parse_provider_transcript(
                    json.dumps(payload), provider, schema_version=schema
                ),
            )

    def test_cli_aggregate_mode_and_conflicting_raw_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.json"
            source.write_text(
                json.dumps(
                    {
                        "references": ["가"],
                        "systems": {"private-a": ["나"], "private-b": ["가"]},
                    }
                ),
                encoding="utf-8",
            )
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(
                    main(["compare", str(source), "--privacy-mode", "aggregate"]), 0
                )
            self.assertNotIn("private-a", stdout.getvalue())
            self.assertEqual(
                json.loads(stdout.getvalue())["options"]["privacy_mode"], "aggregate"
            )
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(
                SystemExit
            ):
                main(
                    [
                        "compare",
                        str(source),
                        "--privacy-mode",
                        "aggregate",
                        "--include-transcripts",
                    ]
                )
