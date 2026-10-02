# 문장 오류율과 보고서 검증

## 문장 오류율은 무엇을 세나요?

`evaluate_corpus`의 기존 `sentence_error_rate`와 `perfect_sentences`는
**CER 전처리 후 문자 오류가 있는지**를 셉니다. CER은 항상 공백을 제거하므로
띄어쓰기만 틀린 문장도 이 기준에서는 완전 일치입니다.

```python
import nlptutti as nt

result = nt.evaluate_corpus(["가 나"], ["가나"])
print(result["sentence_error_rate"])       # 0.0
print(result["perfect_sentences"])         # 1
print(result["word_sentence_error_rate"])  # 1.0
print(result["word_perfect_sentences"])    # 0
```

0.0.0.24부터 `sentence_error_unit="character"`로 기존 기준을 명시하고,
어절 기준의 `word_sentence_error_rate`, `word_perfect_sentences`를 함께
반환합니다. 기존 두 필드의 의미는 바꾸지 않았습니다. 어절은 형태소가 아니라
공백으로 나눈 WER 토큰입니다.

- 구두점만 다르면 기본 `rm_punctuation=True`에서는 두 기준 모두 일치합니다.
- 빈 참조와 빈 인식 결과는 일치입니다. 빈 참조에 단어를 삽입하면 두 기준 모두 오류입니다.
- `rate_mode`는 오류율의 분모를 정합니다. 문장에 오류가 있는지 여부는 바꾸지 않습니다.
- Unicode 변환은 여전히 `None`이 기본입니다. 필요할 때만 `NFC` 등을 지정하세요.

## JSON과 Markdown이 같은 계약을 검사합니다

`validate_comparison_report(report)`는 필수 필드, 옵션, 유한 숫자, 편집 횟수,
시스템 ID와 pairwise 참조를 검사합니다. 두 renderer도 같은 함수를 호출합니다.
잘못된 값은 `ValueError: report.systems[0].metrics.cer.micro: ...`처럼
필드 경로를 포함한 오류로 알립니다.

1.x의 추가 필드는 허용하지만 JSON으로 저장 가능한 값이어야 합니다. 알 수 없는
major 버전, 중복 시스템, NaN/Infinity, 누락된 지표는 거부합니다. 이 검사는
저장된 보고서의 형식을 확인하며, 원본 전사나 계산 결과의 진위를 보증하지 않습니다.
실행 계약은 공개 TypedDict와 런타임 validator로 관리합니다. 중복 유지가 필요한
별도 JSON Schema와 추가 런타임 의존성은 이번에 넣지 않았습니다.

번들 저장은 JSON과 Markdown을 **모두 렌더링한 뒤** 각 파일을 교체합니다.
렌더링 오류라면 기존 두 파일을 보존합니다. 두 파일 전체를 묶는 파일시스템
트랜잭션은 아니므로, 디스크 오류나 다른 프로세스의 동시 쓰기까지 원자적으로
묶지는 않습니다. 실행별 출력 폴더를 사용하는 것이 좋습니다.
