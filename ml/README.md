# ML 파이프라인 — 예술의전당 공연 정보 추출

크롤링된 공연 detail_text(반정형 한·영 혼재 텍스트)에서 작곡가/곡 정보를 추출·정규화해 웹 앱이 사용할 JSON으로 만든다.

## 결과 (2026년 5월 기준)

| 항목 | 값 |
|---|---|
| 입력 공연 수 | 108 (detail 있는 것) |
| 추출 곡 수 | 562 |
| Unique 작곡가 (raw) | 269 |
| Unique 작곡가 (정규화 후) | **186** |
| 최종 JSON 크기 | 67 KB (concerts) + 7 KB (composers) |

TOP 5 작곡가: Beethoven 36, Mozart 31, Brahms 25, Schumann 23, Bach 22.

## 모델·비용

- 모델: `google/gemini-2.5-flash` (OpenRouter), `temperature=0`
- 추출 1공연당 ~2초 → 108공연 ~4분
- 정규화는 청크(80명)로 LLM 호출, ~10초
- 한 달치 풀 컨텍스트 LLM 호출(58 KB JSON): 약 18k 토큰, **호출당 7~8원** (Gemini Flash)

## 파이프라인

```
sac_2026_05.csv
   │
   ├─ extract_full_may.py        ← 공연별 곡 추출 (LLM)
   │   └─ data/작곡가_곡_5월_전체_v2.csv
   │
   ├─ normalize_full.py          ← 작곡가 canonical 매핑 (LLM)
   │   ├─ data/작곡가_곡_5월_전체_정규화.csv
   │   └─ data/composer_mapping_full.json
   │
   ├─ postprocess_to_array.py    ← 공동작곡 split, 편곡표기 title로 이동
   │   └─ data/작곡가_곡_5월_최종.csv
   │
   ├─ renormalize_after_split.py ← split로 새로 생긴 이름들 다시 매핑 (LLM)
   │   └─ (위 두 파일 덮어씀)
   │
   └─ build_web_data.py          ← 최종 웹용 JSON 생성
       ├─ data/concerts.json
       └─ data/composers.json
```

`extract_full_may.py`만 LLM 추출이 비싸고(108회 호출), 나머지는 빠름.

## 핵심 의사결정 기록

### 1. Canonical은 영어 풀네임으로
- 한국어는 표기 변형이 많음 ("차이콥스키" / "차이코프스키" / "차이코프스키")
- 영어 풀네임은 IMSLP/Wikipedia 표준 → 외부 연동 쉬움
- 한국어/약어 → 영어 매핑은 dict로 양방향 검색 가능

### 2. 작곡가는 배열, 편곡자는 곡명에 보존
- 공동작곡 (`Hans Zimmer & John Powell`) 처리 위해 composers는 배열
- 편곡자는 별도 컬럼 만들지 않고 `title` 끝에 `(Arr. Liszt)`로 보존
  - 이유: 편곡자로 검색하는 일은 거의 없음. 같은 원곡의 다른 편곡판 구분만 가능하면 충분

### 3. 곡명 한·영 병기는 영어 우선 단일화
- 원문은 보통 `Wasserklavier (1965) / 물의 클라비어` 같이 병기
- 영어 원제를 canonical title로 사용. 한국어 부제는 정보 손실로 처리
- 곡 수 dedup 위해 필수

### 4. 추출 단계에서 일반 지식으로 보충 금지
- "원문에 없는 정보(연도, 별칭 등)는 추가하지 말 것" 룰 명시
- 검증 결과 환각 0건. 모든 (1839), (Arr. X) 등은 원문에 있는 것

## 프롬프트 설계 (핵심 룰)

`extract_full_may.py`의 `PROMPT_TEMPLATE` 참조.

요약:
1. composers는 배열, 원작자만
2. 편곡자(`-`, `Arr.`, `transcribed by`)는 title 끝에 `(Arr. X)`로 보존
3. 곡 제목은 한 가지 언어만 (영어 원제 우선)
4. 연도/부제/별칭은 원문에 있으면 곡명에 포함
5. 응답 전 곡 수 자기검증
6. 일반 지식 금지

few-shot 예시 4개로 위 룰을 구체화 (단일/편곡/공동작곡/부제 보존).

## 개선/검수 포인트

| 항목 | 현재 상태 | 후속 |
|---|---|---|
| 공동작곡 split | 자동 (`&`, `,`, `/`) | OK |
| 편곡 표기 분리 | 자동 (`A - B` → `(Arr. B)`) | OK |
| "슈트라우스" 동명이인 | Richard Strauss로 매핑됨 | 원문 검증 필요 (왈츠 왕인지 확인) |
| "이자이" 등 한국어 잔류 | 일부 매핑 누락 | 재실행 또는 사전 추가 |
| nan/빈 셀 9건 | 정상 데이터 | 무시 가능 |

## 향후 (6월·7월 데이터)

```bash
# 1. 새 데이터로 sac_2026_06.csv 받기
# 2. extract_full_may.py 안의 파일명만 바꿔서 실행 (혹은 인자화)
python extract_full_may.py
python normalize_full.py
python postprocess_to_array.py
python renormalize_after_split.py
python build_web_data.py
```

`composer_mapping_full.json`에 누적되는 매핑은 다음 달에 재사용 → 신규 작곡가만 LLM 호출 (캐시 효과). 추가 비용 거의 없음.

## 회귀 테스트

```bash
python regression_test_v3.py
```

수동 라벨링한 5개 공연(24곡)에 대해 곡 수 100% 일치 확인. 프롬프트 변경 시 회귀 검증용.
