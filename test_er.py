import unittest
import asr_metrics as metrics


class TestER(unittest.TestCase):

    def test_cer_case_korean(self):
        refs = "아키택트"
        preds = "아키택쳐"
        # S = 1, D = 0, I = 0, N = 4, CER = 1 / 4

        result_metric =  metrics.get_cer(refs, preds)

        char_error_rate = result_metric[0]
        expected_error_rate =  0.25
        self.assertTrue(abs(char_error_rate - expected_error_rate) < 1e-6)



    def test_cer_case_english(self):
        refs = "My hoverscraftis full of eels"
        preds = "My hovercraft is full of eels"
        # S = 0, D = 1, I = 0, N = 25, CER = 1 / 25

        [cer, substitutions, deletions, insertions] =  metrics.get_cer(refs, preds)


        expected_deletion = 1
        expected_error_rate =  0.04
        self.assertTrue((abs(deletions - expected_deletion) == 0) and cer==expected_error_rate)
        # self.assertTrue(self)



    def test_cer_normalized_case(self):
        refs = "STEAM"
        preds = "STREAM"
        [cer, substitutions, deletions, insertions] = metrics.get_cer(refs, preds)
        # S = 0, D = 0, I = 1, N=5, C = 5, CER = 1 / (5+1)
        expected_error_rate = 0.1666666666
        print("cer : ", cer)

        self.assertTrue(abs(cer - expected_error_rate) < 1e-6)


    def test_korean_cer_simple_sentence_case(self):
        refs = "제이 차 세계 대전은 인류 역사상 가장 많은 인명 피해와 재산 피해를 남긴 전쟁이었다"
        preds = "제이차 세계대전은 인류 역사상 가장많은 인명피해와 재산피해를 남긴 전쟁이었다"
        [cer, substitutions, deletions, insertions] = metrics.get_cer(refs, preds)
        # S = 0, D = 0, I = 0, N = 34, CER = 0 / 34
        expected_error_rate =0
        self.assertTrue(abs(cer - expected_error_rate) < 1e-6)



    def test_korean_wer_simple_sentence_case(self):
        refs = "대한민국은 주권 국가 입니다."
        preds = "대한민국은 주권국가 입니다."
        # S = 1, D = 1, I = 0, N = 4, CER = 2 / 4
        [wer, substitutions, deletions, insertions] = metrics.get_wer(refs, preds)
        expected_error_rate =0.5
        self.assertTrue(abs(wer - expected_error_rate) < 1e-6)

    def test_remove_punctuation_case(self):
        refs = "또 다른 방법으로, 데이터를 읽는 작업과 쓰는 작업을 분리합니다!"
        preds = "또! 다른 방법으로 데이터를 읽는 작업과 쓰는 작업을 분리합니다."
        [wer, substitutions, deletions, insertions] = metrics.get_wer(refs, preds, rm_punctuation=True)
        # S = 0, D = 0, I = 0, N = 9, CER = 0 / 9
        expected_error_rate = 0.0
        self.assertTrue(abs(wer - expected_error_rate) < 1e-6)

    # def test_function_case_of_list(self):
    #     refs = ["My", "hoverscraftis"]
    #     preds = ["My", "hove"]
    #
    #     for p, r in zip(preds,refs):
    #         print("p : ",p)
    #         print("r : ", r)
    #
    #     self.assertTrue(self)