import itertools
import unittest

from nlptutti.alignment import align_sequences
from nlptutti.asr_metrics import _align_sequences, levenshtein
from nlptutti.entity_metrics import _align_with_indices


class TestSharedAlignment(unittest.TestCase):
    def test_tie_breaking_golden_paths_are_preserved(self):
        cases = [
            (
                "ab",
                "ba",
                [
                    {"type": "substitute", "reference": "a", "hypothesis": "b"},
                    {"type": "substitute", "reference": "b", "hypothesis": "a"},
                ],
            ),
            (
                "aba",
                "bab",
                [
                    {"type": "delete", "reference": "a", "hypothesis": ""},
                    {"type": "equal", "reference": "b", "hypothesis": "b"},
                    {"type": "equal", "reference": "a", "hypothesis": "a"},
                    {"type": "insert", "reference": "", "hypothesis": "b"},
                ],
            ),
        ]

        for reference, hypothesis, expected in cases:
            with self.subTest(reference=reference, hypothesis=hypothesis):
                self.assertEqual(
                    _align_sequences(list(reference), list(hypothesis)), expected
                )

    def test_entity_wrapper_uses_the_shared_indexed_path(self):
        reference = list("aba")
        hypothesis = list("bab")

        self.assertEqual(
            _align_with_indices(reference, hypothesis),
            align_sequences(reference, hypothesis),
        )

    def test_exhaustive_small_inputs_match_legacy_edit_counts(self):
        strings = [""]
        for length in range(1, 4):
            strings.extend(
                "".join(values)
                for values in itertools.product("가나", repeat=length)
            )

        for reference in strings:
            for hypothesis in strings:
                with self.subTest(reference=reference, hypothesis=hypothesis):
                    _, expected = levenshtein(hypothesis, reference)
                    alignment = align_sequences(list(reference), list(hypothesis))
                    actual = (
                        sum(item["type"] == "substitute" for item in alignment),
                        sum(item["type"] == "insert" for item in alignment),
                        sum(item["type"] == "delete" for item in alignment),
                    )
                    self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
