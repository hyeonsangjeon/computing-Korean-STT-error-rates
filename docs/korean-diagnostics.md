# 한국어 오류 진단 프로필

`korean-v1`은 CER·WER·CRR을 바꾸거나 대체하지 않고 모델 간 차이를 살펴보는
선택 기능입니다. 기존 사용자의 점수가 달라지지 않도록 기본값은 계속
`None`입니다.

```python
import nlptutti as metrics

report = metrics.compare_systems(
    ["회의에는 3명이 참석합니다", "부산 바다"],
    {
        "baseline": ["회의에는 4명이 참석했다", "부산바다"],
        "candidate": ["회의에는 3명이 참석합니다", "부산 바다"],
    },
    diagnostic_profile="korean-v1",
)

diagnostics = report["systems"][0]["diagnostics"]
print(diagnostics["spacing_boundary"])
print(diagnostics["number_unit"])
```

CLI에서는 `nlptutti compare input.json --diagnostic-profile korean-v1`로 같은
진단을 켭니다.

## 규칙과 경계

| 규칙 | 상태 | 의미 |
| --- | --- | --- |
| `spacing-boundary-difference/1.0` | stable | 공백과 구두점을 제외한 문자가 완전히 같은 문장만 대상으로 기준보다 빠지거나 추가된 어절 경계를 셉니다. |
| `number-unit-mention-difference/1.0` | experimental | 아라비아 숫자와 제한된 단위 목록의 누락·추가를 정규식으로 셉니다. |
| `josa-eomi-adjacent-substitution/1.0` | experimental | 어절 정렬에서 어간 문자열이 같고 알려진 조사끼리 또는 어미끼리 바뀐 치환을 셉니다. |
| `top-character-edits/1.0` | stable | 기존 `explain_errors()`의 문자 정렬을 재사용해 상위 치환·삭제·삽입을 최대 10개까지 집계합니다. |

숫자·단위와 조사·어미 항목은 형태소 분석이나 NER 결과가 아닙니다. 제한된
문자열 규칙이라 문맥에 따라 오분류할 수 있으며, 결과 provenance에도
`experimental` 상태로 기록됩니다. 띄어쓰기 진단은 어휘 오류가 섞인 문장을
띄어쓰기 오류로 분류하지 않고 `skipped_lexical_items`로 제외합니다.

`keywords` 또는 `entities`를 함께 전달하면 기존 평가 함수가 계산한 keyword
recall/false positive와 entity F1/CER가 `metric_breakdowns`에도 담깁니다. 값을
다시 계산하거나 지표의 의미를 바꾸지는 않습니다.

상위 편집 목록에는 원문 전체는 없지만 관측된 문자 조각이 들어갑니다. 보고서를
외부에 공유하기 전에 민감한 토큰이 없는지 확인해야 하며, 이 때문에 프로필을
켠 보고서에는 별도 경고가 포함됩니다.
