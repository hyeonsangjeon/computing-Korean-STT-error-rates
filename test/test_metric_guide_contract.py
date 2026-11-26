import unicodedata

import pytest

import nlptutti as nt

REFERENCE = "오늘 날씨가 맑습니다"
HYPOTHESIS = "오늘 날씨는 맑습니다"


def test_readme_core_metric_example_matches_public_api():
    cer = nt.get_cer(REFERENCE, HYPOTHESIS, rate_mode="standard")
    wer = nt.get_wer(REFERENCE, HYPOTHESIS, rate_mode="standard")
    crr = nt.get_crr(REFERENCE, HYPOTHESIS, rate_mode="standard")

    assert cer == {
        "cer": 1 / 9,
        "substitutions": 1,
        "deletions": 0,
        "insertions": 0,
    }
    assert wer == {
        "wer": 1 / 3,
        "substitutions": 1,
        "deletions": 0,
        "insertions": 0,
    }
    assert crr == {
        "crr": 0.89,
        "substitutions": 1,
        "deletions": 0,
        "insertions": 0,
    }


def test_cer_and_crr_ignore_spaces_while_wer_uses_word_boundaries():
    hypothesis_without_spaces = "오늘날씨가맑습니다"

    assert nt.get_cer(REFERENCE, hypothesis_without_spaces)["cer"] == 0.0
    assert nt.get_crr(REFERENCE, hypothesis_without_spaces)["crr"] == 1.0
    assert nt.get_wer(REFERENCE, hypothesis_without_spaces)["wer"] > 0.0


def test_punctuation_is_removed_by_default_and_can_be_scored():
    assert nt.get_cer("가,나", "가나")["cer"] == 0.0
    assert nt.get_wer("가, 나", "가 나")["wer"] == 0.0

    assert nt.get_cer("가,나", "가나", rm_punctuation=False)["cer"] > 0.0
    assert nt.get_wer("가, 나", "가 나", rm_punctuation=False)["wer"] > 0.0


@pytest.mark.parametrize("ref,hyp,cer", [
    ("3.5만 원", "35만 원", 1 / 5),
    ("수수료 1.5%", "수수료 15%", 1 / 6),
])
def test_decimal_deletion_reaches_every_report(ref, hyp, cer):
    assert nt.get_cer(ref, hyp) == {
        "cer": cer, "substitutions": 0, "deletions": 1, "insertions": 0
    }
    assert nt.get_wer(ref, hyp)["wer"] == 0.5
    assert nt.get_crr(ref, hyp)["crr"] == round(1 - cer, 2)
    explanation = nt.explain_errors(ref, hyp)
    assert explanation["error_frequencies"]["deletions"] == [{"reference": ".", "count": 1}]
    assert nt.explain_errors(ref, hyp, unit="word")["rate"] == 0.5
    corpus = nt.evaluate_corpus([ref], [hyp])
    comparison = nt.compare_systems([ref], {"a": [hyp], "b": [ref]}, include_items=True,
                                    diagnostic_profile="korean-v1")
    transcript = nt.evaluate_transcript(ref, nt.parse_transcript(hyp, "text"))
    for metric in ("cer", "wer", "crr"):
        assert corpus[metric] == comparison["systems"][0]["metrics"][metric]
        assert transcript["metrics"][metric]["value"] == corpus[metric]["micro"]
        assert comparison["details"]["systems"][0]["items"][0]["metrics"][metric] == corpus[metric]
    assert comparison["options"]["punctuation_policy"] == transcript["options"]["punctuation_policy"] == "decimal-aware"
    assert comparison["systems"][0]["diagnostics"]["spacing_boundary"]["skipped_lexical_items"] == 1
    assert comparison["systems"][0]["diagnostics"]["top_character_edits"]["deletions"][0]["reference"] == "."


@pytest.mark.parametrize("text,processed", [
    (" 1 . 5. ", "15"), ("1 .5", "15"), ("1. 5", "15"),
    ("1,!.", "1"), (".5", "5"), ("1..5", "15"), ("1.2.3.", "1.2.3"),
    ("١.٥", "١.٥"), ("３．５", "３５"), ("².³", "²³"), ("1.５", "1.５"),
    ("가\u00a0나", "가\u00a0나"), ("부산\t바다!", "부산바다"),
])
def test_decimal_policy_uses_immediate_neighbors_before_space_removal(text, processed):
    assert nt.explain_errors(text, "")["processed_reference"] == processed


def test_unicode_opt_in_empty_reference_and_entity_offsets():
    assert nt.explain_errors("３．５.", "", unicode_normalization="NFKC")["processed_reference"] == "3.5"
    assert nt.get_cer("...", "1.5", rate_mode="standard")["cer"] == 3
    assert nt.get_cer("...", "1.5")["cer"] == 1
    assert nt.get_crr("", "1.5", rate_mode="standard")["crr"] == -2
    assert nt.get_cer("부산 바다", "부산바다")["cer"] == 0
    assert nt.get_cer("부산은", "부산이")["substitutions"] == 1
    entity = nt.evaluate_entities(["3.5"], ["35"], ["3.5"])
    assert entity["entity_cer"]["deletions"] == 1
    assert entity["entity_cer"]["reference_characters"] == 3


def test_rate_mode_does_not_apply_unicode_normalization():
    composed = "가"
    decomposed = unicodedata.normalize("NFD", composed)

    assert nt.get_cer(composed, decomposed, rate_mode="normalized")["cer"] > 0.0
    assert nt.get_cer(composed, decomposed, rate_mode="standard")["cer"] > 0.0
    assert (
        nt.get_cer(
            composed,
            decomposed,
            rate_mode="standard",
            unicode_normalization="NFC",
        )["cer"]
        == 0.0
    )


def test_crr_is_the_rounded_complement_of_cer_for_the_same_mode():
    for rate_mode in ("normalized", "standard"):
        cer = nt.get_cer("STEAM", "STREAM", rate_mode=rate_mode)["cer"]
        crr = nt.get_crr("STEAM", "STREAM", rate_mode=rate_mode)["crr"]

        assert crr == round(1 - cer, 2)


def test_standard_crr_can_be_negative_when_insertions_exceed_reference_length():
    assert nt.get_crr("", "가나다", rate_mode="standard")["crr"] == -2.0
