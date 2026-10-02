import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path

import nlptutti as nt
from nlptutti.cli import main
from nlptutti.manifest import MANIFEST_SCHEMA, load_comparison_manifest


class TestManifest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.path = self.root / "평가 목록.json"
        self.formats = {
            "text": "서울 날씨",
            "json": '{"text":"서울 날씨", "file":"PRIVATE-PATH", "model":"SECRET-MODEL"}',
            "srt": "1\r\n00:00:00,000 --> 00:00:01,000\r\n서울 날씨\r\n",
            "tsv": "start\tend\ttext\r\n0\t1\t서울 날씨\r\n",
        }
        for format_, content in self.formats.items():
            (self.root / ("입력." + format_)).write_bytes(content.encode("utf-8"))
        self.manifest = {
            "schema": MANIFEST_SCHEMA,
            "references": [self.entry("text")],
            "systems": {key: [self.entry(key)] for key in self.formats},
        }

    def entry(self, format_):
        return {"id": "PRIVATE-ID", "path": "입력." + format_, "source_format": format_}

    def write(self, manifest=None):
        self.path.write_text(
            json.dumps(manifest or self.manifest, ensure_ascii=False), encoding="utf-8"
        )

    def run_cli(self, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(
                main(["compare", str(self.path), "--input-format", "manifest", *args]),
                0,
            )
        return json.loads(output.getvalue())

    def test_equivalent_formats_and_minimal_provenance(self):
        self.write()
        report = self.run_cli(
            "--unicode-normalization", "NFC", "--privacy-mode", "aggregate"
        )
        for system in report["systems"]:
            self.assertEqual(system["metrics"]["cer"]["micro"], 0)
            self.assertEqual(system["metrics"]["wer"]["micro"], 0)
            self.assertEqual(system["metrics"]["crr"]["micro"], 1)
        self.assertEqual(
            [s["id"] for s in report["input_sources"]["systems"]],
            ["system-1", "system-2", "system-3", "system-4"],
        )
        serialized = nt.render_comparison_json(report)
        for private in ("PRIVATE", "SECRET", "서울", "입력", str(self.root)):
            self.assertNotIn(private, serialized)
        self.assertEqual(len(report["input_sources"]["manifest_sha256"]), 64)
        for source in report["input_sources"]["systems"]:
            self.assertEqual(source["files"][0]["item_index"], 0)
        nt.render_comparison_markdown(report)

    def test_explicit_provider_schema_and_config(self):
        azure = {"RecognitionStatus": "Success", "DisplayText": "서울 날씨"}
        (self.root / "azure.json").write_text(json.dumps(azure), encoding="utf-8")
        whisper = {
            "text": "서울 날씨",
            "language": "ko",
            "segments": [],
            "model": "PRIVATE",
        }
        (self.root / "whisper.json").write_text(json.dumps(whisper), encoding="utf-8")
        self.manifest["systems"] = {
            "a": [
                dict(
                    self.entry("json"),
                    path="azure.json",
                    provider="azure-speech",
                    schema_version="short-audio-simple-v1",
                )
            ],
            "b": [
                dict(
                    self.entry("json"),
                    path="whisper.json",
                    provider="openai-whisper",
                    schema_version="transcribe-v1",
                )
            ],
        }
        config = self.root / "config.json"
        config.write_text(
            json.dumps(
                {
                    "keywords": ["서울"],
                    "entities": ["서울"],
                    "entity_aliases": {"서울": ["서울시"]},
                }
            ),
            encoding="utf-8",
        )
        self.write()
        report = self.run_cli("--evaluation-config", str(config))
        self.assertTrue(report["evaluation_config"]["keywords"])
        self.assertTrue(report["evaluation_config"]["entity_aliases"])
        self.assertEqual(report["systems"][0]["keywords"]["summary"]["recall"], 1)
        source = report["input_sources"]["systems"][0]["files"][0]
        self.assertEqual(source["provider"], "azure-speech")
        self.assertEqual(source["schema_version"], "short-audio-simple-v1")
        self.assertNotIn(
            "PRIVATE", nt.render_comparison_json(report).replace("PRIVATE-ID", "")
        )

    def test_missing_duplicate_or_mismatched_ids_fail(self):
        for value in (None, "", "missing"):
            manifest = copy.deepcopy(self.manifest)
            manifest["systems"]["json"][0]["id"] = value
            self.write(manifest)
            with self.subTest(value=value), self.assertRaises(ValueError):
                load_comparison_manifest(self.path)
        self.manifest["references"] *= 2
        self.write()
        with self.assertRaisesRegex(ValueError, "unique"):
            load_comparison_manifest(self.path)

    def test_bad_contract_does_not_write_output(self):
        mutations = [
            {"provider": "azure-speech"},
            {"schema_version": "v1"},
            {"source_format": "auto"},
            {"json_text_policy": "segments_fallback"},
            {"path": "not-here"},
            {"unknown": True},
        ]
        for mutation in mutations:
            document = copy.deepcopy(self.manifest)
            document["references"][0].update(mutation)
            self.write(document)
            output = self.root / "absent"
            with self.subTest(mutation=mutation), contextlib.redirect_stderr(
                io.StringIO()
            ), self.assertRaises(SystemExit) as caught:
                main(
                    [
                        "compare",
                        str(self.path),
                        "--input-format",
                        "manifest",
                        "--output-dir",
                        str(output),
                    ]
                )
            self.assertEqual(caught.exception.code, 2)
            self.assertFalse(output.exists())

    def test_duplicate_json_keys_and_bad_utf8(self):
        for payload in (b'{"schema":1,"schema":2}', b"\xff"):
            self.path.write_bytes(payload)
            with self.assertRaises(ValueError):
                load_comparison_manifest(self.path)

    def test_config_unknown_option_fails_closed(self):
        self.write()
        config = self.root / "config.json"
        config.write_text('{"keyword":["typo"]}', encoding="utf-8")
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(
            SystemExit
        ) as caught:
            self.run_cli("--evaluation-config", str(config))
        self.assertEqual(caught.exception.code, 2)
