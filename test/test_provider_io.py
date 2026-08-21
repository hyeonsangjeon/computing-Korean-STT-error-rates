import json
import unittest
from pathlib import Path

import nlptutti as nt


FIXTURES = Path(__file__).parent / "fixtures" / "providers"


class TestProviderTranscriptAdapters(unittest.TestCase):
    def test_azure_short_audio_simple_fixture(self):
        transcript = nt.parse_provider_transcript(
            (FIXTURES / "azure-short-audio-simple.json").read_bytes(),
            "azure-speech",
            schema_version="short-audio-simple-v1",
        )

        self.assertEqual(transcript["source_format"], "json")
        self.assertEqual(transcript["text"], "회의는 오후 세 시에 시작합니다.")
        self.assertEqual(
            transcript["provenance"]["timing"],
            {"offset": 1200000, "duration": 24700000, "unit": "100ns_tick"},
        )

    def test_whisper_fixture_and_evaluation_are_json_safe(self):
        transcript = nt.parse_provider_transcript(
            (FIXTURES / "openai-whisper-transcribe.json").read_text(
                encoding="utf-8"
            ),
            "openai-whisper",
            schema_version="transcribe-v1",
        )
        report = nt.evaluate_transcript("오늘 회의가 있습니다.", transcript)

        self.assertEqual(transcript["text"], " 오늘 회의가 있습니다.")
        self.assertEqual(
            transcript["provenance"]["metadata"], {"language": "ko"}
        )
        self.assertEqual(transcript["provenance"]["timestamp_unit"], "seconds")
        json.dumps(report, ensure_ascii=False, allow_nan=False)

    def test_empty_successful_results_remain_empty(self):
        azure = nt.parse_provider_transcript(
            {"RecognitionStatus": "Success", "DisplayText": ""},
            "azure-speech",
            schema_version="short-audio-simple-v1",
        )
        whisper = nt.parse_provider_transcript(
            {"text": "", "segments": [], "language": "ko"},
            "openai-whisper",
            schema_version="transcribe-v1",
        )

        self.assertEqual(azure["text"], "")
        self.assertEqual(whisper["text"], "")

    def test_provider_and_schema_are_never_inferred(self):
        with self.assertRaisesRegex(ValueError, "provider must be one of"):
            nt.parse_provider_transcript(
                {}, "auto", schema_version="transcribe-v1"
            )
        with self.assertRaisesRegex(ValueError, "unsupported schema_version"):
            nt.parse_provider_transcript(
                {}, "openai-whisper", schema_version="verbose-json-v2"
            )

    def test_malformed_json_and_non_object_fail_closed(self):
        for payload in ("{", "[]", b"\xff"):
            with self.subTest(payload=payload), self.assertRaises(
                nt.TranscriptFormatError
            ):
                nt.parse_provider_transcript(
                    payload,
                    "openai-whisper",
                    schema_version="transcribe-v1",
                )

    def test_azure_non_success_and_partial_timing_fail_closed(self):
        invalid = [
            {"RecognitionStatus": "NoMatch"},
            {"RecognitionStatus": "Success"},
            {
                "RecognitionStatus": "Success",
                "DisplayText": "문장",
                "Offset": 0,
            },
            {
                "RecognitionStatus": "Success",
                "DisplayText": "문장",
                "Offset": True,
                "Duration": 1,
            },
        ]
        for payload in invalid:
            with self.subTest(payload=payload), self.assertRaises(
                nt.TranscriptFormatError
            ):
                nt.parse_provider_transcript(
                    payload,
                    "azure-speech",
                    schema_version="short-audio-simple-v1",
                )

    def test_whisper_required_fields_and_segment_times_fail_closed(self):
        invalid = [
            {"text": "문장", "segments": []},
            {"text": "문장", "segments": {}, "language": "ko"},
            {
                "text": "문장",
                "segments": [{"text": "문장", "start": 2, "end": 1}],
                "language": "ko",
            },
            {
                "text": "문장",
                "segments": [{"text": "문장", "start": 0}],
                "language": "ko",
            },
        ]
        for payload in invalid:
            with self.subTest(payload=payload), self.assertRaises(
                nt.TranscriptFormatError
            ):
                nt.parse_provider_transcript(
                    payload,
                    "openai-whisper",
                    schema_version="transcribe-v1",
                )


if __name__ == "__main__":
    unittest.main()
