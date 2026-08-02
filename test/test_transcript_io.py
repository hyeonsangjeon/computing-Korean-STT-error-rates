import json
import unittest
from pathlib import Path

import nlptutti as nt

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "transcripts"


def fixture(name):
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


class TestTranscriptParsing(unittest.TestCase):
    def test_equivalent_formats_produce_the_same_text(self):
        parsed = {
            "text": nt.parse_transcript(fixture("equivalent.txt").strip(), "text"),
            "json": nt.parse_transcript(fixture("equivalent.json"), "json"),
            "srt": nt.parse_transcript(fixture("equivalent.srt"), "srt"),
            "tsv": nt.parse_transcript(fixture("equivalent.tsv"), "tsv"),
        }

        for source_format, transcript in parsed.items():
            with self.subTest(source_format=source_format):
                self.assertEqual(transcript["text"], "오늘 날씨가 맑습니다")
                self.assertEqual(transcript["source_format"], source_format)

    def test_text_accepts_utf8_bytes_and_txt_alias(self):
        parsed = nt.parse_transcript("\ufeff안녕하세요".encode("utf-8"), "TXT")

        self.assertEqual(parsed["source_format"], "text")
        self.assertEqual(parsed["text"], "안녕하세요")
        self.assertEqual(parsed["provenance"], {})

    def test_json_preserves_only_documented_metadata_and_raw_timestamps(self):
        parsed = nt.parse_transcript(fixture("equivalent.json"), "json")
        provenance = parsed["provenance"]

        self.assertEqual(provenance["segment_count"], 2)
        self.assertEqual(provenance["json_text_policy"], "text")
        self.assertEqual(provenance["text_source"], "top_level_text")
        self.assertEqual(
            provenance["metadata"],
            {
                "file": "sample.wav",
                "model": "example-model",
                "language": "ko",
                "duration_s": 2.5,
            },
        )
        self.assertEqual(
            provenance["timestamps"],
            [{"start": 0, "end": 1200}, {"start": 1200, "end": 2500}],
        )
        self.assertNotIn("timestamp_unit", provenance)

    def test_json_requires_top_level_text_by_default(self):
        document = {"segments": [{"text": "오늘"}, {"text": "날씨"}]}

        with self.assertRaises(nt.TranscriptFormatError):
            nt.parse_transcript(document, "json")

    def test_json_segment_fallback_is_explicit_and_joins_with_one_space(self):
        document = {
            "segments": [
                {"text": "  오늘\n날씨가  "},
                {"text": "맑습니다"},
            ]
        }

        parsed = nt.parse_transcript(
            document,
            "json",
            json_text_policy="segments_fallback",
        )

        self.assertEqual(parsed["text"], "오늘 날씨가 맑습니다")
        self.assertEqual(parsed["provenance"]["text_source"], "segments")

    def test_json_top_level_text_wins_when_fallback_is_enabled(self):
        parsed = nt.parse_transcript(
            {
                "text": "공식 전체 문장",
                "segments": [{"text": "다른 구간 문장"}],
            },
            "json",
            json_text_policy="segments_fallback",
        )

        self.assertEqual(parsed["text"], "공식 전체 문장")

    def test_srt_multiline_cue_uses_a_single_space(self):
        parsed = nt.parse_transcript(
            "1\n00:00:00,000 --> 00:00:01,000\n첫째 줄\n둘째 줄\n",
            "srt",
        )

        self.assertEqual(parsed["text"], "첫째 줄 둘째 줄")
        self.assertEqual(parsed["provenance"]["timestamp_unit"], "srt_timecode")

    def test_srt_requires_a_blank_line_between_cues(self):
        serialized = (
            "1\n00:00:00,000 --> 00:00:01,000\n첫째\n"
            "2\n00:00:01,000 --> 00:00:02,000\n둘째\n"
        )

        with self.assertRaises(nt.TranscriptFormatError):
            nt.parse_transcript(serialized, "srt")

    def test_tsv_declares_second_based_timestamps(self):
        parsed = nt.parse_transcript(fixture("equivalent.tsv"), "tsv")

        self.assertEqual(parsed["provenance"]["timestamp_unit"], "seconds")
        self.assertEqual(
            parsed["provenance"]["timestamps"][0],
            {"start": "0.0", "end": "1.2"},
        )

    def test_empty_plain_text_and_json_text_are_valid(self):
        self.assertEqual(nt.parse_transcript("", "text")["text"], "")
        self.assertEqual(nt.parse_transcript('{"text": ""}', "json")["text"], "")

    def test_malformed_fixtures_raise_a_specific_error(self):
        for source_format in ("json", "srt", "tsv"):
            with self.subTest(source_format=source_format), self.assertRaises(
                nt.TranscriptFormatError
            ):
                nt.parse_transcript(
                    fixture(f"malformed.{source_format}"),
                    source_format,
                )

    def test_invalid_format_and_policy_are_rejected(self):
        with self.assertRaises(ValueError):
            nt.parse_transcript("text", "xml")
        with self.assertRaises(ValueError):
            nt.parse_transcript(
                '{"text": "text"}',
                "json",
                json_text_policy="automatic",
            )

    def test_invalid_utf8_is_rejected(self):
        with self.assertRaises(nt.TranscriptFormatError):
            nt.parse_transcript(b"\xff\xfe", "text")

    def test_incomplete_or_mixed_json_timestamps_are_rejected(self):
        invalid_documents = [
            {"text": "가", "segments": [{"text": "가", "start": 0}]},
            {
                "text": "가 나",
                "segments": [
                    {"text": "가", "start": 0, "end": 1},
                    {"text": "나"},
                ],
            },
        ]

        for document in invalid_documents:
            with self.subTest(document=document), self.assertRaises(
                nt.TranscriptFormatError
            ):
                nt.parse_transcript(document, "json")

    def test_non_finite_or_reversed_json_times_are_rejected(self):
        invalid_documents = [
            {"text": "가", "duration_s": float("nan")},
            {
                "text": "가",
                "segments": [{"text": "가", "start": 2, "end": 1}],
            },
        ]

        for document in invalid_documents:
            with self.subTest(document=document), self.assertRaises(
                nt.TranscriptFormatError
            ):
                nt.parse_transcript(document, "json")

    def test_invalid_srt_clock_values_are_rejected(self):
        with self.assertRaises(nt.TranscriptFormatError):
            nt.parse_transcript(
                "1\n00:60:00,000 --> 00:60:01,000\n잘못된 시간\n",
                "srt",
            )

    def test_invalid_tsv_rows_and_times_are_rejected(self):
        invalid_inputs = [
            "start\tend\ttext\n0\t1\t가\textra\n",
            "start\tend\ttext\n0\tNaN\t가\n",
            "start\tend\ttext\n2\t1\t가\n",
            "start\tstart\tend\ttext\n0\t0\t1\t가\n",
        ]

        for serialized in invalid_inputs:
            with self.subTest(serialized=serialized), self.assertRaises(
                nt.TranscriptFormatError
            ):
                nt.parse_transcript(serialized, "tsv")


class TestTranscriptEvaluation(unittest.TestCase):
    def test_equivalent_formats_produce_identical_metrics(self):
        inputs = [
            nt.parse_transcript(fixture("equivalent.txt").strip(), "text"),
            nt.parse_transcript(fixture("equivalent.json"), "json"),
            nt.parse_transcript(fixture("equivalent.srt"), "srt"),
            nt.parse_transcript(fixture("equivalent.tsv"), "tsv"),
        ]

        reports = [
            nt.evaluate_transcript(
                "오늘 날씨가 맑습니다",
                transcript,
                rate_mode="standard",
            )
            for transcript in inputs
        ]

        for report in reports:
            self.assertEqual(report["metrics"], reports[0]["metrics"])
            self.assertEqual(report["metrics"]["cer"]["value"], 0.0)
            self.assertEqual(report["metrics"]["wer"]["value"], 0.0)
            self.assertEqual(report["metrics"]["crr"]["value"], 1.0)
            self.assertEqual(
                report["provenance"]["hypothesis"],
                reports[0]["provenance"]["hypothesis"],
            )

    def test_report_preserves_metric_defaults_and_actual_options(self):
        parsed = nt.parse_transcript("STREAM", "text")

        default_report = nt.evaluate_transcript("STEAM", parsed)
        standard_report = nt.evaluate_transcript(
            "STEAM",
            parsed,
            rate_mode="STANDARD",
            unicode_normalization="nfc",
        )

        self.assertAlmostEqual(default_report["metrics"]["cer"]["value"], 1 / 6)
        self.assertEqual(default_report["options"]["rate_mode"], "normalized")
        self.assertIsNone(default_report["options"]["unicode_normalization"])
        self.assertAlmostEqual(standard_report["metrics"]["cer"]["value"], 1 / 5)
        self.assertEqual(standard_report["options"]["rate_mode"], "standard")
        self.assertEqual(standard_report["options"]["unicode_normalization"], "NFC")

    def test_report_is_json_serializable_deterministic_and_excludes_raw_text(self):
        reference = "오늘 날씨가 맑습니다"
        hypothesis = "오늘 날씨는 맑습니다"
        parsed = nt.parse_transcript(hypothesis, "text")

        first = nt.evaluate_transcript(reference, parsed, rate_mode="standard")
        second = nt.evaluate_transcript(reference, parsed, rate_mode="standard")
        serialized = json.dumps(first, ensure_ascii=False, sort_keys=True)

        self.assertEqual(
            serialized, json.dumps(second, ensure_ascii=False, sort_keys=True)
        )
        self.assertNotIn(reference, serialized)
        self.assertNotIn(hypothesis, serialized)
        self.assertEqual(first["schema_version"], "1.0")
        self.assertEqual(first["evaluator"]["name"], "nlptutti")
        self.assertTrue(first["evaluator"]["version"])
        self.assertAlmostEqual(first["metrics"]["cer"]["value"], 1 / 9)
        self.assertAlmostEqual(first["metrics"]["wer"]["value"], 1 / 3)

    def test_report_keeps_timestamps_only_under_provenance(self):
        parsed = nt.parse_transcript(fixture("equivalent.srt"), "srt")
        report = nt.evaluate_transcript("오늘 날씨가 맑습니다", parsed)

        self.assertNotIn("timestamps", report["metrics"])
        self.assertEqual(
            report["provenance"]["source"]["details"]["segment_count"],
            2,
        )
        self.assertIn(
            "timestamps",
            report["provenance"]["source"]["details"],
        )

    def test_report_preserves_substitution_deletion_and_insertion_counts(self):
        cases = [
            ("가다", {"substitutions": 1, "deletions": 0, "insertions": 0}),
            ("가", {"substitutions": 0, "deletions": 1, "insertions": 0}),
            ("가나다", {"substitutions": 0, "deletions": 0, "insertions": 1}),
        ]

        for hypothesis, expected_counts in cases:
            with self.subTest(hypothesis=hypothesis):
                report = nt.evaluate_transcript(
                    "가나",
                    nt.parse_transcript(hypothesis, "text"),
                    rate_mode="standard",
                )
                cer = report["metrics"]["cer"]
                self.assertEqual(cer["value"], 0.5)
                for key, value in expected_counts.items():
                    self.assertEqual(cer[key], value)

    def test_invalid_parsed_transcript_is_rejected(self):
        with self.assertRaises(TypeError):
            nt.evaluate_transcript("정답", {"source_format": "text", "text": 1})
        with self.assertRaises(TypeError):
            nt.evaluate_transcript(
                "정답",
                {
                    "source_format": "text",
                    "text": "가설",
                    "provenance": {"invalid": object()},
                },
            )


if __name__ == "__main__":
    unittest.main()
