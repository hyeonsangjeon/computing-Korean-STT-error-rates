import inspect
import unittest

import nlptutti as nt
from nlptutti.comparison_types import ComparisonReport


class TestComparisonTypeContract(unittest.TestCase):
    def test_schema_identifier_and_public_type_are_importable(self):
        self.assertEqual(nt.COMPARISON_SCHEMA, "nlptutti.comparison/1.0")
        self.assertIs(nt.ComparisonReport, ComparisonReport)

    def test_existing_public_signatures_keep_historical_defaults(self):
        expected = {
            "get_cer": (
                (
                    "reference",
                    "transcription",
                    "rm_punctuation",
                    "rate_mode",
                    "unicode_normalization",
                ),
                {
                    "rm_punctuation": True,
                    "rate_mode": "normalized",
                    "unicode_normalization": None,
                },
                {"rate_mode", "unicode_normalization"},
            ),
            "get_wer": (
                (
                    "reference",
                    "transcription",
                    "rm_punctuation",
                    "rate_mode",
                    "unicode_normalization",
                ),
                {
                    "rm_punctuation": True,
                    "rate_mode": "normalized",
                    "unicode_normalization": None,
                },
                {"rate_mode", "unicode_normalization"},
            ),
            "get_crr": (
                (
                    "reference",
                    "transcription",
                    "rm_punctuation",
                    "rate_mode",
                    "unicode_normalization",
                ),
                {
                    "rm_punctuation": True,
                    "rate_mode": "normalized",
                    "unicode_normalization": None,
                },
                {"rate_mode", "unicode_normalization"},
            ),
            "parse_transcript": (
                ("data", "source_format", "json_text_policy"),
                {"json_text_policy": "text"},
                {"json_text_policy"},
            ),
        }

        for name, (parameter_names, defaults, keyword_only) in expected.items():
            with self.subTest(name=name):
                parameters = inspect.signature(getattr(nt, name)).parameters
                self.assertEqual(tuple(parameters), parameter_names)
                self.assertEqual(
                    {
                        parameter_name: parameters[parameter_name].default
                        for parameter_name in defaults
                    },
                    defaults,
                )
                self.assertEqual(
                    {
                        parameter_name
                        for parameter_name, parameter in parameters.items()
                        if parameter.kind is inspect.Parameter.KEYWORD_ONLY
                    },
                    keyword_only,
                )

    def test_existing_public_names_remain_exported(self):
        historical_names = {
            "COMPLEX_EOMI",
            "COMPLEX_JOSA",
            "TranscriptFormatError",
            "calculate_keyword_error_rate_with_pattern",
            "evaluate_corpus",
            "evaluate_entities",
            "evaluate_keywords",
            "evaluate_transcript",
            "explain_errors",
            "get_cer",
            "get_crr",
            "get_wer",
            "make_keyword_pattern",
            "parse_transcript",
        }

        self.assertTrue(historical_names.issubset(set(nt.__all__)))


if __name__ == "__main__":
    unittest.main()
