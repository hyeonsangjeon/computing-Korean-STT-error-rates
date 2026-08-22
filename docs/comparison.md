# STT 시스템 비교와 결과 번들

`compare_systems()`는 이미 생성된 둘 이상의 STT 출력과 reference를 문장별로
맞춰 CER, WER, CRR을 계산합니다. 오디오를 읽거나 STT 모델을
실행하지 않습니다.

## 가장 작은 비교

```python
import nlptutti as metrics

report = metrics.compare_systems(
    ["오늘 날씨가 맑습니다", "서울은 따뜻합니다"],
    {
        "baseline": ["오늘 날씨는 맑습니다", "서울은 춥습니다"],
        "candidate": ["오늘 날씨가 맑습니다", "서울은 따뜻합니다"],
    },
    rate_mode="standard",
)
```

이 예제는 저장소의 [`examples/comparison_input.json`](../examples/comparison_input.json)과
같은 데이터입니다. 핵심 기대값은 다음과 같습니다.

| System | CER micro | WER micro | CRR micro |
| --- | ---: | ---: | ---: |
| `baseline` | `0.235294...` | `0.4` | `0.76` |
| `candidate` | `0.0` | `0.0` | `1.0` |

candidate에서 baseline을 뺀 pairwise CER micro delta는 `-0.235294...`입니다.
CER/WER delta가 음수면 candidate의 오류율이 더 낮고, CRR delta가 양수면
candidate의 정답률이 더 높습니다.

## 입력을 맞추는 규칙

순서 기반 입력은 모든 목록의 길이가 같아야 합니다.

```python
references = ["문장 1", "문장 2"]
systems = {
    "system-a": ["결과 1", "결과 2"],
    "system-b": ["결과 1", "결과 2"],
}
```

ID 기반 입력은 reference와 모든 시스템의 ID 집합이 정확히 같아야 합니다.
mapping에 넣은 순서와 관계없이 ID 문자열을 정렬한 순서로 계산합니다. 같은 ID
집합을 다시 만들었을 때 fingerprint와 bootstrap 결과가 흔들리지 않도록 하기
위한 규칙입니다.

```python
references = {"utt-2": "문장 2", "utt-1": "문장 1"}
systems = {
    "system-a": {"utt-1": "결과 1", "utt-2": "결과 2"},
    "system-b": {"utt-2": "결과 2", "utt-1": "결과 1"},
}
```

누락·추가 ID, 중복 ID, 길이 차이, 빈 입력, 두 개 미만의 시스템은 조용히
보정하지 않고 예외로 거부합니다.

## CLI 입력과 저장

CLI JSON에는 `references`와 시스템 ID별 `systems`가 필요합니다. 값에는 문자열
목록, ID를 key로 두고 문장을 value로 둔 object 또는
`{"id": ..., "text": ...}` object 목록을 쓸 수 있습니다.

```bash
nlptutti compare examples/comparison_input.json \
  --rate-mode standard \
  --output-dir comparison-report
```

- `report.json`: `nlptutti.comparison/1.0` schema의 자동화용 결과
- `report.md`: 같은 결과를 표로 보여 주는 검토용 문서

`--output report.json`은 JSON 하나만 저장합니다. `--output`과 `--output-dir`은
동시에 사용할 수 없습니다. 둘 다 생략하면 JSON을 표준 출력으로 보냅니다.

## 계산 옵션

| 옵션 | 기본값 | 정책 |
| --- | --- | --- |
| `rate_mode` | `"normalized"` | 기존 Nlptutti 분모를 보존합니다. 공식 비교는 `"standard"`를 직접 지정합니다. |
| `rm_punctuation` | `True` | 문장부호를 제거합니다. CLI에서는 `--keep-punctuation`으로 끕니다. |
| `unicode_normalization` | `None` | Unicode 원문을 유지합니다. 필요한 경우에만 NFC/NFD/NFKC/NFKD를 지정합니다. |
| `include_transcripts` | `False` | 원문을 보고서에서 제외합니다. |
| `bootstrap` | `0` | paired bootstrap을 끕니다. 양의 정수로 켭니다. |
| `seed` | `42` | bootstrap 난수 seed입니다. |
| `confidence` | `0.95` | percentile 신뢰구간의 confidence입니다. |
| `diagnostic_profile` | `None` | 한국어 진단을 끕니다. 켜려면 `"korean-v1"`을 지정합니다. |

기본값을 변경하지 않으므로 기존 API 결과는 그대로 유지됩니다. 보고서의
`options`에는 실제 적용한 모든 값이 기록됩니다.

## Paired bootstrap

```python
report = metrics.compare_systems(
    references,
    systems,
    rate_mode="standard",
    bootstrap=1000,
    seed=42,
    confidence=0.95,
)
```

reference 문장을 sampling unit으로 삼고, 표본을 다시 뽑을 때 모든 시스템에서
같은 문장 ID를 함께 선택합니다. 반환값은 CER/WER micro delta의 percentile
신뢰구간이며 시스템마다 따로 bootstrap하지 않습니다. corpus가 한 문장뿐이면
bootstrap을 켤 수 없습니다. 이 구간은 모델 정확도 자체의 보편적인 확률을
뜻하지 않고, 현재 평가 corpus를 다시 표집할 때 생기는 점수 변동을 보여 줍니다.

## 키워드, 개체명, 한국어 진단

```python
report = metrics.compare_systems(
    references,
    systems,
    keywords={"PRODUCT": ["갤럭시 S26"]},
    entities={"ORG": ["삼성전자"]},
    diagnostic_profile="korean-v1",
)
```

keyword recall/false positive와 Entity CER/F1은 기존 공개 평가 함수로
계산합니다. `korean-v1`의 spacing, number/unit, josa/eomi, top edit는
`diagnostics`에 따로 들어가며 CER/WER를 바꾸지 않습니다. 규칙의 버전과
experimental 상태는 [한국어 진단 문서](korean-diagnostics.md)에 정리했습니다.

## 재현성과 개인정보

- JSON key는 정렬하고 유한한 값만 허용합니다.
- Markdown 숫자는 고정 형식으로 출력합니다.
- 같은 입력 순서, 옵션, 패키지 버전에서 같은 내용을 생성합니다.
- ID mapping은 key를 정렬하므로 mapping 삽입 순서가 결과에 영향을 주지 않습니다.
- 원문 대신 ID/reference/hypothesis 목록의 SHA-256을 기본 provenance에 둡니다.
- 키워드·개체명·별칭을 사용하면 설정 전체의 SHA-256도 기록합니다.
- 해시는 익명화가 아니며 짧은 민감 문장은 사전 대입 위험이 있습니다.
- 한국어 진단의 상위 편집에는 관측된 문자 조각이 포함될 수 있습니다.
- 원문이 필요할 때만 `include_transcripts=True`를 명시하고 공유 전에 검토합니다.

`write_comparison_bundle()`은 각 파일을 임시 경로에 먼저 완성한 뒤 교체합니다.
따라서 쓰다 만 내용이 최종 파일에 남을 가능성이 줄어듭니다.

## Python에서 직접 저장

```python
from pathlib import Path

import nlptutti as metrics

report = metrics.compare_systems(references, systems, rate_mode="standard")
paths = metrics.write_comparison_bundle(report, Path("comparison-report"))

print(paths["json"])
print(paths["markdown"])
```

구조의 필수·선택 필드는 [비교 schema 문서](comparison-schema.md)에 정리되어
있습니다. JSON·SRT·TSV 하나를 평가 여권으로 남기는 방법은
[구조화 transcript 문서](structured-transcripts.md)에서 볼 수 있습니다.
