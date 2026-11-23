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

CLI에서는 `nlptutti score ref.txt hyp.txt --diagnostic-profile korean-v1` 또는
`nlptutti compare input.json --diagnostic-profile korean-v1`로 같은 진단을 켭니다.

## 규칙과 경계

| 규칙 | 상태 | 의미 |
| --- | --- | --- |
| `spacing-boundary-difference/1.0` | stable | 공백과 구두점을 제외한 문자가 완전히 같은 문장만 대상으로 기준보다 빠지거나 추가된 어절 경계를 셉니다. |
| `number-unit-mention-difference/1.1` | experimental | ASCII 숫자와 지원 단위의 **표기**를 발화 안에서 비교합니다. `3.5만 원`, `3.5만원`, `1.5%`, `오후 2시 30분` 등이 대상입니다. |
| `josa-eomi-adjacent-substitution/1.0` | experimental | 어절 정렬에서 어간 문자열이 같고 알려진 조사끼리 또는 어미끼리 바뀐 치환을 셉니다. |
| `top-character-edits/1.0` | stable | 기존 `explain_errors()`의 문자 정렬을 재사용해 상위 치환·삭제·삽입을 최대 10개까지 집계합니다. |

숫자·단위와 조사·어미 항목은 형태소 분석이나 NER 결과가 아닙니다. 제한된
문자열 규칙이라 문맥에 따라 오분류할 수 있으며, 결과 provenance에도
`experimental` 상태로 기록됩니다. 띄어쓰기 진단은 어휘 오류가 섞인 문장을
띄어쓰기 오류로 분류하지 않고 `skipped_lexical_items`로 제외합니다.

숫자·단위는 문장부호를 지우기 전 원문에서 찾습니다. `3.5만 원 → 35만 원`은
기준 표현 하나 누락, 다른 표현 하나 추가입니다. 단위 안 띄어쓰기와 제대로
묶인 천 단위 쉼표는 허용하지만 `3.5만원`을 `35,000원`으로 환산하지 않습니다.
숫자로 쓴 시각은 오전/오후와 분을 한 덩어리로 비교하며 `오후 2시`와 `14시`를
같게 만들지 않습니다. `두 시 반`, `14:30`, 이름, 사전 없는 별칭의 의미는 판단하지 않습니다.

`number_unit.coverage`는 전체 발화를 양쪽 검출(`both_detected_items`), 기준만·가설만
검출(`reference_only_items`, `hypothesis_only_items`), 양쪽 미검출(`neither_detected_items`)로
나눕니다. `unknown_items`는 한쪽이라도 검출이 없거나 어느 한쪽에 규칙이 읽지 못한
십진 숫자가 남은 발화 수입니다. 두 쪽에서 하나씩 찾은 발화도 일부 숫자를 놓칠 수 있으므로
미판정과 양쪽 검출은 겹칠 수 있습니다. **누락·추가 0건은 의미 일치 판정이 아닙니다.**
규칙은 숫자가 없는 표현의 완전한 목록도 알지 못합니다.

`keywords` 또는 `entities`를 함께 전달하면 기존 평가 함수가 계산한 keyword
recall/false positive와 entity F1/CER가 `metric_breakdowns`에도 담깁니다. 값을
다시 계산하거나 지표의 의미를 바꾸지는 않습니다.

상위 편집 목록에는 원문 전체는 없지만 관측된 문자 조각이 들어갑니다. 보고서를
외부에 공유하기 전에 민감한 토큰이 없는지 확인해야 하며, 이 때문에 프로필을
켠 보고서에는 별도 경고가 포함됩니다.
