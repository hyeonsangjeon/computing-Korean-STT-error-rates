# STT 도구별 JSON 어댑터

`parse_provider_transcript()`는 STT 도구가 만든 JSON을 `nlptutti`의 공통
transcript 구조로 바꿉니다. 네트워크 요청, 인증, SDK 호출, 모델 실행은 하지
않습니다. 공급자와 스키마도 자동으로 감지하지 않습니다.

## Azure Speech

현재 지원 범위는 short-audio REST API의 `simple` 성공 응답입니다.

```python
import json

import nlptutti as metrics

payload = json.loads(open("azure-result.json", encoding="utf-8").read())
transcript = metrics.parse_provider_transcript(
    payload,
    "azure-speech",
    schema_version="short-audio-simple-v1",
)
report = metrics.evaluate_transcript("회의는 오후 세 시에 시작합니다.", transcript)
```

| 항목 | 정책 |
| --- | --- |
| 평가 문자열 | 성공 응답의 `DisplayText` |
| 필수 필드 | `RecognitionStatus="Success"`, 문자열 `DisplayText` |
| 선택 필드 | `Offset`과 `Duration`을 함께 제공한 경우 provenance에 보존 |
| 시간 단위 | Microsoft 문서에 따른 100ns tick |
| 빈 성공 결과 | 빈 `DisplayText`를 빈 가설문장으로 유지 |
| 실패 상태 | `NoMatch`, timeout, `Error`를 평가 결과로 처리하지 않고 예외 발생 |

`detailed`의 `NBest`, batch transcription, fast transcription은 형식이 서로
달라 이 버전에서 지원하지 않습니다. 공식 근거는 Microsoft의
[short-audio REST 응답 문서](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/rest-speech-to-text-short)와
[offset/duration 설명](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/get-speech-recognition-results)입니다.

## OpenAI Whisper

현재 지원 범위는 오픈소스 `openai/whisper`의 `transcribe()` 반환 구조입니다.
OpenAI API의 transcription 응답은 형식이 다르며 지원 대상이 아닙니다.

```python
import json

import nlptutti as metrics

payload = json.loads(open("whisper-result.json", encoding="utf-8").read())
transcript = metrics.parse_provider_transcript(
    payload,
    "openai-whisper",
    schema_version="transcribe-v1",
)
```

| 항목 | 정책 |
| --- | --- |
| 평가 문자열 | 최상위 `text` |
| 필수 필드 | 문자열 `text`, 문자열 `language`, 배열 `segments` |
| segment | 문자열 `text`와 초 단위 `start`, `end` 검증 |
| 선택 메타데이터 | 실제 입력에 있는 `model`, `duration_s`만 보존 |
| 빈 성공 결과 | 빈 `text`와 빈 `segments`를 허용 |

필드 구성은 고정 커밋 `5f86d1d86363843179951550570367b37c5d6f78`의
[`transcribe()` 반환값](https://github.com/openai/whisper/blob/5f86d1d86363843179951550570367b37c5d6f78/whisper/transcribe.py)을 기준으로 삼았습니다.
fixture는 공개 음성이나 공급자 응답을 복제하지 않고 위 필드 구성에 맞춰 직접
작성했습니다.

## 오류 정책

알 수 없는 provider/schema, JSON 문법 오류, 필수 필드 누락, 음수 또는 역전된
시간은 fail-closed 방식으로 거부합니다. 이 어댑터를 추가해도 일반
JSON·SRT·TSV용 `parse_transcript()`의 동작과 strictness는 바뀌지 않습니다.
