# 공개 채택 지표 기준선

## 목적과 시점

이 문서는 comparison workflow가 처음 배포되기 전인 2026-08-21에 수집한
기준선입니다. 당시 PyPI 최신 버전은 `0.0.0.19`이고 `0.0.0.20`은 아직
게시되지 않았습니다. 원자료는
[`adoption/2026-08-21-baseline.json`](adoption/2026-08-21-baseline.json)에
보존했습니다.

측정은 런타임 telemetry를 추가하지 않고 GitHub와 PyPIStats의 집계, 공개
GitHub code search만 사용합니다. 서로 다른 기간이나 집계원을 나눠 전환율을
만들지 않습니다.

## 릴리스 전 기준선

### GitHub

GitHub traffic은 API가 제공하는 2026-08-07~2026-08-20 UTC 14일입니다.

| 항목 | raw count |
| --- | ---: |
| 누적 stars | 73 |
| 누적 forks | 11 |
| 14일 신규 stars | 0 |
| 14일 신규 forks | 0 |
| 14일 views | 22 |
| 14일 unique visitors | 17 |
| 14일 clones | 113 |
| 14일 unique cloners | 73 |

views와 clones는 같은 14일 창이지만 서로 다른 행동입니다. 둘을 나눠
전환율로 해석하지 않습니다. clone은 전체 repository clone 요청이며 사람이
실제로 패키지를 설치하거나 실행했다는 뜻이 아닙니다. unique 집계도 신원이
확인된 고유 사용자 수로 표현하지 않습니다.

상위 referrer 중 Google은 9 views/8 uniques였고 GitHub Pages는 1/1이었습니다.
상위 path는 Overview 20/15, 구조화 transcript 문서 1/1, issue 목록 1/1입니다.
이는 GitHub가 제공한 상위 목록이며 전체 유입을 완전히 분해한 값은 아닙니다.

### PyPIStats

PyPIStats `without_mirrors` 일별 자료는 2026-08-20까지 반영됐습니다.

| 창 | downloads |
| --- | ---: |
| 최근 1일 | 52 |
| 최근 7일 | 648 |
| 최근 14일 | 1,291 |
| 최근 30일 | 50,062 |

30일 값 가운데 2026-07-22~2026-07-26의 5일 합계가 47,266입니다. 급증은
원자료에서 확인되지만 원인은 이 집계로 알 수 없습니다. PyPIStats는 알려진
mirror를 제외하지만 CI/CD 다운로드는 포함하므로 이를 신규 사용자, 성공한
설치, 실제 제품 사용으로 부르지 않습니다. 후속 검토에서도 30일 합계만 보지
말고 같은 일별 시계열과 7일·14일 raw count를 함께 확인합니다.

### 공개 코드 검색

GitHub code search에서 대상 저장소 자체를 제외하고 정확한 문자열을 조회한
기준선입니다.

| query | indexed files/repos |
| --- | ---: |
| `"import nlptutti"` | 51 files |
| `"from nlptutti"` | 10 files |
| 두 query의 distinct repositories | 30 repos |
| 저장소 소유자의 다른 repo를 제외한 distinct repositories | 28 repos |
| `"nlptutti" "compare_systems"` | 0 files |
| `"nlptutti compare"` | 0 files |

28은 공개 index에서 보인 repository 수이지 dependent 사용자 수가 아닙니다.
fork, notebook, 복제 프로젝트, 비활성 코드가 섞일 수 있고 private repository와
검색 index에 없는 코드는 보이지 않습니다. comparison 검색 0은 기능 출시 전
기준선으로만 사용합니다.

comparison/schema/adapter 관련 외부 issue와 PR은 각각 0건입니다. 전체 역사에서
외부 작성 issue는 1건이지만 2022년 import 오류로 이번 기능과 무관하며, 외부
PR은 0건입니다.

## 30·60·90일 검토

릴리스 기준일을 2026-08-21로 둘 때 점검일은 다음과 같습니다.

| 검토 | 목표일 | 확인할 신호 |
| --- | --- | --- |
| 30일 | 2026-09-20 | 같은 GitHub 14일 snapshot, PyPIStats 30일/일별, comparison code search, 설치·schema correctness blocker |
| 60일 | 2026-10-20 | 반복되는 사용 질문, adapter 요청, 문서 이탈 지점, 외부 issue/PR |
| 90일 | 2026-11-19 | 공개 dependent repo의 comparison 사용, 외부 기여, schema 호환성, 0.1.0 후보 조건 |

GitHub traffic은 최근 14일만 제공하므로 각 검토일의 직전 14일을 기준선의
14일과 비교합니다. 30일 전체 traffic으로 이름을 바꾸지 않습니다. PyPIStats는
각 검토일에 최근 30일을 다시 받고 일별 값도 snapshot에 저장합니다.

각 검토는 [`adoption-review-template.md`](adoption-review-template.md)를 복사해
작성합니다. raw count가 작을 때 비율을 만들지 않고, star·download 변화가
기능 개선 때문에 발생했다고 단정하지 않습니다.

## 판정 원칙

- `compare_systems` 또는 CLI의 공개 code search 결과가 생기면 adoption 후보
  신호로 기록하되 실제 실행 여부는 주장하지 않습니다.
- correctness·privacy·설치 blocker가 한 건이라도 재현되면 star/download보다
  우선해 수정합니다.
- provider 요청 수는 지원 필요성의 후보일 뿐 모든 provider를 기본 의존성으로
  추가하는 근거가 아닙니다.
- 문서 referrer와 popular path는 상위 목록만 제공된다는 한계를 유지합니다.
- 숫자 상승이 없더라도 schema 호환성과 외부 재현 사례가 확인되면 품질 성과로
  별도 기록합니다.
- 패키지에 사용자 추적, 전화 home, install hook telemetry를 추가하지 않습니다.

## 출처와 재현

- [GitHub repository traffic API](https://docs.github.com/en/rest/metrics/traffic): 최근 14일 views와 clones, 상위 referrer/path
- [GitHub stargazers API](https://docs.github.com/en/rest/activity/starring): 기간 내 신규 star timestamp
- [GitHub code search API](https://docs.github.com/en/rest/search/search#search-code): 공개 기본 branch 중심의 문자열 검색
- [PyPIStats API](https://pypistats.org/api/): 알려진 mirror를 제외한 일별·최근 집계, 1일 1회 갱신
- [PyPIStats 한계](https://pypistats.org/faqs): CI/CD 포함과 mirror 관련 불확실성

API 응답이 실패하거나 rate limit에 걸리면 이전 값을 현재 값처럼 재사용하지
않고 수집 실패와 재시도 시각을 기록합니다.
