# Nlptutti 기여 안내

버그 수정, 지표 검증, 공급자 출력 어댑터, 문서 개선을 환영합니다. 이
저장소는 기존 사용자의 평가 결과와 기본값을 호환성 계약으로 취급합니다.

## 개발 환경

```bash
git clone https://github.com/hyeonsangjeon/computing-Korean-STT-error-rates.git
cd computing-Korean-STT-error-rates
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install pytest build twine
python -m pytest test -q
```

Windows PowerShell에서는 활성화 명령만 `.venv\Scripts\Activate.ps1`로
바꿉니다. 패키지는 Python 3.8 이상을 지원하며 pull request CI가 3.8부터
3.14까지 검사합니다.

배포 산출물까지 확인하려면 다음을 실행합니다.

```bash
python -m build
python -m twine check dist/*
```

wheel을 새 가상환경에 설치한 뒤 import, README 빠른 시작,
`nlptutti --help`, 비교 번들 생성을 확인하는 단계도 CI에 포함되어 있습니다.

## 변경 원칙

- `get_cer`, `get_wer`, `get_crr`의 인자 순서와 기존 기본값을 바꾸지 않습니다.
- 새 정규화나 진단 규칙은 이름이 있는 명시적 opt-in 옵션으로 시작합니다.
- `normalized`와 `standard` 계산식을 구분하고 둘 다 회귀 테스트합니다.
- 공개 JSON 구조를 바꾸면 schema version과 하위 호환성 정책을 함께 제안합니다.
- 같은 입력과 옵션에서 JSON·Markdown 결과가 결정적이어야 합니다.
- 점수 계산을 복제하지 말고 기존 공개 함수와 공용 alignment 경로를 재사용합니다.
- 새 runtime 의존성은 설치 크기, Python 지원 범위, 라이선스 영향을 설명합니다.

패키지 코드, README, 공개 API를 변경하면 `pyproject.toml` version과
`CHANGELOG.md`를 함께 갱신해야 합니다. pull request의 release policy가 이를
검사합니다.

## 테스트와 fixture

버그를 수정할 때는 수정 전 실패하는 최소 테스트를 먼저 추가합니다. 지표
변경은 사람이 계산할 수 있는 작은 reference/hypothesis, 기대 치환·삭제·삽입
횟수, 적용한 `rate_mode`, 문장부호·Unicode 옵션을 기록해야 합니다.

fixture는 다음 원칙을 지킵니다.

- 실제 사용자, 고객, 회사 내부 transcript와 음성을 올리지 않습니다.
- 이름, 전화번호, 계정, 비공개 상품명 등 식별 가능한 정보를 합성 예제로 바꿉니다.
- 외부 공개 응답을 그대로 복사하기보다 공식 필드 계약에 맞는 작은 합성 JSON을 작성합니다.
- 외부 데이터나 모델 자산이 꼭 필요하면 출처, license, 재배포 허용 범위를 먼저 확인합니다.
- 저장소 코드의 MIT license가 제3자 데이터·모델·가중치에 자동 적용된다고 가정하지 않습니다.

## 공급자 어댑터 제안

공급자 출력 파서는 SDK 호출이 아니라 **저장된 출력만 읽는 순수 어댑터**여야
합니다. 제안 이슈와 PR에는 다음 정보를 포함합니다.

1. 공급자와 제품/API의 정확한 이름
2. 공식 schema 문서 URL과 검증한 API/schema version
3. 평가 문자열로 선택할 필드와 segment 결합 정책
4. 필수·선택 필드, 빈 성공 결과, 실패 상태, timestamp 단위
5. 알 수 없는 version과 malformed input을 fail-closed 처리하는 테스트
6. credential, 네트워크, SDK, 모델 runtime 없이 실행되는 합성 fixture

provider 자동 감지는 추가하지 않습니다. 비슷한 JSON 구조를 추측해 잘못된
문장을 평가하는 것보다 사용자가 provider와 version을 명시하는 계약을
우선합니다.

## 문서 기여

README 첫 화면은 설치, 단일 평가, 시스템 비교, 결과 저장 순서를 유지합니다.
긴 함수 설명은 `docs/` 또는 사용자 매뉴얼로 연결합니다. 예제의 기대값은
테스트 fixture에서 계산한 값만 사용하고 구현 전 기능이나 재현하지 않은 성능을
홍보하지 않습니다.

## Pull request 전 확인

```bash
python -m pytest test -q
python -m build
python -m twine check dist/*
```

- 공개 API·기본값·schema 영향과 마이그레이션 필요 여부를 설명합니다.
- 새 동작의 정상·경계·실패 테스트를 포함합니다.
- 실제 transcript나 secret이 diff와 fixture에 없는지 확인합니다.
- 외부 자료를 사용했다면 고정 commit 또는 version, license, 독립 구현 범위를 기록합니다.
- 변경 버전의 한국어 `CHANGELOG.md` 항목을 추가합니다.

보안 취약점은 공개 이슈 대신 [Security policy](SECURITY.md)의 비공개 경로로
제보하십시오.
