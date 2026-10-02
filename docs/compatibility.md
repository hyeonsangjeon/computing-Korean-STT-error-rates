# 설치본 호환성 검증

Python 3.8 지원과 `jiwer>=3,<5` 선언을 유지합니다. 모든 OS와 Python 버전의
곱집합을 실행하는 대신 다음 조합을 CI에서 검사합니다.

| 환경 | Python | jiwer | 검증 |
| --- | --- | --- | --- |
| Linux | 3.8~3.14 | 해당 환경에서 설치 가능한 최신 `<5` | 소스·sdist 테스트, wheel/sdist 설치 smoke |
| Linux | 3.8 | 3.0.0 하한 | 격리 wheel 전체 테스트·CLI |
| Linux | 3.12 | 최신 3.x | 격리 wheel 전체 테스트·CLI |
| Windows, macOS | 3.12 | 최신 4.x | 격리 wheel 전체 테스트·CLI |

대표 OS 검사는 한글·공백 경로, UTF-8, CRLF 입력과 기존 파일 교체를 포함합니다.
OS별 모든 Python·jiwer 조합을 보증한다는 뜻은 아닙니다. resolver가 호환되지
않는 버전을 골라 실패하면 해당 job에서 드러나며 조용히 범위를 낮추지 않습니다.

기존 Python 7개 job에 대표 조합 4개 job을 추가합니다. 각 job은 외부 모델 없이
빌드·설치·테스트하며 소요 시간을 로그 마지막에 기록합니다. 패키지 설치 시에는
네트워크가 필요할 수 있지만, 설치 후 `nlptutti sample`과 비교는 오프라인입니다.

로컬에서도 같은 검사를 실행할 수 있습니다.

```bash
python -m pip install build
python .github/scripts/verify_compatibility.py --jiwer "jiwer>=4,<5"
```
