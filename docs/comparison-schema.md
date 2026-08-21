# Comparison schema 1.0

Nlptutti의 다중 STT 비교 결과는 `nlptutti.comparison/1.0` 스키마를 사용한다.
이 계약은 기존 단일 지표 함수의 반환값을 변경하지 않고 새 비교 API에만 적용된다.

## 최상위 필드

| 필드 | 설명 |
| --- | --- |
| `schema` | 항상 `nlptutti.comparison/1.0` |
| `evaluator` | 패키지 이름과 실행한 패키지 버전 |
| `options` | 정규화, 구두점, bootstrap, 진단 설정 |
| `dataset` | 문장 수와 ID·reference SHA-256 |
| `systems` | 시스템별 CER·WER·CRR과 선택적 세부 평가 |
| `pairwise` | 입력 순서에 따른 두 시스템 간 점수 차이 |
| `warnings` | 결과를 해석할 때 확인할 구조화된 경고 |

기본 결과에는 reference와 hypothesis 원문이 포함되지 않는다. 원문 저장은
`include_transcripts=True`를 명시한 경우에만 `raw_inputs`에 추가된다.

## 안정성 원칙

- 새 필드는 1.x에서 추가될 수 있지만 기존 필드의 의미와 타입은 변경하지 않는다.
- 필드 삭제, 지표 단위 변경, 기본 정규화 변경은 새 스키마 식별자가 필요하다.
- 같은 입력, 옵션, seed, 패키지 버전은 의미가 같은 JSON을 생성해야 한다.
- JSON 키 순서는 계약이 아니며 소비자는 이름으로 필드를 읽어야 한다.
- CER·WER의 `micro`와 `macro`는 0~1로 제한되지 않는다. 특히
  `rate_mode="standard"`에서는 삽입이 많으면 1보다 클 수 있다.

공개 Python 타입은 `nlptutti.comparison_types`에서 제공하며 wheel에는
PEP 561의 `py.typed` 마커가 포함된다.
