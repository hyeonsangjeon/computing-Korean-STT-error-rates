# Comparison schema 1.0

Nlptutti의 다중 STT 비교 결과는 `nlptutti.comparison/1.0` 스키마를 사용한다.
이 스키마는 기존 단일 지표 함수의 반환값을 건드리지 않고 새 비교 API에만 적용된다.

## 최상위 필드

| 필드 | 설명 |
| --- | --- |
| `schema` | 항상 `nlptutti.comparison/1.0` |
| `evaluator` | 패키지 이름과 실행한 패키지 버전 |
| `options` | 정규화, 구두점, bootstrap, 진단 설정 |
| `dataset` | 문장 수와 ID·reference SHA-256 |
| `evaluation_config` | 키워드·개체명·별칭 사용 여부와 설정 SHA-256 |
| `systems` | 시스템별 CER·WER·CRR과 선택적 세부 평가 |
| `pairwise` | 입력 순서에 따른 두 시스템 간 점수 차이 |
| `warnings` | 결과를 해석할 때 확인할 구조화된 경고 |

문장 전체는 `include_transcripts=True`일 때만 `raw_inputs`에 추가된다.
기본 상세 결과의 개체명 오류 구간이나 진단 토큰은 별개이므로 이 옵션을
모든 텍스트의 비공개 보장으로 해석하면 안 된다.

0.0.0.23부터 `options.privacy_mode`를 기록한다. 이전 결과에서 이 필드가
없으면 `detailed`로 해석한다. 기본 `detailed`는 기존 상세 결과를 보존한다.
선택적 `aggregate` 모드에서만 다음 필드가 달라진다.

- 시스템 ID와 pairwise ID는 입력 순서에 따른 `system-1`, `system-2` 등으로 바뀐다.
- `keywords`에는 `summary`만 남는다.
- `entities`에는 `summary`, `entity_cer`, `rate_mode`, `rm_punctuation`, `unicode_normalization`, `aliases_enabled`만 남는다.
- 진단 `top_character_edits`는 `redacted: true`와 세 가지 편집의 빈 목록을 가진다. 실제 토큰과 `limit`은 생략한다.
- `raw_inputs`는 허용하지 않는다. 점수·fingerprint와 그 밖의 집계는 동일하다.

이 생략은 새 모드를 직접 선택한 결과에만 적용한다. 해시는 익명화를 보장하지 않는다.

## 안정성 원칙

- 새 필드는 1.x에서 추가될 수 있지만 기존 필드의 의미와 타입은 변경하지 않는다.
- 필드 삭제, 지표 단위 변경, 기본 정규화 변경은 새 스키마 식별자가 필요하다.
- 같은 입력, 옵션, seed, 패키지 버전은 의미가 같은 JSON을 생성해야 한다.
- ID mapping은 key를 정렬해 삽입 순서가 fingerprint와 bootstrap에 영향을 주지 않게 한다.
- JSON 키 순서는 보장하지 않으므로 필드 이름으로 값을 읽어야 한다.
- CER·WER의 `micro`와 `macro`는 0~1로 제한되지 않는다. 특히
  `rate_mode="standard"`에서는 삽입이 많으면 1보다 클 수 있다.

공개 Python 타입은 `nlptutti.comparison_types`에서 제공하며 wheel에는
PEP 561의 `py.typed` 마커가 포함된다.

0.0.0.24부터 JSON·Markdown·번들 저장은 같은 런타임 validator를 사용한다.
생성 버전은 1.0이며, 읽을 때는 추가 필드를 포함한 1.x를 허용하고 다른 major는
거부한다. [필드 오류와 파일 저장 보장 범위](corpus-and-validation.md)를 참고한다.

`evaluation_config.sha256`은 키워드, 개체명, 별칭 설정을 canonical JSON으로
직렬화한 fingerprint입니다. 세 설정을 모두 생략하면 값은 `null`입니다. 해시는
설정 원문을 복구하거나 익명화하는 수단이 아니라, 다시 실행할 때 같은 평가
설정을 사용했는지 확인하는 값입니다.

## 0.0.0.24의 선택적 필드

- `input_sources`: manifest의 파일 해시·형식·provider/schema. 경로와 임의 공급자 메타데이터는 제외한다.
- `details`: `include_items=True`일 때 문장별 metrics, delta, 상위 악화/개선 ID를 `nlptutti.details/1.0`으로 기록한다.
- `slices`, `labels_sha256`: 사용자 labels가 있을 때 조건별 집계와 설정 해시를 기록한다. aggregate 모드에는 details와 slices를 허용하지 않는다.
- `warnings`: bootstrap 해석 안내가 추가될 수 있다. 경고 문장을 안정적인 오류 코드로 파싱하지 않는다.

새 필드도 두 renderer가 함께 검증한다. 기본 비교에는 details, slices와 파일
출처가 추가되지 않는다. 점수 단위와 기존 필드 의미는 동일하다.
