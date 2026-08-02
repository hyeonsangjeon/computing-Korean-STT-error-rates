# 구조화 STT 결과 평가

`nlptutti`는 STT 모델을 실행하지 않고 이미 생성된 일반 텍스트, JSON, SRT, TSV 결과를 같은 문자열 평가 경로로 연결합니다. 파싱이 끝난 가설문장은 기존 `get_cer`, `get_wer`, `get_crr`와 동일한 계산 함수로 평가됩니다.

## 공통 사용 순서

```python
from pathlib import Path

import nlptutti as metrics

serialized = Path("result.json").read_text(encoding="utf-8")
transcript = metrics.parse_transcript(serialized, "json")
report = metrics.evaluate_transcript(
    "오늘 날씨가 맑습니다",
    transcript,
    rate_mode="standard",
)

print(report["metrics"]["cer"]["value"])
print(report["metrics"]["wer"]["value"])
```

`parse_transcript()`에는 파일 경로가 아니라 파일에서 읽은 문자열 또는 UTF-8 bytes를 전달합니다. JSON은 Python mapping도 직접 받을 수 있습니다.

## 일반 텍스트

입력 문자열을 바꾸지 않고 그대로 가설문장으로 사용합니다. `txt`는 `text`의 별칭입니다.

```python
transcript = metrics.parse_transcript("오늘 날씨가 맑습니다", "text")
```

## JSON

기본값은 최상위 `text` 문자열만 평가 입력으로 사용합니다. `file`, `model`, `language`, `duration_s`가 실제로 있으면 결과의 provenance에 보존합니다.

```python
transcript = metrics.parse_transcript(
    {
        "text": "오늘 날씨가 맑습니다",
        "segments": [
            {"start": 0, "end": 1200, "text": "오늘 날씨가"},
            {"start": 1200, "end": 2500, "text": "맑습니다"},
        ],
        "model": "example-model",
        "language": "ko",
    },
    "json",
)
```

최상위 `text`가 없는 JSON에서 `segments[*].text`를 결합하려면 정책을 직접 지정해야 합니다.

```python
transcript = metrics.parse_transcript(
    {
        "segments": [
            {"text": "오늘 날씨가"},
            {"text": "맑습니다"},
        ]
    },
    "json",
    json_text_policy="segments_fallback",
)
```

`segments_fallback`도 최상위 `text`가 있으면 이를 우선합니다. 구간 문자열은 앞뒤 공백과 연속 공백을 정리한 뒤 ASCII 공백 하나로 연결합니다. JSON 예시에서 타임스탬프 단위가 명시되지 않은 경우에는 단위를 추정하지 않고 원래 숫자만 provenance에 기록합니다.

## SRT

각 cue의 텍스트 줄을 순서대로 읽어 ASCII 공백 하나로 연결합니다. cue 번호는 선택 사항이지만 시작·종료 타임코드, 비어 있지 않은 cue 텍스트, cue 사이 빈 줄이 필요합니다.

```python
srt = """1
00:00:00,000 --> 00:00:01,200
오늘 날씨가

2
00:00:01,200 --> 00:00:02,500
맑습니다
"""

transcript = metrics.parse_transcript(srt, "srt")
```

타임코드는 평가 문자열에 포함하지 않고 `srt_timecode` 형식으로 provenance에만 보존합니다.

## TSV

첫 행에 `start`, `end`, `text` 헤더가 모두 있어야 합니다. 추가 열은 허용하지만 평가에는 `text`만 사용하며 `start`와 `end`는 초 단위의 유한한 숫자로 검증합니다.

```python
tsv = """start\tend\ttext
0.0\t1.2\t오늘 날씨가
1.2\t2.5\t맑습니다
"""

transcript = metrics.parse_transcript(tsv, "tsv")
```

## 평가 여권

`evaluate_transcript()`는 JSON으로 저장할 수 있는 `schema_version="1.0"` 보고서를 반환합니다.

```python
{
    "schema_version": "1.0",
    "evaluator": {"name": "nlptutti", "version": "..."},
    "options": {
        "rate_mode": "standard",
        "rm_punctuation": True,
        "unicode_normalization": None,
    },
    "metrics": {
        "cer": {"value": 0.0, "substitutions": 0, "deletions": 0, "insertions": 0},
        "wer": {"value": 0.0, "substitutions": 0, "deletions": 0, "insertions": 0},
        "crr": {"value": 1.0, "substitutions": 0, "deletions": 0, "insertions": 0},
    },
    "provenance": {"source": {}, "reference": {}, "hypothesis": {}},
}
```

보고서에는 reference와 hypothesis 원문을 다시 넣지 않고 SHA-256, 문자 수, UTF-8 byte 수만 기록합니다. 해시는 원문을 직접 노출하지 않지만 익명화 수단은 아니므로 민감한 짧은 문장에 대한 접근 권한은 별도로 관리해야 합니다.

기존 호환성을 위해 `rate_mode` 기본값은 계속 `normalized`, `unicode_normalization` 기본값은 계속 `None`입니다. 공식 비교용 표준 CER/WER가 필요할 때만 `rate_mode="standard"`를 명시합니다.

## 오류 처리

JSON 문법 오류, 필수 필드 누락, 잘못된 SRT 타임코드, TSV 헤더 누락처럼 입력 계약을 위반하면 `TranscriptFormatError`가 발생합니다. 잘못된 구조화 입력을 빈 가설문장으로 조용히 바꾸지 않습니다.

## 참조 범위

입력 형식은 FunASR 고정 커밋 `d1007c323068d0c5aaa8e0f198668aaebc1a4fc2`의 [CLI 출력 문서](https://github.com/modelscope/FunASR/blob/d1007c323068d0c5aaa8e0f198668aaebc1a4fc2/docs/cli.md)에 제시된 text, JSON, SRT, TSV 예시를 검토해 공급자 중립적인 계약으로 독립 구현했습니다. FunASR 코드, 모델, 런타임은 포함하거나 의존하지 않습니다. 참조 저장소의 [MIT 라이선스](https://github.com/modelscope/FunASR/blob/d1007c323068d0c5aaa8e0f198668aaebc1a4fc2/LICENSE)와 별도 [모델 라이선스](https://github.com/modelscope/FunASR/blob/d1007c323068d0c5aaa8e0f198668aaebc1a4fc2/MODEL_LICENSE)는 서로 다른 범위로 확인했습니다.
