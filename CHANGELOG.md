# Changelog

모든 중요한 변경 사항은 이 파일에 기록됩니다.


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
