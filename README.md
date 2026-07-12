[![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)](https://github.com/hyeonsangjeon/computing-Korean-STT-error-rates/blob/main/LICENSE)
[![Downloads](https://static.pepy.tech/badge/nlptutti)](https://pepy.tech/project/nlptutti)
[![PyPI version](https://badge.fury.io/py/nlptutti.svg)](https://pypi.org/project/nlptutti/)
[![Tests](https://github.com/hyeonsangjeon/computing-Korean-STT-error-rates/actions/workflows/test.yml/badge.svg)](https://github.com/hyeonsangjeon/computing-Korean-STT-error-rates/actions/workflows/test.yml)
[![Tested Python](https://img.shields.io/badge/tested%20python-3.8%20%7C%203.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue?style=flat-square)](https://github.com/hyeonsangjeon/computing-Korean-STT-error-rates/actions/workflows/test.yml)
# 한국어 자동 음성 인식 오류율 측정 패키지

Amazon Transcribe와 같은 음성 인식기의 한국어 출력에 대해 문자 오류율(CER), 단어 오류율(WER), 문자 정답률(CRR)을 계산하는 Python 패키지입니다.
정답 문장(reference)과 인식 문장(hypothesis) 사이의 Levenshtein 최소 편집거리에서 치환, 삭제, 삽입 횟수를 계산합니다.

문자 오류율(CER/WER)은 자동 음성 인식 시스템의 성능에 대한 일반적인 메트릭입니다. CER은 WER(단어 오류율)과 유사하지만 단어 대신 문자에 대해 작동합니다. 자세한 내용은 WER 문서를 참조하십시오.[1]
문자 오류율은 다음과 같이 계산할 수 있습니다. 

---

<img src="https://raw.githubusercontent.com/hyeonsangjeon/computing-Korean-STT-error-rates/main/pic/ER_CASE.png" width="90%">

---

<img src="https://raw.githubusercontent.com/hyeonsangjeon/computing-Korean-STT-error-rates/main/pic/FORMULA_CASE.png" width="70%">

---

표준 CER/WER:

~~~text
(S + D + I) / (S + D + C)
~~~

Nlptutti 기본 정규화 오류율:

~~~text
(S + D + I) / (S + D + I + C)
~~~

- S: 치환(substitution)
- D: 삭제(deletion)
- I: 삽입(insertion)
- C: 올바르게 인식한 문자 또는 단어(hit)

> **호환성 정책:** <code>rate_mode</code>를 생략하면 기존 버전과 동일한 <code>rate_mode="normalized"</code>가 적용됩니다. 표준 CER/WER가 필요한 경우에만 <code>rate_mode="standard"</code>를 명시하십시오. 기본값은 기존 사용자 결과 보호를 위해 변경하지 않습니다.

### 국내관련발표기고
클라우드와 오픈소스 위스퍼를 이용한 한국어 음성 텍스트 변환
- http://www.itdaily.kr/news/articleView.html?idxno=213297
- http://www.comworld.co.kr/news/articleView.html?idxno=50818

### 개발 배경 글
이 패키지를 만들게 된 배경과 한국어 ASR/STT 평가 실험을 정리한 프롤로그 글입니다.
- Korean: https://hyeonsangjeon.github.io/job-transcribe/
- English: https://hyeonsangjeon.github.io/job-transcribe/en/

### 사용자 매뉴얼
설치부터 CER/WER/CRR, 코퍼스 평가, 키워드·개체명 보존 평가, 오류 상세 분석까지 함수별 예제를 제공합니다.
- Korean manual: https://hyeonsangjeon.github.io/job-transcribe/nlptutti/

### 사용방법 
가장 간단한 사용 사례는 두 문자열 간의 편집 거리를 계산하는 것입니다.
```bash
pip install nlptutti
```

### 평가 정책
- 기존 호출의 기본 계산식은 계속 <code>rate_mode="normalized"</code>입니다. 표준식은 <code>rate_mode="standard"</code>를 직접 지정할 때만 사용합니다.
- 유니코드 정규화는 기존 결과 보호를 위해 기본적으로 적용하지 않습니다. 필요한 경우 <code>unicode_normalization="NFC"</code>를 지정합니다.
- `get_cer("", "")`, `get_wer("", "")`처럼 참조문장과 가설문장이 모두 비어 있으면 완전 일치로 보고 오류율 `0.0`을 반환합니다.
- 참조문장은 비어 있고 가설문장만 있는 경우에는 전체를 삽입 오류로 계산합니다.
- CER/CRR 계산에서는 `rm_punctuation` 값과 관계없이 공백을 제거합니다. `rm_punctuation`은 문장부호 제거 여부만 제어합니다.
- 키워드 패턴은 정규식 특수문자를 포함한 키워드도 안전하게 처리하며, 긴 단어 내부의 부분문자열 오탐을 줄이기 위해 키워드 앞뒤 경계를 검사합니다.
- `calculate_keyword_error_rate_with_pattern`은 참조문장 리스트와 STT 결과 리스트의 길이가 다르면 `ValueError`를 발생시킵니다.

#### CER

```python
import nlptutti as metrics

refs = "아키택트"
preds = "아키택쳐"
result = metrics.get_cer(refs, preds)
# result -> {"cer": 0.25, "substitutions": 1, "deletions": 0, "insertions": 0}
```

```python
import nlptutti as metrics

refs = "제이 차 세계 대전은 인류 역사상 가장 많은 인명 피해와 재산 피해를 남긴 전쟁이었다."
preds = "제이차 세계대전은 인류 역사상 가장많은 인명피해와 재산피해를 남긴 전쟁이었다."
result = metrics.get_cer(refs, preds)
cer = result['cer']
substitutions = result['substitutions']
deletions = result['deletions']
insertions = result['insertions']
# prints: [cer, substitutions, deletions, insertions] -> [CER = 0 / 34, S = 0, D = 0, I = 0]
```

#### WER

```python
import nlptutti as metrics

refs = "대한민국은 주권 국가 입니다."
preds = "대한민국은 주권국가 입니다."
result = metrics.get_wer(refs, preds)

wer = result['wer']
substitutions = result['substitutions']
deletions = result['deletions']
insertions = result['insertions']
# prints: [wer, substitutions, deletions, insertions] -> [WER =  2 / 4, S = 1, D = 1, I = 0]
```

#### CRR

```python
import nlptutti as metrics

refs = "제이 차 세계 대전은 인류 역사상 가장 많은 인명 피해와 재산 피해를 남긴 전쟁이었다."
preds = "제이차 세계대전은 인류 역사상 가장많은 인명피해와 재산피해를 남긴 전쟁이었다."
result = metrics.get_crr(refs, preds)
crr = result['crr']
substitutions = result['substitutions']
deletions = result['deletions']
insertions = result['insertions']
# prints: [crr, substitutions, deletions, insertions] -> [CRR = 1 - (0 / 34), S = 0, D = 0, I = 0]
```


### 정규화 방식 선택

기존 코드와 같은 값이 필요하면 옵션을 생략합니다. 표준 CER/WER를 보고할 때만 <code>rate_mode="standard"</code>를 지정합니다.

~~~python
import nlptutti as metrics

default_result = metrics.get_cer("STEAM", "STREAM")
standard_result = metrics.get_cer("STEAM", "STREAM", rate_mode="standard")

print(default_result["cer"])   # 0.16666666666666666
print(standard_result["cer"])  # 0.2
~~~

### 코퍼스 평가 (evaluate_corpus)

여러 문장을 한 번에 평가하고 micro/macro CER·WER와 문장 오류율을 확인합니다.

~~~python
import nlptutti as metrics

report = metrics.evaluate_corpus(
    ["가나", "다라"],
    ["가마", "다라바"],
)

print(report["cer"]["micro"])  # 0.4
print(report["cer"]["macro"])  # 0.41666666666666663
~~~

### 키워드·개체명 보존 평가 (evaluate_keywords)

문장별 실제 언급 횟수를 기준으로 누락과 추가 인식을 함께 집계합니다. 라벨 딕셔너리를 넘기면 ORG, PRODUCT 같은 유형별 결과도 제공합니다. 이 함수는 키워드 목록을 평가하며 NER 모델을 실행하지는 않습니다.

~~~python
import nlptutti as metrics

report = metrics.evaluate_keywords(
    ["삼성전자와 삼성전자가 협력했다.", "애플이 발표했다."],
    ["삼성전자가 협력했다.", "애플과 삼성전자가 발표했다."],
    {"ORG": ["삼성전자", "애플"]},
)

print(report["keywords"]["삼성전자"]["false_negatives"])  # 1
print(report["keywords"]["삼성전자"]["false_positives"])  # 1
print(report["summary"]["f1"])  # 0.6666666666666666
~~~

### 오류 상세 분석 (explain_errors)

점수만으로 원인을 찾기 어려울 때 문자 또는 단어 단위 정렬과 오류 빈도를 확인합니다.

~~~python
import nlptutti as metrics

detail = metrics.explain_errors("아키택트", "아키택쳐")

print(detail["counts"])
# {"hits": 3, "substitutions": 1, "deletions": 0, "insertions": 0}

print(detail["error_frequencies"]["substitutions"])
# [{"reference": "트", "hypothesis": "쳐", "count": 1}]
~~~

### 전처리 예 

#### 띄어쓰기 
가설 또는 정답 텍스트에 일부 전처리 단계를 적용해야 할 수 있습니다. 
한국어 문장 구성은 단어간 띄어쓰기의 모호성으로 CER계산에서 공백을 계산하지 않았습니다. 근대 이전까지 동양의 언어에는 ‘띄어쓰기’ 개념이 존재하지 않았고, 한국어는 맞춤법 상 띄어쓰기 규칙이 정해져 있기는 하나, 띄어쓰기를 지키지 않아도 문장의 맥락을 이해하는데 큰 무리가 없는 언어입니다.
따라서 CER 계산에서 입력 변수의 whitespace는 제거합니다. 
공백 문자는 \t, \n, \r, \x0b 및 \x0c와 whitespace입니다.
```text
ref = '또 다른 방법으로 데이터를 읽는 작업과 쓰는 작업을 분리합니다'
refs ->  또다른방법으로데이터를읽는작업과쓰는작업을분리합니다
```

#### 구두점 처리 
STT 인식기에 따라 구두점을 처리하지 않는 경우가 많습니다. 입력 변수의 구두점 필터링은 flag처리로 사용할 수 있습니다. 필터링 기본값은 True입니다. 구두점 문자는: 

```text
구두점 filter-> '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'
```
```python
import nlptutti as metrics
refs = "또 다른 방법으로, 데이터를 읽는 작업과 쓰는 작업을 분리합니다!"
preds = "또! 다른 방법으로 데이터를 읽는 작업과 쓰는 작업을 분리합니다."
result = metrics.get_wer(refs, preds, rm_punctuation=True)

# prints: wer -> 0.0
```

### 한국어 키워드 패턴 생성 (make_keyword_pattern)

`make_keyword_pattern` 함수는 한국어 자연어 처리(NLP)에서 매우 중요한 **형태소의 변이**와 **띄어쓰기 오류**를 robust하게 다루기 위해 설계된 함수입니다.  
이 함수는 입력한 키워드가 실제 문장 내에서 **조사(예: "의", "에서", "까지" 등)**, **어미(예: "다", "했다" 등)**와 결합하거나, **키워드 내부에 불규칙한 띄어쓰기가 포함**되어 나타나는 다양한 형태 모두를 정규표현식 패턴으로 포괄적으로 인식할 수 있게 해줍니다.

특히 한국어 음성인식(STT) 결과에서는 띄어쓰기 오류나 조사·어미 결합이 빈번하게 발생해 키워드 매칭이 어렵기 때문에,  
이 함수를 활용하면 **키워드 기반 오류 분석**이나 **고유명사 인식 평가** 등에서 훨씬 더 정확한 평가가 가능합니다.

```python
import nlptutti as nt
from nlptutti.asr_metrics import make_keyword_pattern, COMPLEX_JOSA

# 조사 리스트 (기본 제공되는 COMPLEX_JOSA 사용 가능)
josa_list = ["의", "에서", "까지", "도", "만", "를", "을", "은", "는", "이", "가", "와", "과"]

# 어미 리스트 (선택사항)
eomi_list = ["다", "합니다", "했다", "한다", "한다면", "하고"]

# "삼성전자" 키워드에 대한 패턴 생성
pattern = make_keyword_pattern("삼성전자", josa_list, eomi_list)

# 테스트 문장들
test_sentences = [
    "삼성전자",              # True
    "삼성전자의",            # True  
    "삼 성 전 자의",         # True (띄어쓰기 있어도 인식)
    "삼성전자에서부터",       # True (조사 확장 포함)
    "삼성전자합니다",         # True (어미 결합)
    "삼성전자 했다",          # True (어미 결합, 띄어쓰기)
    "애플은"                # False
]

for sentence in test_sentences:
    is_matched = bool(pattern.search(sentence))
    print(f"'{sentence}' → {is_matched}")
```

**NLP적 의의**  
- 키워드와 조사, 어미, 띄어쓰기 등 다양한 실제 사용 맥락을 포괄적으로 처리  
- 형태소 분석 없이도 정규표현식만으로 한국어의 대표적 변이현상(조사·어미 결합, 띄어쓰기 오류 등)에 강건  
- 음성인식(STT) 결과물, 문서 검색, 정보추출 등에서 **키워드 기반 평가 및 분석의 정밀도**를 크게 향상  

### 기존 문장 단위 키워드 평가 (calculate_keyword_error_rate_with_pattern)

`calculate_keyword_error_rate_with_pattern` 함수는 여러 키워드에 대해 STT 인식 결과와 참조문장을 비교하여,  
각 키워드별 인식 정확도 및 전체 요약 통계를 제공합니다.  
조사·어미·띄어쓰기 등 한국어 변형을 유연하게 처리하므로, 고유명사/중요 단어의 STT 인식 품질 평가에 적합합니다.

이 함수는 하위 호환을 위해 유지되는 문장 존재 여부 기반 API입니다. 반복 언급과 false positive까지 평가하려면 <code>evaluate_keywords</code>를 사용하십시오.

```python
from nlptutti.asr_metrics import calculate_keyword_error_rate_with_pattern, COMPLEX_JOSA

# 조사·어미 리스트 정의 (필요시 확장 가능)
josa = COMPLEX_JOSA + ["라는", "이라는", "에서의", "으로서의"]
eomi = ["다", "합니다", "했다", "한다면", "하고", "하는데", "했었다"]

# 참조(정답) 문장과 STT(가설) 문장
refs = [
    "오늘은 메리츠화재의 주식이 올랐습니다.",
    "애플은 새로운 아이폰을 발표했습니다.",
    "구글에서 검색해보세요.",
    "메리츠화재까지도 주가가 상승했다."
]
hyps = [
    "오늘은 매리츠화제의 주식이 올랐습니다.",     # 메리츠화재 → 매리츠화제 (오류)
    "애플은 새로운 아이푼을 발표했습니다.",      # 아이폰 → 아이푼 (오류)
    "구글에서 검색해보세요.",                  # 정확 인식
    "메리츠 화재까지도 주가가 상승했다."          # 띄어쓰기 포함, 정확 인식
]
keywords = ["메리츠화재", "애플", "구글", "아이폰"]

# 오류율 계산 및 결과 출력
result = calculate_keyword_error_rate_with_pattern(refs, hyps, keywords, josa, eomi)

print("=== 개별 키워드 결과 ===")
for k, stats in result["keywords"].items():
    print(f"'{k}': 총 {stats['total']}회, 정확 {stats['correct']}회, 오류 {stats['errors']}회")
    print(f"         정확도: {stats['accuracy']:.1%}, 에러율: {stats['error_rate']:.1%}")

print("\n=== 전체 키워드 요약 ===")
s = result["summary"]
print(f"전체 키워드 등장 횟수: {s['total_keywords']}")
print(f"정확히 인식된 키워드: {s['correct_keywords']}")
print(f"오류가 발생한 키워드: {s['incorrect_keywords']}")
print(f"전체 키워드 에러율: {s['keyword_error_rate']:.1%}")
```

**출력 예시**
```
=== 개별 키워드 결과 ===
'메리츠화재': 총 2회, 정확 1회, 오류 1회
         정확도: 50.0%, 에러율: 50.0%
'애플': 총 1회, 정확 1회, 오류 0회
         정확도: 100.0%, 에러율: 0.0%
'구글': 총 1회, 정확 1회, 오류 0회
         정확도: 100.0%, 에러율: 0.0%
'아이폰': 총 1회, 정확 0회, 오류 1회
         정확도: 0.0%, 에러율: 100.0%

=== 전체 키워드 요약 ===
전체 키워드 등장 횟수: 5
정확히 인식된 키워드: 3
오류가 발생한 키워드: 2
전체 키워드 에러율: 40.0%
```

**반환값 구조**
```python
{
    "keywords": {
        "키워드명": {
            "total": 등장횟수,           # 참조 문장에서의 총 등장 횟수
            "correct": 정확개수,         # 정확히 인식된 횟수
            "errors": 오류횟수,          # 인식 실패 횟수
            "accuracy": 정확도율,        # correct/total
            "error_rate": 에러율         # errors/total
        }
    },
    "summary": {
        "total_keywords": 전체등장횟수,      # 모든 키워드의 총 등장 횟수
        "correct_keywords": 전체정확횟수,    # 전체 정확히 인식된 횟수
        "incorrect_keywords": 전체오류횟수,  # 전체 인식 실패 횟수
        "keyword_error_rate": 전체에러율    # 전체 키워드 에러율
    }
}
```

**NLP적 의미**  
- 형태소 변이, 띄어쓰기 오류, 조사·어미 결합 등 한국어 STT 결과의 자연스러운 변형을 고려하여 키워드 인식 성능을 신뢰성 있게 평가합니다.
- 특히 고유명사, 신조어, 전문용어 등 특정 단어의 인식률 분석 시 유용합니다.

### References 
- `[1]`. Word Error Rate, https://en.wikipedia.org/wiki/Word_error_rate
- `[2]`. Computing error rates, Text Digitisation, https://sites.google.com/site/textdigitisation/qualitymeasures/computingerrorrates
