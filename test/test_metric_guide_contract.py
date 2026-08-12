import unicodedata

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
