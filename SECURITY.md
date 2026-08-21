# 보안 정책

## 지원 버전

보안 수정은 PyPI에 공개된 최신 `nlptutti` 버전에 우선 적용합니다. 이전
버전에서 문제가 확인되면 최신 버전에서도 재현되는지 먼저 확인해 주십시오.
지원 종료 버전에 별도 backport를 보장하지 않습니다.

## 비공개 제보

취약점, 악의적으로 조작한 입력에 의한 비정상 동작, 배포·Trusted Publisher
설정 문제, 의존성 공급망 문제는 공개 issue나 discussion에 올리지 마십시오.

[GitHub private vulnerability report](https://github.com/hyeonsangjeon/computing-Korean-STT-error-rates/security/advisories/new)를
사용해 다음 정보를 보내 주십시오.

- 영향받는 `nlptutti` 버전과 Python/운영체제
- 재현 가능한 최소 입력과 실행 명령
- 예상 영향과 실제 결과
- 가능한 경우 완화책 또는 수정 제안

실제 고객 transcript, 음성, credential, access token, 개인식별정보는 제보에
첨부하지 마십시오. 문제를 재현할 수 있도록 민감 정보를 제거한 합성 입력으로
바꾸고, 꼭 필요한 비공개 자료의 전달 방식은 maintainer와 먼저 합의하십시오.

접수 사실과 공개 일정을 가능한 범위에서 비공개로 조율합니다. 수정이 준비되기
전에 취약점 세부 내용을 공개하지 말아 주십시오. 이 문서는 응답 시간이나 수정
기한에 대한 서비스 수준을 보장하지 않습니다.

## 공개 이슈로 적합한 내용

일반적인 metric correctness, 문서 오류, 공개 schema 지원 제안은 해당 issue
template을 사용하십시오. 보안 영향이 불명확하면 먼저 비공개 제보 경로를
선택하는 편이 안전합니다.
