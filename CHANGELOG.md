# Changelog

모든 중요한 변경 사항은 이 파일에 기록됩니다.

## [0.0.0.20] - 2026-08-21

---

### Added
- 두 개 이상 STT 시스템의 정렬된 출력에서 CER·WER·CRR micro/macro와 pairwise delta를 계산하는 `compare_systems` 공개 API 추가.
- ID mapping 또는 순서 기반 corpus JSON을 받아 비교 결과를 출력하는 `nlptutti compare` CLI 추가.
- 자동화용 `nlptutti.comparison/1.0` JSON과 검토용 Markdown을 결정적으로 생성하고 원자적으로 저장하는 결과 번들 API 추가.
- 문장 쌍을 유지하는 percentile paired bootstrap CER·WER delta 신뢰구간 추가. 기본값 `bootstrap=0`은 비활성.
- Microsoft Azure Speech short-audio simple 응답과 오픈소스 OpenAI Whisper `transcribe()` 결과를 읽는 명시적 provider adapter 추가.
- 띄어쓰기 경계, 숫자·단위, 조사·어미 인접 치환, 상위 문자 편집을 분리하는 opt-in `korean-v1` 진단 프로필 추가.
- 공개 비교 결과 `TypedDict`, `py.typed`, comparison schema 문서와 공급자·진단·비교 매뉴얼 추가.
- 기여, 인용, 비공개 보안 제보 정책과 provider·metric·문서 Issue Form 추가.
- 릴리스 직전 GitHub 14일 traffic, PyPIStats 일별·30일, 공개 code search를 분리한 채택 기준선과 30·60·90일 검토 템플릿 추가.

### Changed
- `explain_errors`와 개체명 평가의 중복 full-matrix backtrace를 동일한 tie-breaking과 위치 계약을 보존하는 공용 alignment 커널로 통합.
- README와 PyPI 첫 화면을 설치, 단일 CER, 두 시스템 비교, JSON/Markdown 저장 순서로 단축하고 같은 fixture의 기대값을 CI에서 검증.
- wheel smoke가 `py.typed`, console script help, 비교 API와 실제 CLI 번들 생성을 source tree 밖에서 검사하도록 강화.
- sdist에 전체 `docs/`, example corpus, 중첩 test fixture가 포함되도록 manifest 범위를 보강.

### Compatibility
- `get_cer`, `get_wer`, `get_crr`와 기존 공개 API의 인자 순서, 반환 키, `rate_mode="normalized"`, `rm_punctuation=True`, `unicode_normalization=None` 기본값을 유지.
- 비교 API의 bootstrap과 한국어 진단, 원문 포함은 모두 명시적으로 선택할 때만 활성화.
- Beta classifier를 유지하고 `0.1.0` 선언은 comparison schema와 CLI가 최소 두 patch release에서 검증될 때까지 보류.

### Security
- 비교 보고서에서 원문을 기본 제외하고 fingerprint만 기록하며, 진단 토큰 또는 원문 opt-in 사용 시 공유 전 검토 경고를 제공.
- 실제 사용자 transcript를 공개 issue fixture로 올리지 않는 정책과 GitHub private vulnerability report 경로 추가.

### Tests
- comparison 입력 정렬·schema·CLI, JSON/Markdown golden, paired bootstrap, alignment exhaustive small-input, provider malformed input, 한국어 진단 오탐 경계 테스트 추가.
- Python 3.8~3.14 CI에서 wheel/sdist, metadata, 깨끗한 wheel 설치와 README 첫 실행 경로를 계속 검증.

### Known limitations
- provider 자동 감지, Azure detailed/batch/fast, OpenAI API, AWS·Google·FunASR 전용 adapter는 이번 릴리스 범위가 아님.
- 숫자·단위와 조사·어미 진단은 형태소 분석이 아닌 experimental 문자열 휴리스틱.
- paired bootstrap은 주어진 평가 corpus의 문장 sampling 변동을 나타내며 모델 정확도의 보편적 확률 보장이 아님.

## [0.0.0.19] - 2026-08-13

---

### Changed
- README와 PyPI 패키지 안내 첫 화면에 CER·WER·CRR의 입력, 반환 키, 점수 방향과 사용 경계를 대조하는 표를 추가.
- 빠른 시작에서 같은 정답·인식 문장으로 CER·WER·CRR를 모두 계산하고 기대값과 치환 횟수를 확인하도록 예제를 확장.
- `rate_mode="normalized"`는 오류율 분모 정책이며 입력 문자열을 바꾸는 한국어 텍스트 정규화가 아님을 명시.
- 실제 문자열 변환은 선택 옵션인 `unicode_normalization`이 담당하며 기존 기본값 `None`을 유지한다는 점을 별도로 안내.

### Tests
- 배포 wheel의 빠른 시작 스모크 테스트가 세 핵심 지표의 공개 반환 계약과 문서 기대값을 함께 검사하도록 강화.
- 공백·문장부호, CRR 반올림, 분모 방식과 Unicode 정규화의 경계를 고정하는 문서 계약 테스트 추가.


## [0.0.0.18] - 2026-08-03

---

### Added
- 일반 텍스트와 JSON, SRT, TSV 형식의 STT 출력을 공급자 중립적으로 읽는 `parse_transcript` 공개 API 추가.
- JSON 최상위 `text`를 기본으로 사용하고, 사용자가 `json_text_policy="segments_fallback"`을 지정한 경우에만 `segments[*].text`를 결합하는 명시적 입력 정책 추가.
- 기존 CER, WER, CRR 함수로 평가한 결과와 실제 옵션, 패키지 버전, 입력 provenance를 `schema_version="1.0"` JSON 계약으로 반환하는 `evaluate_transcript` 추가.
- 구조화 입력 오류를 빈 문자열로 숨기지 않고 전달하는 `TranscriptFormatError` 추가.
- 네 입력 형식의 사용법, 시간 정보 처리, 오류 계약, 개인정보 주의사항을 설명하는 한국어 문서 추가.

### Changed
- SRT cue와 TSV `text` 열은 구간별 공백을 정리한 뒤 ASCII 공백 하나로 연결하도록 규칙을 고정.
- 평가 여권은 reference와 hypothesis 원문을 복제하지 않고 SHA-256, 문자 수, UTF-8 byte 수만 기록하도록 구성.
- FunASR CLI의 구조화 출력 형식을 고정 커밋에서 검토하되 모델·런타임 의존성 없이 독립 구현하고, 참조 범위와 라이선스 경계를 문서화.
- 테스트 워크플로와 PyPI 배포 워크플로에서 빌드된 wheel을 source tree 밖에 다시 설치한 뒤 README 빠른 시작 경로를 실행하도록 배포물 검증 강화.

### Compatibility
- `get_cer`, `get_wer`, `get_crr`를 포함한 기존 공개 API와 반환값은 변경하지 않음.
- 새 평가 API도 기존 기본값인 `rate_mode="normalized"`, `unicode_normalization=None`, `rm_punctuation=True`를 유지.
- FunASR 또는 다른 STT 모델의 실행 패키지를 기본 의존성에 추가하지 않음.

### Tests
- 같은 전사를 text, JSON, SRT, TSV로 입력했을 때 동일한 평가 문자열과 CER·WER·CRR이 생성되는 골든 테스트 추가.
- JSON 필드·정책, SRT cue·타임코드, TSV 헤더·시간 값과 malformed fixture에 대한 실패 계약 테스트 추가.
- 평가 여권의 JSON 직렬화, 결정성, 원문 미포함, 옵션·provenance 기록을 검증하는 테스트 추가.

---


## [0.0.0.17] - 2026-07-31

---

### Changed
- 검색 방문자가 README 상단에서 설치, CER·WER 첫 평가, 개체명 보존 평가를 순서대로 실행할 수 있도록 빠른 시작 경로를 추가.
- 각 예제의 실제 출력과 완전 일치·개체명 완전 보존 성공 기준을 명시.
- 공식 비교용 `rate_mode="standard"`와 기존 결과 재현용 기본값 `rate_mode="normalized"`를 첫 사용 단계에서 구분해 안내.
- 중복 설치 안내를 제거하고 지표 선택, 계산식, 관련 자료, 상세 사용법의 문서 구조를 정리.

---

## [0.0.0.16] - 2026-07-22

---

### Changed
- README에 CER, WER, CRR, 코퍼스, 키워드, 개체명, 오류 분석 API를 목적별로 선택할 수 있는 한국어 기준표를 추가.
- 표준 비교용 `rate_mode="standard"`와 이전 결과 호환용 기본값 `rate_mode="normalized"`의 선택 기준을 명시.
- 선택적 유니코드 정규화와 한국어 사용자 매뉴얼 연결을 안내하고, PyPI 패키지 설명을 README와 동기화.

---

## [0.0.0.15] - 2026-07-17

---

### Changed
- PyPI 배포 인증을 장기 API 토큰 방식에서 GitHub Actions OIDC 기반 Trusted Publishing으로 전환.
- `pypi` environment와 배포 워크플로의 신원을 PyPI 프로젝트에 직접 연결하도록 구성.
- 배포 산출물에 PyPI 디지털 증명(attestation)을 함께 발행하도록 설정.

### Security
- 배포 워크플로에서 `PYPI_API_TOKEN` 참조를 제거하고, PyPI 업로드 job에만 단기 OIDC 토큰 발급 권한을 부여.
- 최초 Trusted Publishing 배포 성공을 확인한 뒤 기존 GitHub Actions 저장소 비밀 값을 제거하도록 전환 절차를 분리.

---

## [0.0.0.14] - 2026-07-17

---

### Changed
- main 브랜치의 Python 3.8~3.14 CI가 성공한 뒤 새 버전을 자동으로 PyPI에 배포하도록 릴리스 흐름을 개선.
- 검증한 동일 wheel과 source archive를 GitHub Release와 PyPI 배포에 사용하도록 구성.
- 실제 업로드 job을 GitHub의 pypi environment에 연결해 Deployments 상태로 확인할 수 있도록 수정.

### Release policy
- pyproject.toml의 버전이 PyPI에 없을 때만 새 패키지를 업로드.
- 같은 버전이 이미 존재하면 PyPI 설명과 현재 README.md가 정확히 일치하는지 검사하고, 일치하면 중복 배포를 생략.
- 같은 버전의 PyPI 설명과 README.md가 다르면 버전 증가 없이 문서가 변경된 것으로 보고 배포 워크플로를 실패 처리.
- 같은 버전의 Git 태그 이후 패키지 소스나 메타데이터가 변경된 경우에도 버전 증가를 요구.
- wheel과 source archive의 이름, 버전, README 본문이 모두 일치한 경우에만 릴리스 산출물로 사용.

---

## [0.0.0.13] - 2026-07-17

---

### Changed
- README와 PyPI 설명을 특정 STT 공급자에 종속되지 않는 문구로 수정.
- 지원 대상 예시는 Microsoft Azure Speech를 먼저 안내하고 Amazon Transcribe, Google Cloud Speech-to-Text, OpenAI Whisper를 함께 명시.
- PyPI 패키지 요약에 CER, WER, CRR, 키워드, 개체명 평가 범위를 명확히 표시.

---

## [0.0.0.12] - 2026-07-16

---

### Added
- 기존 정규화 오류율과 표준 CER/WER를 명시적으로 선택하는 rate_mode 옵션 추가.
  - 기본값은 이전 버전과 동일한 normalized로 고정.
  - standard는 사용자가 직접 지정한 경우에만 적용.
- 여러 문장을 한 번에 평가하는 evaluate_corpus 추가.
  - micro/macro CER·WER, 편집 횟수 합계, 완전 일치 문장 수, 문장 오류율 제공.
- 키워드 실제 언급 횟수와 false positive/false negative를 집계하는 evaluate_keywords 추가.
  - 선택적으로 ORG, PRODUCT와 같은 라벨별 precision, recall, F1 제공.
- 참조 개체명 span의 문자 오류율과 개체명 언급 F1을 함께 제공하는 evaluate_entities 추가.
  - Entity CER micro/macro, 개체명·라벨별 편집 횟수, 누락·추가·오인식 목록 제공.
  - 사용자가 명시한 aliases만 동일 개체의 허용 전사형으로 처리하며 퍼지 매칭은 적용하지 않음.
  - NE-WER, NEER, Spoken NER 관련 논문과 한국어 적용 기준을 README와 사용자 매뉴얼에 명시.
  - ContextASR-Bench, NVIDIA NeMo-Skills, Teklia ie-eval, PIER의 실제 공개 구현과 Nlptutti의 차이를 README와 사용자 매뉴얼에 명시.
- 문자·단어 단위 정렬과 치환/삭제/삽입 빈도를 보여주는 explain_errors 추가.
- NFC, NFD, NFKC, NFKD 유니코드 정규화를 선택할 수 있는 unicode_normalization 옵션 추가.

### Changed
- Python 지원 범위를 실제 CI와 맞게 3.8 이상으로 명확히 함.
- JiWER 지원 범위를 3 이상 5 미만으로 명시.
- 빌드 백엔드를 wheel 명령이 내장된 setuptools 70.1 이상으로 현대화.
- GitHub Actions를 Node.js 24 기반 checkout v6와 setup-python v6로 업데이트.
- make_keyword_pattern의 조사 목록을 생략하면 기본 한국어 조사 목록을 사용하도록 개선.
- README에 기본 정규화 정책, 표준식 선택, 새 API 예제와 사용자 매뉴얼 링크 추가.

### Fixed
- 공백이 포함된 입력 키워드도 붙여 쓴 표현과 띄어 쓴 표현을 모두 찾도록 수정.
- README 라이선스 배지가 다른 저장소를 가리키던 링크 수정.
- README의 키워드 출력 예시에서 잘못 표시된 키워드명 수정.

### Compatibility
- get_cer, get_wer, get_crr의 기본 계산 결과와 기존 반환 키를 그대로 유지.
- calculate_keyword_error_rate_with_pattern의 문장 존재 여부 기반 집계 방식 유지.
- 새 표준식과 유니코드 정규화는 모두 명시적으로 선택할 때만 적용.
- evaluate_entities는 새 API로만 추가하고 기존 함수의 계산 및 매칭 결과는 변경하지 않음.
- evaluate_entities도 rate_mode="normalized", unicode_normalization=None을 기본값으로 사용.

### Tests
- 기본값 고정, 표준식, 빈 참조문장, 유니코드 정규화, 코퍼스 집계, 반복 키워드, 오탐, 오류 정렬 테스트 추가.
- 개체명 span CER, 별칭 opt-in, 조사·띄어쓰기, 내부/외부 삽입, 반복 언급, 라벨 집계, 입력 검증 테스트 추가.
- PIER와 ContextASR-Bench의 고정 커밋 실행 결과를 fixture로 보존하고, 공통 동작과 문자/단어 단위 차이를 검증하는 교차 회귀 테스트 4개 추가.
- 기존 테스트를 포함해 총 54개 테스트로 회귀 범위 확대.

---

## [0.0.0.11] - 2026-06-29

---

### Fixed
- 빈 입력 처리 안정화:
  - `get_cer("", "")`, `get_wer("", "")`가 `ZeroDivisionError`를 내지 않고 오류율 `0.0`을 반환하도록 수정.
  - `get_crr("", "")`는 완전 일치로 보고 `1.0`을 반환하도록 수정.
  - 참조문장이 비어 있고 가설문장만 있는 경우에는 삽입 오류로 계산하도록 동작을 명확히 함.
- CER/CRR 전처리 정책 수정:
  - `rm_punctuation=False`일 때도 CER/CRR의 공백 제거 정책이 유지되도록 수정.
  - `rm_punctuation`은 문장부호 제거 여부만 제어하도록 정리.
- 키워드 패턴 매칭 안정화:
  - `C++`처럼 정규식 특수문자가 포함된 키워드에서도 `make_keyword_pattern`이 안전하게 동작하도록 수정.
  - `비삼성전자제품`, `삼성전자제품`처럼 긴 단어 내부에 포함된 부분문자열 오탐을 줄이도록 키워드 경계 검사를 추가.
- 키워드 오류율 입력 검증 추가:
  - `reference_sentences`와 `hypothesis_sentences` 길이가 다르면 조용히 누락하지 않고 `ValueError`를 발생시키도록 수정.

### Changed
- 패키징 메타데이터를 `pyproject.toml` 중심으로 정리:
  - 중복 메타데이터를 가진 `setup.py` 제거.
  - 사용하지 않는 `pandas` 의존성 제거.
- 기본 한국어 조사/어미 목록 보강:
  - `COMPLEX_JOSA`에 `은`, `는` 추가.
  - `COMPLEX_EOMI`에 `한다` 추가.
- GitHub Actions 개선:
  - 릴리스 배포 전에 테스트를 실행하도록 PyPI 배포 워크플로 개선.
  - push/PR에서 Python 3.8~3.14 매트릭스로 테스트, 빌드, `twine check`를 수행하는 테스트 워크플로 추가.

### Tests
- 빈 문자열, 빈 참조문장, 공백/문장부호 정책, 정규식 특수문자 키워드, 부분문자열 오탐, 입력 리스트 길이 불일치 테스트 추가.
- 기존 장문 샘플 테스트와 기본 CER/WER/CRR 테스트를 함께 통과하도록 검증 범위 확대.

---

## [0.0.0.10] - 2025-06-18

---

### Fixed
- README.md의 이미지 경로 수정:
  - PyPI에서 이미지가 표시되지 않는 문제 해결
  - GitHub 상대 경로 (`blob/main`) → GitHub raw URL (`raw.githubusercontent.com`) 변경
  - ER_CASE.png, FORMULA_CASE.png 이미지가 PyPI 패키지 설명 페이지에서 정상 표시되도록 개선

### Changed
- PyPI 패키지 메타데이터 개선:
  - 이메일 주소 설정 최적화
  - 의존성 정보 정리

---

## [0.0.0.9] - 2025-06-18

### Added
- `make_keyword_pattern`:  
  - 고유명사, 중요 키워드 등 한국어 단어가 문장 내에서 조사/어미와 결합하거나 띄어쓰기 변형이 있을 때도 robust하게 매칭할 수 있는 정규표현식 패턴 생성 함수 추가.
- `calculate_keyword_error_rate_with_pattern`:  
  - 여러 키워드(고유명사 등)를 대상으로 STT 인식 결과와 참조문장을 비교하여, 각 키워드별 인식 정확도와 전체 에러율을 일괄적으로 계산하는 함수 추가.
- `COMPLEX_JOSA`, `COMPLEX_EOMI`:  
  - 복합 조사, 어미 리스트 기본 제공.

### Changed
- README:  
  - 한국어 고유명사 인식 평가 관련 예제 및 함수 설명 추가.
  - 함수 사용법과 반환값 구조, NLP적 의의 등 상세 설명 보강.

### Fixed
- (해당 사항 없음)

---

## [0.0.0.8] - 이전 버전

### Added
- 문자 오류율(CER, Character Error Rate) 평가 함수.
- 단어 오류율(WER, Word Error Rate) 평가 함수.
- 음절 정확률(CRR, Character Recognition Rate) 평가 함수.
