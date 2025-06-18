# Changelog

모든 중요한 변경 사항은 이 파일에 기록됩니다.


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