# Nlptutti 공개 채택 지표 검토

## 문서 정보

- 검토 시점: `30일 / 60일 / 90일`
- 수집 시각(UTC):
- 검토 대상 버전:
- 릴리스 날짜와 SHA:
- 기준선: `docs/adoption/2026-08-21-baseline.json`
- 수집 실패·rate limit:

## GitHub 14일 snapshot

- window start/end UTC:
- 누적 stars:
- window 신규 stars:
- 누적 forks:
- window 신규 forks:
- views / unique visitors:
- clones / unique cloners:
- 상위 referrer raw count:
- 상위 path raw count:

기준선도 14일 GitHub 창만 사용합니다. views와 clones를 나누거나 unique 값을
확인된 사용자 수로 표현하지 않습니다.

## PyPIStats

- data through:
- category: `without_mirrors`
- 최근 1일:
- 최근 7일:
- 최근 14일:
- 최근 30일:
- 일별 spike 또는 누락:

30일 합계와 30일 일별 자료를 함께 저장합니다. downloads에는 CI/CD가 포함될
수 있으며 사용자·설치 성공·활성 사용을 뜻하지 않습니다.

## 공개 코드와 외부 상호작용

- `"import nlptutti"` indexed files:
- `"from nlptutti"` indexed files:
- 소유자 repo 제외 distinct public repositories:
- `"nlptutti" "compare_systems"` indexed files/repositories:
- `"nlptutti compare"` indexed files/repositories:
- comparison/schema/adapter 외부 issues:
- comparison/schema/adapter 외부 PRs:
- 재현 가능한 외부 사용 링크:

검색 결과에는 fork·notebook·비활성 코드가 포함될 수 있고 private 사용은 보이지
않습니다. 직전 snapshot과 query 문구를 똑같이 유지합니다.

## 질적 신호

- 설치에서 막힌 질문:
- 지표 의미 또는 기본값 질문:
- comparison 입력/schema 질문:
- provider adapter 요청:
- correctness/privacy 보고:
- 문서에서 반복되는 이탈 지점:

## 판단

- 확인된 사실:
- 아직 추론인 내용:
- 즉시 고칠 blocker:
- 다음 patch 후보:
- 0.1.0 안정성 조건에 미치는 영향:

star, traffic, download 변화와 특정 기능 사이의 인과를 단정하지 않습니다.
표본이 작으면 비율 대신 raw count를 유지하고 패키지 telemetry는 추가하지
않습니다.
