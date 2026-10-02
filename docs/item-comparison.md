# 어떤 문장에서 달라졌나요?

0.0.0.24부터 `include_items=True`로 문장별 점수·편집 횟수와 상위 악화/개선 ID를
확인할 수 있습니다. 기본값은 `False`여서 기존 보고서 크기는 그대로입니다.

```python
import nlptutti as nt

references = {"number": "12개", "spacing": "가 나", "entity": "김민수"}
systems = {
    "baseline": {"number": "13개", "spacing": "가 나", "entity": "김민수"},
    "candidate": {"number": "12개", "spacing": "가나", "entity": "김민서"},
}
labels = {
    "number": {"domain": "숫자"},
    "spacing": {"domain": "일반"},
    "entity": {"domain": "일반"},
}
report = nt.compare_systems(
    references, systems, rate_mode="standard",
    include_items=True, labels=labels, top_n=10,
)
pair = report["details"]["pairwise"][0]
print(pair["top_regressions"]["cer"])   # ['entity']
print(pair["top_improvements"]["cer"])  # ['number']
```

숫자는 고쳤지만 이름은 틀렸습니다. `spacing`의 CER delta는 `0.0`, WER delta는
`1.0`입니다. CER은 공백을 없애므로 띄어쓰기 오류는 WER로 확인합니다.
이름 오류를 집계했다고 NER 모델을 실행한 것은 아닙니다.

JSON `details.systems[].items[].metrics`에는 문장별 점수와 편집 횟수가 있습니다.
한 문장에서는 micro와 macro가 같습니다. 문장별 편집 횟수를 합하면 코퍼스 편집
횟수와 일치하며 별도 재정렬은 하지 않습니다. Markdown에는 상위 ID와 delta를
표시합니다. CER/WER delta의 크기로 정렬하고 동률은 ID 문자열 순서로 고정합니다.
변화 없는 문장은 상위 목록에서 제외하지만 전체 값은 JSON에 남습니다.

## 조건별 집계

`labels`의 도메인·잡음·길이 등은 사용자가 지정한 분류입니다. 음성 속성이나 길이를
자동으로 추정하지 않습니다. 모든 ID에 같은 필드 집합을 채워야 합니다. 순서 기반
입력의 기본 ID는 `"0"`, `"1"` 등이며 Python에서는 `ids=[...]`로 지정할 수 있습니다.

`slices`에는 필드·값별 표본 수, CER/WER/CRR micro/macro와 시스템 간 차이가
들어갑니다. 선택적 키워드·개체명 평가는 현재 전체 코퍼스에만 적용합니다.
각 라벨 필드의 표본 수 합계는 전체 문장 수와 같고 `labels_sha256`은 설정을
기록합니다. 표본 하나의 slice도 계산하지만 일반화 성능으로 해석하면 안 됩니다.

CLI에서는 `--include-items --labels labels.json --top-n 10`을 추가합니다.
원문은 여전히 `--include-transcripts`로 따로 선택합니다. ID와 라벨도 개인정보일
수 있어 `aggregate`와 상세/라벨 옵션을 함께 쓰면 오류로 알립니다.
