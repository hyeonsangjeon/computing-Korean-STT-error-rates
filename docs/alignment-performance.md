# 정렬 커널 성능 기준선

`explain_errors()`와 개체명 평가가 사용하는 backtrace 정렬은
`nlptutti.alignment.align_sequences()` 하나로 통합되어 있습니다. 동률인 편집
경로에서는 `equal/substitute`, `insert`, `delete` 순서를 유지합니다. 이 순서는
최종 편집거리뿐 아니라 오류 귀속 결과에도 영향을 주므로 호환성 계약의
일부입니다.

## 측정 방법

```bash
python benchmarks/alignment_baseline.py
```

스크립트는 같은 프로세스에서 통합 전 알고리즘과 현재 공용 커널을 각각 다섯
번 실행하고 중앙 실행시간과 최대 peak memory를 비교합니다. 한국어 문구를
반복한 8개 합성 문장 쌍을 사용하며 네트워크나 외부 데이터는 필요하지
않습니다. 실행시간 또는 peak memory 비율이 기존 구현의 `1.25`를 넘으면
GitHub Actions 형식의 경고를 출력합니다.

## 최초 기준선

- 측정일: 2026-08-21
- 환경: macOS 26.1, arm64, CPython 3.14.6
- 실행시간: 기존 `0.129841초`, 공용 커널 `0.127856초` (`0.985배`)
- peak memory: 기존 `141,520바이트`, 공용 커널 `158,184바이트` (`1.118배`)

이 값은 특정 장비에서 얻은 회귀 검토 기준이며 다른 운영체제나 Python
버전에서 같은 절대값을 보장하지 않습니다. 경고는 검토 신호일 뿐 테스트
실패로 취급하지 않습니다. 알고리즘 변경 시에는 golden fixture와 exhaustive
small-input 테스트를 먼저 통과시킨 뒤 이 기준선을 다시 측정합니다.
