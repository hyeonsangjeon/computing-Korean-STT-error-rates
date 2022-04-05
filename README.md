[![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)](https://raw.githubusercontent.com/hyeonsangjeon/youtube-dl-nas/master/LICENSE)

# 한국어 자동 음성 인식 평가를 위한 유사도 측정 함수

이 저장소에는 Amazon Transcribes와 같은 한글 문장 인식기의 출력 스크립트의 낱말 오류율(CER), 단어 오류율(WER)을 계산하는 간단한 Python 패키지가 포함되어있습니다. 
STT(speech-to-text) API의 실제(Ground truth)문장과 가설(hypothesis or transcribe)문장 사이의 최소 편집거리를 계산합니다. 최소편집거리는 Dynamic Programing 기법 중 Levenshtein을 사용하여 계산됩니다. 

문자 오류율(CER/WER)은 자동 음성 인식 시스템의 성능에 대한 일반적인 메트릭입니다. CER은 WER(단어 오류율)과 유사하지만 단어 대신 문자에 대해 작동합니다. 자세한 내용은 WER 문서를 참조하십시오.[1]
문자 오류율은 다음과 같이 계산할 수 있습니다. 

---

<img src="https://github.com/hyeonsangjeon/computing-Korean-STT-error-rates/blob/main/pic/ER_CASE.png" width="90%">

---

<img src="https://github.com/hyeonsangjeon/computing-Korean-STT-error-rates/blob/main/pic/FORMULA_CASE.png" width="70%">

---

CER(WER) = (S + D + I) / N = (S + D + I) / (S + D + C)

- S : 대체 오휴, 철자가 틀린 외자(uniliteral)/단어(word) 횟수 
- D : 삭제 오류, 외자/단어의 누락 횟수
- I : 삽입 오류, 잘못된 외자/단어가 포함된 횟수  
- C : Ground truth와 hypothesis 간 올바른 외자/단어(기호)의 합계, (N - D - S)
- N : 참조의(Ground truth) 외자/단어 수 

CER의 출력은 특히 삽입 수가 많은 경우 항상 0과 1 사이의 숫자가 아닙니다. 이 값은 종종 잘못 예측된 문자의 백분율과 연관됩니다. 값이 낮을수록 ASR 시스템의 성능이 향상되고 CER이 0이면 완벽한 점수입니다.
이 함수에서는 insertion에 따른 오류값 초과에 대해 normalized error rate으로 적용했습니다.[2]

CER은 자동 음성 인식(ASR) 및 광학 문자 인식(OCR)과 같은 작업에 대한 다양한 모델을 비교하는 데 유용하며, 특히 언어의 다양성으로 인해 WER이 적합하지 않은 다국어 데이터 세트의 경우에 유용합니다. 
CER 같은 경우, 번역 오류의 특성에 대한 세부 정보를 제공하지 않으므로 오류의 주요 원인을 식별하고 연구 노력에 집중하기 위해서는 추가 작업이 필요합니다.
또한 경우에 따라 원본 ER을 보고하는 대신 실수 수를 편집 작업 수(I + S + D)와 C(정확한 문자 수)의 합으로 나눈 정규화된 ER이 필요합니다.  그 결과 0–100% 범위에 속하는 CER 값이 생성됩니다.


### 사용방법 
가장 간단한 사용 사례는 두 문자열 간의 편집 거리를 계산하는 것입니다.

#### CER
```python
import asr_metrics as metrics
refs = "제이 차 세계 대전은 인류 역사상 가장 많은 인명 피해와 재산 피해를 남긴 전쟁이었다."
preds = "제이차 세계대전은 인류 역사상 가장많은 인명피해와 재산피해를 남긴 전쟁이었다."
[cer, substitutions, deletions, insertions] = metrics.get_cer(refs, preds)
# prints: [cer, substitutions, deletions, insertions] -> [CER = 0 / 34, S = 0, D = 0, I = 0]
```

#### WER
```python
import asr_metrics as metrics
refs = "대한민국은 주권 국가 입니다."
preds = "대한민국은 주권국가 입니다."
[wer, substitutions, deletions, insertions] = metrics.get_wer(refs, preds)
# prints: [wer, substitutions, deletions, insertions] -> [WER =  2 / 4, S = 1, D = 1, I = 0]
```

### 전처리 예 

#### 띄어쓰기 
가설 또는 정답 텍스트에 일부 전처리 단계를 적용해야 할 수 있습니다. 
한국어 문장 구성은 단어간 띄어쓰기의 모호성으로 CER계산에서 공백을 계산하지 않았습니다. 근대 이전까지 동양의 언어에는 ‘띄어쓰기’ 개념이 존재하지 않았고, 한국어는 맞춤법 상 띄어쓰기 규칙이 정해져 있기는 하나, 띄어쓰기를 지키지 않아도 문장의 맥락을 이해하는데 큰 무리가 없는 언어입니다.
따라서 CER 계산에서 입력 변수의 whitespace는 제거합니다. 
공백 문자는 \t, \n, \r, \x0b 및 \x0c와 whirespace입니다.
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
refs = "또 다른 방법으로, 데이터를 읽는 작업과 쓰는 작업을 분리합니다!"
preds = "또! 다른 방법으로 데이터를 읽는 작업과 쓰는 작업을 분리합니다."
[wer, substitutions, deletions, insertions] = metrics.get_wer(refs, preds, rm_punctuation=True)

# prints: wer -> 0.0
```



### References 
- `[1]`. Word Error Rate, https://en.wikipedia.org/wiki/Word_error_rate
- `[2]`. Computing error rates, Text Digitisation, https://sites.google.com/site/textdigitisation/qualitymeasures/computingerrorrates
