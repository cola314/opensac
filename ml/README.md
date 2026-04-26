# OpenSAC ML Pipeline

클래식 공연 상세 텍스트에서 프로그램 정보(작곡가/곡명)를 자동 추출하는 DSPy 파이프라인.

## 구조

```
ml/
├── parser/          # DSPy 모듈 + 추론 파이프라인
│   ├── signatures.py    # ProgramExtractor 시그니처 (input/output 스키마)
│   ├── modules.py       # ConcertProgramParser (ChainOfThought 래퍼)
│   └── pipeline.py      # 추론 실행 CLI
├── optimize/        # DSPy 컴파일러 + 탐색
│   ├── compile.py           # BootstrapFewShot / MIPROv2 컴파일
│   ├── search.py            # 예산 제한 자동 탐색 (AutoML-like)
│   └── compiled_program.json  # 현재 best config (F1=0.952)
├── eval/            # 평가
│   ├── metrics.py       # program F1 v1/v2 (catalog-aware matching)
│   └── evaluate.py      # 평가 CLI + 런 추적
├── label/           # 라벨링 도구
│   ├── generate.py      # LLM 기반 초기 라벨 생성
│   ├── merge.py         # 라벨 파일 병합
│   └── validate.py      # 라벨 품질 검증
├── data/            # 데이터셋 + 런 로그 (gitignore)
└── pyproject.toml   # Python 의존성 (dspy, optuna)
```

## 설정

```bash
cd ml
cp .env.example .env  # OPENROUTER_API_KEY 설정
uv sync
```

## 사용법

### 추론 (공연 프로그램 추출)

```bash
# compiled program으로 추론
uv run python parser/pipeline.py \
  --input data/dataset.dev20.json \
  --output data/results.json \
  --compiled-program optimize/compiled_program.json

# 비용만 추정
uv run python parser/pipeline.py --input data/dataset.json --estimate-only
```

### 평가

```bash
# 평가 (metric v2, catalog-aware)
uv run python eval/evaluate.py \
  --predictions data/results.json \
  --gold data/dataset.dev20.json \
  --metric-version v2

# 런 추적 + 트렌드 보기
uv run python eval/evaluate.py --report-trend
```

### 컴파일 (프롬프트 최적화)

```bash
# BootstrapFewShot
uv run python optimize/compile.py \
  --trainset data/dataset.train30.json \
  --optimizer bootstrap \
  --metric-version v2

# MIPROv2 (optuna 필요)
uv run python optimize/compile.py \
  --trainset data/dataset.train30.json \
  --optimizer mipro \
  --metric-version v2 \
  --auto medium
```

### 예산 제한 탐색

```bash
# dry-run으로 계획 확인
uv run python optimize/search.py --dry-run --budget-usd 0.05

# 실행
uv run python optimize/search.py --max-trials 3 --budget-usd 0.10
```

## 현재 성능 (dev20 기준, metric v2)

| config | F1 | P | R |
|---|---|---|---|
| **best (mipro b=1 l=2 auto=medium)** | **0.952** | 0.976 | 0.944 |
| baseline (no compile) | 0.865 | 0.872 | 0.864 |

## 모델

- LLM: `gemini-2.5-flash` (OpenRouter 경유)
- 월 운영 비용: 50건 기준 ~$0.02

## 파이프라인 구조

```
[detail_text] → ChainOfThought(ProgramExtractor) → [programs: [{composer, piece}]]
```

MIPROv2가 최적화한 instruction + 자동 선택된 few-shot 2개 + CoT 조합.
`compiled_program.json`에 최적화된 프롬프트/데모가 저장되어 있음.
