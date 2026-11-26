# Nlptutti: 한국어 STT 오류율

기준 문장과 음성 인식 결과를 넣으면 **문자 오류율(CER), 어절 오류율(WER), 문자 인식률(CRR)**을 계산합니다. 음성 파일이나 STT 모델은 필요하지 않습니다.

[![MIT 라이선스](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)](https://github.com/hyeonsangjeon/computing-Korean-STT-error-rates/blob/main/LICENSE)
[![PyPI 버전](https://badge.fury.io/py/nlptutti.svg)](https://pypi.org/project/nlptutti/)
[![테스트 상태](https://github.com/hyeonsangjeon/computing-Korean-STT-error-rates/actions/workflows/test.yml/badge.svg)](https://github.com/hyeonsangjeon/computing-Korean-STT-error-rates/actions/workflows/test.yml)

**[브라우저에서 바로 계산하기](https://hyeonsangjeon.github.io/job-transcribe/nlptutti/#calculator)** · [오프라인 계산기 다운로드](https://github.com/hyeonsangjeon/computing-Korean-STT-error-rates/releases/download/0.0.0.25/nlptutti-calculator.html)

**띄어쓰기** 예제를 누르면 `부산 바다 → 부산바다`가 왜 CER 0%인지 보입니다. 내 문장도 브라우저 안에서 바로 채점합니다. 인터넷 연결 없이 쓰려면 내려받은 HTML 파일을 브라우저로 여세요.

| 기준 → 음성 인식 결과 | CER | WER | CRR |
| --- | ---: | ---: | ---: |
| 오늘 날씨**가** 맑습니다 → 오늘 날씨**는** 맑습니다 | 11.11% | 33.33% | 89% |
| 부산 바다 → 부산바다 | 0% | 100% | 100% |
| 3.5만 원 → 35만 원 | 20% | 50% | 80% |

CER는 띄어쓰기를 세지 않지만 바뀐 조사는 글자 하나의 치환으로 셉니다. 마지막 예제에서는 소수점 하나가 빠졌습니다. 이 수치는 표기 차이를 나타내며 금액의 의미나 모델의 성능을 판정하지 않습니다. 분모를 바꿨을 때 점수가 어떻게 달라지는지는 [계산식](#계산식)에서 볼 수 있습니다.

## 빠른 시작: 파일 두 개 평가하기

`score`는 0.0.0.25부터 쓸 수 있습니다. 기준 문장과 인식 결과를 각각 UTF-8 파일로 저장하고 **같은 발화를 같은 줄**에 두세요. 인식 결과가 없는 줄도 지우지 않습니다.

```bash
python -m pip install nlptutti==0.0.0.25
nlptutti score ref.txt hyp.txt
```

저장소에 들어 있는 예제로 확인하려면 저장소 폴더에서 실행하세요.

```bash
python -m pip install .
nlptutti score examples/score-ref.txt examples/score-hyp.txt
```

위 세 발화의 전체(`micro`) 결과는 **CER 0.111111, WER 0.571429, CRR 0.890000**입니다. CLI의 단위는 비율(`1 = 100%`)입니다. `micro`는 편집 횟수를 합친 결과이고, `macro`는 발화별 점수의 단순 평균입니다.

JSON 저장, ID로 정렬하는 CSV·JSONL, 입력 오류는 [단일 평가 사용법](https://github.com/hyeonsangjeon/computing-Korean-STT-error-rates/blob/0.0.0.25/docs/score.md)을 참고하세요.

### Python에서 평가하기

```python
import nlptutti as metrics

result = metrics.get_cer(
    "오늘 날씨가 맑습니다",
    "오늘 날씨는 맑습니다",
    rate_mode="standard",
)

print(round(result["cer"], 4))       # 0.1111
print(result["substitutions"])       # 1
```

CER와 WER는 낮을수록 좋고 완전 일치는 `0.0`입니다. CRR은 높을수록 좋고
완전 일치는 `1.0`입니다.

## 계산식

두 방식 모두 기준 문장을 인식 결과로 바꾸는 데 필요한 최소 편집 횟수를 셉니다. `S`는 치환, `D`는 삭제, `I`는 삽입, `C`는 일치 횟수입니다. 기준 길이 `N = C + S + D`에는 삽입이 들어가지 않습니다.

**기본 방식 (`rate_mode="normalized"`)**에서는 오류 횟수를 **기준 길이와 삽입 수의 합**으로 나눕니다. CER는 글자 단위로, WER는 공백으로 나눈 어절 단위로 같은 식을 씁니다.

```math
\Large \mathrm{ER}_{\mathrm{normalized}} = \dfrac{S+D+I}{N+I}
```

**표준 방식 (`rate_mode="standard"`)**에서는 오류 횟수를 **기준 길이**로만 나눕니다. 아래첨자 `c`는 글자, `w`는 어절을 뜻합니다.

```math
\Large \mathrm{CER} = \dfrac{S_c+D_c+I_c}{N_c}
```

```math
\Large \mathrm{WER} = \dfrac{S_w+D_w+I_w}{N_w}
```

예를 들어 `가나 → 가나다`는 기준 두 글자에 `다` 하나를 삽입한 경우입니다. 기본 CER는 **1/3(33.33%)**, 표준 CER는 **1/2(50%)**입니다. CRR은 선택한 방식의 CER로 `round(1 - CER, 2)`를 계산합니다. 기준이 비어 있으면 표준 오류율은 삽입 수이고, 양쪽이 모두 비면 오류율은 0입니다.

오류 위치를 보여주는 `explain_errors()`와 개체명 평가는 같은 Levenshtein 정렬 커널을 사용합니다. 최소 편집 경로가 여러 개여도 정해진 순서로 하나를 고릅니다.

### 기본값부터 확인하기

| 옵션 | 기본값 | 의미 |
| --- | --- | --- |
| `rate_mode` | `"normalized"` | 분모를 고르는 옵션이지 입력 문자열을 바꾸는 옵션이 아닙니다. 표준 오류율이 필요하면 `"standard"`를 지정합니다. 삽입이 많으면 표준 오류율은 1을 넘을 수 있습니다. |
| `rm_punctuation` | `True` | Unicode 문장부호를 제거하되 양옆이 십진 숫자인 ASCII `.`은 보존합니다. 공백을 제거하기 **전**에 판단하므로 `1 . 5`의 점은 지웁니다. |
| `unicode_normalization` | `None` | Unicode 표현을 그대로 둡니다. 조합형 혼입을 정리할 때만 `"NFC"` 등을 지정합니다. |

비교 API에서 선택한 Unicode 정규화는 키워드·개체명 사전과 조사·어미에도
적용합니다. 단독 `evaluate_keywords`에서도 같은 옵션을 선택할 수 있습니다.
키워드 매칭은 구두점을 제거하지 않으므로 `C++`와 `C`를 다르게 봅니다.

예전 `3.5만 원 / 35만 원`이나 `수수료 1.5% / 수수료 15%`의 CER/WER 0을 재현하려면 **별도 환경에 `python -m pip install nlptutti==0.0.0.24`**를 설치하고 당시 분모와 전처리 설정을 사용하세요. `--keep-punctuation`은 과거값 재현 옵션이 아니라 모든 문장부호를 **남기는** 옵션입니다. 새 기준과 예전 기준으로 계산한 점수를 같은 열에서 비교하지 마세요.

## 선택: 두 STT 시스템 비교

<details>
<summary>서로 다른 시스템의 결과가 둘 이상일 때만 펼치세요.</summary>

```python
import nlptutti as metrics

report = metrics.compare_systems(
    ["오늘 날씨가 맑습니다", "서울은 따뜻합니다"],
    {
        "baseline": ["오늘 날씨는 맑습니다", "서울은 춥습니다"],
        "candidate": ["오늘 날씨가 맑습니다", "서울은 따뜻합니다"],
    },
    rate_mode="standard",
)

for system in report["systems"]:
    print(
        system["id"],
        round(system["metrics"]["cer"]["micro"], 4),
        round(system["metrics"]["wer"]["micro"], 4),
    )

# baseline 0.2353 0.4
# candidate 0.0 0.0
```

`micro`는 코퍼스 전체의 편집 횟수를 합산한 점수이고, `macro`는 문장별 점수의
단순 평균입니다. 논문이나 모델 벤치마크에서는 보통 `rate_mode="standard"`와
`micro`를 먼저 봅니다.

### 비교 결과를 JSON과 Markdown으로 저장

저장소의 [`examples/comparison_input.json`](https://github.com/hyeonsangjeon/computing-Korean-STT-error-rates/blob/main/examples/comparison_input.json)은
바로 위 Python 예제와 같은 입력입니다.
0.0.0.24부터 설치본에 같은 예제가 들어 있습니다. 설치 후에는 모델이나
GitHub 파일을 내려받지 않고 다음 두 명령만 실행하면 됩니다.

```bash
nlptutti sample --output comparison_input.json
nlptutti compare comparison_input.json \
  --rate-mode standard \
  --output-dir comparison-report
```

성공하면 다음 두 파일이 생성됩니다.

```text
comparison-report/report.json
comparison-report/report.md
```

`report.json`은 자동화에서 읽는 버전 스키마이고, `report.md`는 사람이 검토할
표입니다. 입력, 옵션, 패키지 버전이 같으면 실행할 때마다 같은 내용을 만듭니다.
문장 전체를 담는 `raw_inputs`는 `include_transcripts=True` 또는
`--include-transcripts`를 선택할 때만 추가됩니다. 다만 기존 상세 모드에는
키워드·개체명 이름, 개체명 오류 구간, 진단 토큰이 남을 수 있습니다.

**0.0.0.23부터 외부 공유용 보고서는 `privacy_mode="aggregate"` 또는
`--privacy-mode aggregate`를 지정하세요.** 사전·라벨·오류 텍스트를 제외하고
시스템 이름도 `system-1`, `system-2`로 바꿉니다. 점수는 그대로이며 원문 포함
옵션과 함께 쓸 수 없습니다. 기존 코드 호환을 위해 기본값은 `"detailed"`로
유지합니다. 해시와 집계값만 남겨도 익명성이 보장되는 것은 아닙니다.

입력 형식, 오류 처리, paired bootstrap과 결과 해석은
[시스템 비교 매뉴얼](https://github.com/hyeonsangjeon/computing-Korean-STT-error-rates/blob/main/docs/comparison.md)에 정리했습니다.

</details>

## 어떤 함수를 선택할까

`evaluate_corpus`의 기존 문장 오류율은 공백을 제거한 **문자 기준**입니다.
0.0.0.24부터 띄어쓰기까지 구분하는 `word_sentence_error_rate`도 반환합니다.
[문자·어절 기준 예제와 보고서 검증](https://github.com/hyeonsangjeon/computing-Korean-STT-error-rates/blob/main/docs/corpus-and-validation.md)을 참고하세요.

| 목적 | API | 성공 기준과 경계 |
| --- | --- | --- |
| 문자 전사 품질 | `get_cer` | 낮을수록 좋습니다. 공백을 항상 제거하므로 띄어쓰기 자체는 평가하지 않습니다. |
| 단어·띄어쓰기 포함 품질 | `get_wer` | 낮을수록 좋습니다. 시스템 간 토큰화 정책을 같게 맞춰야 합니다. |
| 높을수록 좋은 문자 지표 | `get_crr` | `round(1 - CER, 2)`인 보조 지표입니다. 독립 정렬 점수가 아닙니다. |
| 여러 문장 micro/macro | `evaluate_corpus` | 같은 길이의 reference와 hypothesis 목록이 필요합니다. |
| 둘 이상의 시스템 비교 | `compare_systems` | 정렬된 입력, 시스템별 점수, pairwise delta를 반환합니다. |
| 핵심어 누락·오탐 | `evaluate_keywords` | 제공한 키워드 사전의 precision, recall, F1을 계산합니다. |
| 개체명 구간 품질 | `evaluate_entities` | 제공한 개체명 사전의 Entity CER와 언급 F1을 계산합니다. NER 모델은 아닙니다. |
| 오류 원인 확인 | `explain_errors` | 문자 또는 단어 정렬과 상위 치환·삭제·삽입을 반환합니다. |
| JSON·SRT·TSV 평가 | `parse_transcript` + `evaluate_transcript` | 필드와 시간 단위를 검증하고 평가 provenance를 남깁니다. |

## 선택 기능

### Paired bootstrap 신뢰구간

문장 쌍을 유지한 채 percentile bootstrap을 실행하면 pairwise CER/WER delta의
신뢰구간도 보고서에 남습니다. 기본값 `bootstrap=0`에서는 실행하지 않습니다.

```python
report = metrics.compare_systems(
    references,
    systems,
    rate_mode="standard",
    bootstrap=1000,
    seed=42,
    confidence=0.95,
)
```

### 한국어 오류 진단

`diagnostic_profile="korean-v1"`을 지정하면 띄어쓰기 경계, 숫자·단위,
조사·어미 인접 치환, 상위 문자 편집을 따로 보여 줍니다. 전체 CER/WER에는
영향을 주지 않으며 기본값은 `None`입니다. 숫자·단위와 조사·어미 규칙은
형태소 분석이 아닌 experimental 단계의 휴리스틱입니다.

자세한 규칙과 오분류 가능성은 [한국어 오류 진단 프로필](https://github.com/hyeonsangjeon/computing-Korean-STT-error-rates/blob/main/docs/korean-diagnostics.md)에
정리했습니다.

### STT 도구별 JSON 읽기

`parse_provider_transcript()`는 네트워크나 SDK를 사용하지 않고 저장된 JSON만
읽습니다. 현재 테스트로 확인한 형식은 다음 두 가지입니다.

- Microsoft Azure Speech short-audio REST `simple` 성공 응답
- 오픈소스 `openai/whisper`의 `transcribe()` 반환 구조

공급자와 schema version은 반드시 직접 지정해야 하며 자동으로 감지하지
않습니다. Azure의 다른 REST 형식, OpenAI API, AWS, Google, FunASR 전용 형식은
현재 지원 범위에 포함되지 않습니다. 일반 text/JSON/SRT/TSV는 특정 공급자에
종속되지 않는 `parse_transcript()`로 평가할 수 있습니다.

지원 필드와 공식 출처는 [공급자 출력 어댑터](https://github.com/hyeonsangjeon/computing-Korean-STT-error-rates/blob/main/docs/provider-adapters.md)에
정리했습니다.

## 문서

[한국어 사용자 매뉴얼](https://hyeonsangjeon.github.io/job-transcribe/nlptutti/) · [Python 3.8–3.14 테스트](https://github.com/hyeonsangjeon/computing-Korean-STT-error-rates/actions/workflows/test.yml) · [패키지 다운로드 통계](https://pepy.tech/project/nlptutti)

### 다음 평가로 이어가기 (0.0.0.24부터)

- [저장된 STT 파일 비교](https://github.com/hyeonsangjeon/computing-Korean-STT-error-rates/blob/main/docs/file-comparison.md): text·JSON·SRT·TSV와 명시적 Azure/Whisper 응답을 파일 목록으로 연결합니다.
- [문장·조건별 변화 확인](https://github.com/hyeonsangjeon/computing-Korean-STT-error-rates/blob/main/docs/item-comparison.md): 숫자·띄어쓰기·이름 예제로 상위 악화 문장과 사용자 라벨별 점수를 읽습니다.
- [CI 품질 기준 검사](https://github.com/hyeonsangjeon/computing-Korean-STT-error-rates/blob/main/docs/quality-gate.md): 지정한 허용치를 넘으면 별도 `gate` 명령이 종료 코드 3을 반환합니다.
- [Bootstrap 해석 범위](https://github.com/hyeonsangjeon/computing-Korean-STT-error-rates/blob/main/docs/bootstrap-interpretation.md): 소표본·같은 화자·폭이 0인 구간을 해석할 때의 제한입니다.

### API와 참고 자료

- [시스템 비교와 결과 번들](https://github.com/hyeonsangjeon/computing-Korean-STT-error-rates/blob/main/docs/comparison.md)
- [비교 JSON schema](https://github.com/hyeonsangjeon/computing-Korean-STT-error-rates/blob/main/docs/comparison-schema.md)
- [구조화 STT 결과](https://github.com/hyeonsangjeon/computing-Korean-STT-error-rates/blob/main/docs/structured-transcripts.md)
- [한국어 오류 진단](https://github.com/hyeonsangjeon/computing-Korean-STT-error-rates/blob/main/docs/korean-diagnostics.md)
- [Azure Speech·Whisper 출력 어댑터](https://github.com/hyeonsangjeon/computing-Korean-STT-error-rates/blob/main/docs/provider-adapters.md)
- [정렬 커널과 성능 기준선](https://github.com/hyeonsangjeon/computing-Korean-STT-error-rates/blob/main/docs/alignment-performance.md)
- [공개 채택 지표 기준선과 30·60·90일 검토](https://github.com/hyeonsangjeon/computing-Korean-STT-error-rates/blob/main/docs/adoption-baseline.md)

이 패키지를 만든 배경과 한국어 ASR/STT 평가 실험은
[한국어 프롤로그](https://hyeonsangjeon.github.io/job-transcribe/)와
[영문 글](https://hyeonsangjeon.github.io/job-transcribe/en/)에 정리되어
있습니다.

## 관련 논문과 공개 구현

- Galibert et al., [Generating Task-Pertinent sorted Error Lists for Speech Recognition](https://aclanthology.org/L16-1297/), LREC 2016.
- Le-Duc et al., [Medical Spoken Named Entity Recognition](https://aclanthology.org/2025.naacl-industry.59/), NAACL 2025.
- Szymański et al., [Why Aren't We NER Yet?](https://aclanthology.org/2023.acl-long.98/), ACL 2023.
- Gong et al., [BR-ASR](https://www.isca-archive.org/interspeech_2025/gong25_interspeech.html), Interspeech 2025.
- K et al., [Advocating Character Error Rate for Multilingual ASR Evaluation](https://aclanthology.org/2025.findings-naacl.277/), NAACL 2025 Findings.
- [ContextASR-Bench 평가 코드](https://github.com/MrSupW/ContextASR-Bench/tree/main/evaluation)
- [Teklia `ie-eval`](https://gitlab.teklia.com/ner/metrics/ie-eval)
- [PIER](https://github.com/enesyugan/PIER-CodeSwitching-Evaluation)

`evaluate_entities()`는 위 구현을 포팅한 코드가 아닙니다. 공통 평가 원칙을
한국어 문자 span과 `aliases`로 직접 지정하는 별칭 정책에 맞춰 독립 구현했으며
차이는
[`test_entity_reference_implementations.py`](https://github.com/hyeonsangjeon/computing-Korean-STT-error-rates/blob/main/test/test_entity_reference_implementations.py)에
고정했습니다.

## 라이선스

코드는 [MIT License](https://github.com/hyeonsangjeon/computing-Korean-STT-error-rates/blob/main/LICENSE)로 배포됩니다. 이 저장소는 STT 모델, 가중치,
음성 데이터셋을 포함하지 않으며 외부 모델·데이터의 라이선스는 각각 별도로
확인해야 합니다.
