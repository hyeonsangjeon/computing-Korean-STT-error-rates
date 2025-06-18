import unittest
import re
import sys
import os
# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from nlptutti.asr_metrics import make_keyword_pattern, COMPLEX_JOSA, calculate_keyword_error_rate_with_pattern


class TestMakeKeywordPattern(unittest.TestCase):

    def test_keyword_error_rate_check(self):
        keyword = "삼성전자"
        pattern = make_keyword_pattern(keyword, COMPLEX_JOSA, ["다", "합니다", "합니다만", "했었다", "한다면", "한다니까", "하고", "하는데", "했다", "했었지", "하려면"])
        test_cases = [
            "삼성전자",          # O
            "삼성전자의",        # O
            "삼성 전자의",       # O
            "삼성전자에서부터",   # O
            "삼성 전자에서부터",  # O
            "삼성전자까지도",     # O
            "삼성전자한다",       # O
            "삼성전자 합니다",    # O
            "삼성전자 했었다",    # O
            "삼성전자에서",       # O
            "삼성전자와도",       # O
            "애플은"             # X
        ]
        for case in test_cases:
            print("\nTesting case:", case)
            print(case, "→", bool(pattern.search(case)))
        
        
        self.assertEqual(bool(pattern.search("삼성전자")), True)
        self.assertEqual(bool(pattern.search("삼성전자의")), True)
        self.assertEqual(bool(pattern.search("삼성 전자의")), True)
        self.assertEqual(bool(pattern.search("삼성전자에서부터")), True)
        self.assertEqual(bool(pattern.search("삼성 전자에서부터")), True)
        self.assertEqual(bool(pattern.search("삼성전자까지도")), True)
        self.assertEqual(bool(pattern.search("삼성전자한다")), True)
        self.assertEqual(bool(pattern.search("삼성전자 합니다")), True)
        self.assertEqual(bool(pattern.search("삼성전자 했었다")), True)
        self.assertEqual(bool(pattern.search("삼성전자에서")), True)
        self.assertEqual(bool(pattern.search("삼성전자와도")), True)
        self.assertEqual(bool(pattern.search("애플은")), False)
        
    def test_calculate_keyword_error_rate_with_pattern(self):
        # 복잡한 조사, 어미 리스트 예시
        COSTOM_COMPLEX_JOSA = [
            "의", "에", "에서", "도", "만", "를", "을", "이", "가", "과", "와", "으로", "로", "부터",
            "까지", "에게", "께", "한테", "밖에", "마저", "이나", "나", "며", "든지", "라도", "조차",
            "에서부터", "에게서", "으로부터", "까지도", "밖에도", "이라도", "이나마", "라도나", "와도", "도만", "에도", "조차도", "치고는"
        ]
        CUSTOM_COMPLEX_EOMI = [
            "다", "니다", "합니다", "했다", "하고", "하는데", "했었다", "한다면", "한다니까", "하니", "하더니", "하여도", "하더라도", "했었지", "하려면"
        ]
        
        reference_sentences = [
            "오늘은 메리츠화재의 주식이 올랐습니다.",
            "애플은 새로운 아이폰을 발표했습니다.",
            "구글은 검색 서비스를 제공합니다.",
            "메리츠화재에서부터 새로운 변화가 시작되었습니다.",
            "나는 메리츠화재까지도 믿었었다.",
            "메리츠화재 한다면 한다.",
            "메리츠화재 한다니까."
        ]
        hypothesis_sentences = [
            "오늘은 매리츠화제의 주식이 올랐습니다.",        # 매리츠화제(오류)
            "애플은 새로운 아이푼을 발표했습니다.",         # 애플(정확), 아이폰 → 아이푼 (오류)
            "구글은 검생 서비스를 제공합니다.",           # 구글(정확)
            "메리츠화재에서부터 새로운 변화가 시작되었습니다.",  # 메리츠화재(정확)
            "나는 매리치화제까지도 믿었었다.",              # 메리츠화재 → 매리치화제 (오류)
            "메리츠 화재 한다면 한다.",                   # 메리츠화재(정확, 띄어쓰기 있어도 인식)
            "메리츠 화재 한다니까."                      # 메리츠화재(정확, 띄어쓰기 있어도 인식)
        ]
        keywords = ["메리츠화재", "애플", "구글", "아이폰"]
        result = calculate_keyword_error_rate_with_pattern(
            reference_sentences,
            hypothesis_sentences,
            keywords,
            COSTOM_COMPLEX_JOSA,
            CUSTOM_COMPLEX_EOMI
        )
        print("\n=== 개별 키워드 결과 ===")
        for kw, stats in result["keywords"].items():
            print(f"'{kw}': 총 {stats['total']}회, 정확 {stats['correct']}회, 오류 {stats['errors']}회")
            print(f"        정확도: {stats['accuracy']:.1%}, 에러율: {stats['error_rate']:.1%}")
        
        print("\n=== 전체 키워드 요약 ===")
        summary = result["summary"]
        print(f"전체 키워드 등장 횟수: {summary['total_keywords']}")
        print(f"정확히 인식된 키워드: {summary['correct_keywords']}")
        print(f"오류가 발생한 키워드: {summary['incorrect_keywords']}")
        print(f"전체 키워드 에러율: {summary['keyword_error_rate']:.1%}")
        
        # 예상 결과 검증
        expected_keywords = {
            "메리츠화재": {"total": 5, "correct": 3, "errors": 2, "accuracy": 0.6, "error_rate": 0.4},
            "애플": {"total": 1, "correct": 1, "errors": 0, "accuracy": 1.0, "error_rate": 0.0},
            "구글": {"total": 1, "correct": 1, "errors": 0, "accuracy": 1.0, "error_rate": 0.0},
            "아이폰": {"total": 1, "correct": 0, "errors": 1, "accuracy": 0.0, "error_rate": 1.0}
        }
        
        expected_summary = {
            "total_keywords": 8,      # 5 + 1 + 1 + 1
            "correct_keywords": 5,    # 3 + 1 + 1 + 0  
            "incorrect_keywords": 3,  # 2 + 0 + 0 + 1
            "keyword_error_rate": 0.375  # 3/8 = 0.375
        }

        self.assertEqual(result["keywords"], expected_keywords)
        self.assertEqual(result["summary"], expected_summary)


if __name__ == '__main__':
    unittest.main()