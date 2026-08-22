# 릴리스와 0.1.0 안정성 정책

## 현재 판단

`0.0.0.20`은 새 comparison API, CLI, `nlptutti.comparison/1.0` schema가 처음
사용자에게 배포된 **Beta patch release**입니다. `0.0.0.21`은 같은 코드와
계약을 유지하면서 README의 공식 계산식 이미지를 복원한 문서 patch입니다.
기존 metric API는 충분한 사용 이력이 있지만 비교 계약의 30·60·90일 채택
검토가 진행 중이므로 아직 `0.1.0`과 Stable classifier를 선언하지 않습니다.

`0.0.0.20`과 `0.0.0.21` 두 patch release에서 아래 계약을 검증합니다. 두 번째
patch 배포만으로 `0.1.0` 조건이 끝나는 것은 아니며 실제 호환성·오류 보고와
30·60·90일 채택 검토 결과를 함께 확인합니다.

## 기능 상태

| 기능 | 0.0.0.21 상태 | 호환성 약속 |
| --- | --- | --- |
| 기존 CER·WER·CRR·corpus·keyword·entity API | Beta, 기존 계약 유지 | 인자 순서, 반환 키와 기본값을 변경하지 않습니다. |
| `compare_systems`와 CLI | provisional Beta | patch 기간에는 필수 필드를 제거하지 않고 추가 정보는 선택 필드로만 검토합니다. 파괴적 변경은 새 schema가 필요합니다. |
| `nlptutti.comparison/1.0` JSON | provisional Beta | 같은 schema 안에서 기존 필드의 의미·단위를 바꾸지 않습니다. |
| 결정적 JSON/Markdown bundle | Beta | 같은 입력·옵션·패키지 버전에서 같은 내용을 생성합니다. |
| paired percentile bootstrap | Beta | 기본 비활성이며 방법, seed, resample 수, sampling unit을 결과에 기록합니다. |
| spacing/top-edit 진단 | stable rule within `korean-v1` | rule name과 version을 결과에 기록합니다. |
| number/unit 및 josa/eomi 진단 | experimental | 형태소 분석으로 표현하지 않으며 오탐 경계를 문서화합니다. |
| Azure Speech·Whisper adapter | versioned, narrow support | provider/schema를 명시하며 알려지지 않은 형식은 거부합니다. |

## 0.1.0 후보 조건

다음 조건을 모두 확인한 뒤 별도 release issue에서 결정합니다.

1. comparison API, schema, CLI가 최소 두 번의 실제 patch release에 포함됩니다.
2. 공개된 patch 사이에서 기존 metric 기본값과 golden 결과가 유지됩니다.
3. Python 3.8~3.14 test, wheel/sdist build, `twine check`, 깨끗한 wheel smoke가 통과합니다.
4. README, PyPI 설명, GitHub Pages의 첫 실행 fixture와 기대값이 일치합니다.
5. JSON/Markdown 결정성, 원문 기본 제외, 진단 토큰 경고가 회귀 테스트로 유지됩니다.
6. paired bootstrap의 방법과 한계가 문서화되고 실제 사용자 오류 보고를 검토합니다.
7. 지원 provider/schema와 비지원 범위를 명시하고 자동 감지를 추가하지 않습니다.
8. CHANGELOG, migration note, CITATION version, GitHub Release, PyPI metadata가 같은 버전을 가리킵니다.
9. 30/60/90일 adoption review에서 발견된 correctness·설치·문서 blocker를 처리합니다.

조건을 만족해도 classifier 변경은 별도 판단입니다. `0.1.0`은 공개 계약을
안정적으로 유지하겠다는 신호이고, 모든 roadmap 기능이나 모든 STT provider를
지원한다는 의미가 아닙니다.

## 0.0.0.20 migration note

기존 호출은 변경할 필요가 없습니다.

```python
get_cer(reference, hypothesis)
get_wer(reference, hypothesis)
get_crr(reference, hypothesis)
```

위 호출은 계속 `rate_mode="normalized"`, `rm_punctuation=True`,
`unicode_normalization=None`을 사용합니다. 표준 지표, bootstrap, 한국어 진단,
원문 포함은 각각 명시적 옵션을 선택해야 합니다.

새 비교 기능을 도입하는 코드는 반환 dict의 key 순서나 Markdown 문구보다
`schema`, 필드 이름, metric 단위에 의존해야 합니다. `raw_inputs`와
`diagnostics`는 요청한 경우에만 존재할 수 있는 선택 필드입니다.

## 릴리스 체크리스트

- [ ] `pyproject.toml`, `CITATION.cff`, `CHANGELOG.md`의 버전과 날짜가 일치합니다.
- [ ] 공개 API signature와 기존 golden fixture가 통과합니다.
- [ ] Python 3.8~3.14 GitHub Actions가 모두 통과합니다.
- [ ] wheel과 sdist를 빌드하고 `twine check`를 통과합니다.
- [ ] 깨끗한 환경에서 wheel을 설치해 import, `py.typed`, README 예제, CLI help와 bundle을 확인합니다.
- [ ] wheel/sdist의 METADATA description이 현재 README와 정확히 일치합니다.
- [ ] 지원 schema, experimental 기능, 알려진 제한과 개인정보 경고를 검토합니다.
- [ ] main의 검증된 SHA에서 GitHub Release와 PyPI가 같은 산출물을 사용합니다.

## 배포 경로

현재 GitHub Actions Trusted Publisher 경로를 유지합니다. main push의 Python
matrix가 성공한 동일 SHA를 checkout해 wheel/sdist를 다시 검증하고 GitHub
Release를 만든 뒤, `pypi` environment에서 OIDC `id-token: write` 권한으로
PyPI에 게시합니다. 장기 `PYPI_API_TOKEN`을 다시 도입하지 않습니다.

같은 version이 이미 PyPI에 있으면 다시 업로드하지 않습니다. README와 PyPI
description이 다르거나 package 파일이 tag 이후 바뀌었으면 version bump 없이
배포를 진행하지 않습니다.
