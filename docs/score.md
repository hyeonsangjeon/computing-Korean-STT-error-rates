# STT 결과 한 개 평가하기

`python -m pip install nlptutti==0.0.0.26`로 설치합니다. **기준 문장(ref)을 먼저**, 음성 인식 결과(hyp)를 두 번째에 넣습니다.

```bash
nlptutti score ref.txt hyp.txt
nlptutti score ref.txt hyp.txt --rate-mode standard --format json --output score.json
```

기본 출력은 사람이 읽는 한국어 요약입니다. CER·WER는 낮을수록, CRR은 높을수록 원문 표기와 가깝습니다. 기본값은 `normalized`, Unicode 변환 없음, 숫자 사이 점을 제외한 문장부호 제거입니다. 점수에 이름·금액 사전을 사용하지 않습니다.

점을 판별할 때는 선택한 Unicode 정규화만 먼저 적용합니다. `1.5.`는 `1.5`가 되지만 `1..5`의 두 점과 `1 . 5`의 점은 모두 지웁니다. `1.2.3`은 두 점 모두 숫자 사이에 있어 남습니다. 숫자 파서가 아니라 문자 규칙입니다. CER·CRR은 기존처럼 ASCII 공백·탭·줄바꿈 등을 제거하며 줄바꿈 없는 공백(NBSP)까지 일괄 삭제하지 않습니다. WER는 Python의 `str.split()`으로 어절을 나눕니다.

## TXT, CSV, JSONL

UTF-8(BOM 허용)로 저장하세요. 확장자가 같은 두 파일의 형식을 읽으며, 확장자가 없으면 `--input-format text|csv|jsonl` 중 하나를 지정합니다.

- **TXT:** 한 줄에 한 발화, 같은 줄 번호끼리 평가합니다. 줄의 앞뒤 공백을 자르지 않습니다. 전사가 없는 발화는 **빈 줄**로 남깁니다. `\n` 하나는 빈 발화 1개이고, 0바이트는 발화 0개입니다. 마지막 개행은 새 발화를 만들지 않습니다.
- **CSV:** 헤더는 `id,text` 두 열만 사용합니다. ID가 같으면 행 순서는 달라도 됩니다. 쉼표가 있는 본문은 큰따옴표로 감싸세요. 빈 가설의 예는 `u01,`입니다.
- **JSONL:** 한 줄에 `{"id":"u01","text":"부산 바다"}` 형태의 객체 하나를 씁니다. 빈 가설은 `"text":""`입니다. 일반 JSON 문서나 공급자 응답 형식으로 추측하지 않습니다.

두 구조화 형식 모두 유일한 문자열 ID와 문자열 본문만 받습니다. 알 수 없는 열/키, 빠진 값, 빈 ID, 추가·누락·중복 ID, 레코드 안의 줄바꿈은 오류입니다. ID는 문자열 그대로 비교하며, 문장별 결과는 ID 순으로 정렬합니다.

```bash
nlptutti score ref.csv hyp.csv --include-items
nlptutti score ref.jsonl hyp.jsonl --diagnostic-profile korean-v1 --output score.json
```

## 옵션과 결과 읽기

| 선택 | 효과 |
| --- | --- |
| `--format json` | 기계 판독용 JSON. 생략해도 `--output` 경로가 `.json`이면 JSON으로 저장합니다. |
| `--rate-mode standard` | 분모로 기준 길이를 사용합니다. 기본 `normalized`는 삽입 수도 분모에 더합니다. |
| `--keep-punctuation` | 마침표·쉼표 등을 모두 남깁니다. |
| `--unicode-normalization NFC` | 명시한 정규화를 양쪽에 적용합니다. NFD, NFKC, NFKD도 선택할 수 있습니다. |
| `--include-items` | 발화별 ID(TXT는 1부터 시작하는 줄 번호)와 CER/WER/CRR을 추가합니다. |
| `--diagnostic-profile korean-v1` | [한국어 진단](korean-diagnostics.md)을 추가합니다. 진단을 켜도 전체 점수는 같습니다. |

`nlptutti.score/1.0` JSON에는 `corpus` 아래 `utterances`, 전처리 설정, `cer`, `wer`, `crr`와 문자·어절 기준 문장 오류율이 있습니다. 점수 단위는 비율입니다. `micro`는 전체 편집 횟수로 계산하고, `macro`는 발화별 점수의 평균입니다. CRR은 `round(1 - CER, 2)`이며 macro는 발화별로 반올림한 뒤 평균을 냅니다. 빈 참조에 대해서도 삽입을 세므로 standard에서 오류율이 1보다 크거나 CRR이 음수일 수 있습니다.

기본 출력에는 원문이나 발화 ID가 없습니다. JSON에는 입력 형식, 평가기, 정렬된 입력의 SHA-256이 기록되며, 이는 익명화를 보장하지 않습니다. 상세 옵션을 켜면 `items`에 실제 ID가, `diagnostics`에 오류 문자 조각이 남을 수 있습니다.

성공 시 종료 코드는 `0`입니다. 서로 다른 발화 수, 인코딩 오류, 잘못된 파일/옵션은 `2`이며 기존 출력 파일을 교체하지 않습니다. 한 시스템의 점수이므로 모델 간 우열, bootstrap, 품질 gate 결과는 만들지 않습니다. 두 시스템 이상을 비교할 때만 [`compare`](comparison.md)를 사용하세요.
