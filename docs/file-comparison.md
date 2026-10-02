# 저장된 STT 파일 비교하기

0.0.0.24부터 `nlptutti compare --input-format manifest`로 파일 목록을 읽습니다.
기존 references/systems 문자열 JSON도 그대로 지원하며 계산 경로는 같습니다.

## 파일 목록

`manifest.json`의 `u1`은 같은 발화를 가리킵니다. 모든 시스템에 같은 ID가 있어야 합니다.

```json
{
  "schema": "nlptutti.manifest/1.0",
  "references": [
    {"id": "u1", "path": "reference.txt", "source_format": "text"}
  ],
  "systems": {
    "baseline": [
      {"id": "u1", "path": "baseline.srt", "source_format": "srt"}
    ],
    "candidate": [
      {"id": "u1", "path": "candidate.json", "source_format": "json"}
    ]
  }
}
```

```bash
nlptutti compare manifest.json --input-format manifest \
  --rate-mode standard --unicode-normalization NFC \
  --output-dir comparison-report
```

상대 경로는 **manifest가 있는 폴더**를 기준으로 읽습니다. 절대 경로도 허용하므로
신뢰할 수 있는 목록만 실행하세요. 네트워크·클라우드 자격증명·음성 모델은 사용하지 않습니다.

| source_format | 읽는 내용 | 제한 |
| --- | --- | --- |
| `text` | UTF-8 원문 | 문자열을 그대로 전달 |
| `json` | 최상위 `text` | 필요할 때만 `json_text_policy: "segments_fallback"` 지정 |
| `srt` | cue 텍스트를 공백 하나로 연결 | 타임코드는 평가하지 않음 |
| `tsv` | `start`, `end`, `text` 헤더 중 `text` | 헤더 필수 |

ID 누락·중복·집합 불일치, 중복 JSON 키, 잘못된 UTF-8/형식, 알 수 없는 필드는
종료 코드 `2`로 실패합니다. 부분 보고서를 만들지 않습니다.

## 공급자 응답과 사전

Azure 파일 항목에는 다음처럼 provider와 schema를 명시합니다.

```json
{
  "id": "u1", "path": "azure.json", "source_format": "json",
  "provider": "azure-speech", "schema_version": "short-audio-simple-v1"
}
```

OpenAI Whisper `transcribe()` 결과는 `provider: "openai-whisper"`,
`schema_version: "transcribe-v1"`입니다. 자동 감지, 다른 Azure API,
OpenAI 호스팅 API, AWS/Google 응답을 지원한다는 뜻은 아닙니다.
[지원 필드와 제한](provider-adapters.md)을 확인하세요.

`--evaluation-config evaluation.json`으로 기존 Python 사전 설정도 전달합니다.

```json
{
  "keywords": ["서울"],
  "entities": ["서울"],
  "entity_aliases": {"서울": ["서울시"]}
}
```

실제 사전·별칭과 키워드 Unicode 정책은 `evaluation_config.sha256`에 반영합니다.

## 보고서에 남는 것

`input_sources`에는 manifest 해시, ID 정렬 순서의 `item_index`, 파일 바이트의
SHA-256, 형식, provider/schema 또는 JSON text 정책만 기록합니다. 파일 경로와
JSON의 모델명·언어·임의 메타데이터는 복사하지 않습니다. 같은 전사라도 형식이나
줄바꿈이 다르면 파일 해시는 달라집니다.

기본 `detailed` 모드에는 시스템 이름과 선택적 사전·오류 텍스트가 남을 수 있습니다.
외부 공유에는 `--privacy-mode aggregate`를 지정하세요. 공급자 이력의 시스템
이름도 `system-1` 등으로 바뀝니다. 파일 해시 역시 익명화 보장은 아닙니다.
