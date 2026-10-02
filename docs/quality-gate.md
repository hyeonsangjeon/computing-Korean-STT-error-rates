# STT 변경을 CI에서 검사하기

0.0.0.24부터 `nlptutti gate`로 비교 보고서에 허용 오차를 적용합니다. 기존
`compare`는 보고서 생성 성공 여부만 알리며, 품질 판정은 별도 명령입니다.

```bash
nlptutti sample --output comparison_input.json
nlptutti compare comparison_input.json --rate-mode standard --output report.json
nlptutti gate report.json --policy examples/gate_policy.json --output decision.json
```

저장소의 [`gate_policy.json`](../examples/gate_policy.json)은 이 예제에서 통과하는
정책입니다. CER/WER 악화를 0.02까지 허용하고 CRR 0.8 이상을 요구합니다.
설명용 값이며 업계 권장값이 아닙니다. 실제 데이터와 실패 비용에 맞춰 정하세요.

## 정책 계약

`schema`, `report_schema`, baseline/candidate ID, `rate_mode`, `rm_punctuation`,
`unicode_normalization`, `score_unit: "ratio"`, `evaluation_config_sha256`,
비어 있지 않은 `rules`가 필수입니다. 분모·정규화·사전 fingerprint가 보고서와
다르면 판정을 거부합니다. 사전 평가를 생략했을 때만 fingerprint는 `null`입니다.
`aggregate` 보고서에는 바뀐 `system-1` 등의 ID를 씁니다.

| metric | aggregation | 허용 조건 |
| --- | --- | --- |
| `cer`, `wer` | `micro` 또는 `macro` | `max_regression`, `max_score` |
| `crr` | `micro` 또는 `macro` | `max_regression`, `min_score` |
| `keyword_recall`, `entity_f1` | `summary` | `max_regression`, `min_score` |

규칙마다 하나 이상의 조건을 적습니다. `max_regression`은 **악화량**입니다.
CER/WER는 candidate-baseline, CRR/recall/F1은 baseline-candidate로 계산합니다.
별도 `delta` 필드는 항상 candidate-baseline입니다.

임계치는 0~1 비율만 허용합니다. 2%p 허용은 `0.02`이며 `2`는 오류입니다.
`standard`의 실제 CER/WER가 1보다 커지는 것은 정상이며 점수를 자르지 않습니다.
첫 정책 버전은 1 초과 임계치와 음수 최소 점수는 지원하지 않습니다. 소수 경계의
절대 오차 `1e-12`만 허용하며 이 값도 결과에 기록합니다.

## 종료 코드

| 코드 | 뜻 |
| --- | --- |
| `0` | 모든 규칙 통과 |
| `3` | 품질 기준 미달, decision JSON은 정상 생성 |
| `2` | 잘못된 입력·정책, 설정 불일치 또는 파일 오류 |

decision JSON에는 정책, 보고서 SHA-256, 점수·악화량·실패 이유가 남습니다.
잘못된 입력에서는 기존 출력 파일을 보존하므로 **파일 존재가 아니라 현재 종료
코드**로 판단하세요. bootstrap 구간은 pass/fail에 쓰지 않습니다. 실무 허용치와
통계적 유의성은 다르며, 통과했다고 모델이 항상 더 좋다는 뜻은 아닙니다.

## GitHub Actions 예시

0.0.0.24 배포 후 사용하며 버전은 검증한 값으로 고정하세요. 아래 예제는 같은
`examples/gate_policy.json` fixture로 테스트합니다.

```yaml
name: STT quality
on: [pull_request]
permissions:
  contents: read
jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: "3.12"
      - run: python -m pip install nlptutti==0.0.0.24
      - run: nlptutti sample --output comparison_input.json
      - run: nlptutti compare comparison_input.json --rate-mode standard --output report.json
      - run: nlptutti gate report.json --policy examples/gate_policy.json --output decision.json
```

내장 예제는 명령을 확인하는 합성 데이터입니다. 모델을 검사하려면 실제 출력으로
입력을 바꿔야 합니다. 보고서의 시스템 이름·사전·오류 텍스트가 공개될 수 있으니
artifact 업로드는 별도로 검토하세요.
