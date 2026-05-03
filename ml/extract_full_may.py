"""
2026년 5월 예술의전당 음악당 전체 공연(108개)에 대해 Gemini Flash v2 프롬프트로
작곡가/곡 정보 추출. 결과는 CSV로 저장.
"""

import json
import os
import sys
from pathlib import Path
from time import sleep

import pandas as pd
import requests

DATA = Path(__file__).parent / "data"


PROMPT_TEMPLATE = """다음은 클래식 음악 공연의 프로그램 정보입니다.
이 텍스트에서 **작곡가 이름**과 **곡 제목**을 추출해주세요.

공연 정보:
{detail}

다음 JSON 형식으로 응답해주세요:
{{
  "pieces": [
    {{"composers": ["작곡가1", "작곡가2"], "title": "곡 제목"}}
  ]
}}

규칙:
1. **composers는 배열**. 원작자만 포함한다.
   - 단일 작곡가: ["베토벤"]
   - 공동작곡 (`A & B`, `A, B`, `A/B`): ["A", "B"] 식으로 모두 배열에 포함
   - 영화음악 등 여러 작곡가 합작도 모두 배열에 포함
2. **편곡자(`-`, `Arr.`, `transcribed by` 등)는 composers에 넣지 말고 title 끝에 보존한다.**
   - 원문 `J. S. Bach - F. Liszt: Sonata BWV 1003`
     → composers: ["J. S. Bach"], title: "Sonata BWV 1003 (Arr. F. Liszt)"
   - 원문에 이미 `(Arr. Liszt)` 같은 표기가 있으면 그대로 유지
3. 작곡가는 풀네임 또는 성만 (예: "베토벤", "Ludwig van Beethoven", "쇼팽")
4. 곡 제목은 가능한 한 완전하게 (번호, 조성, 작품번호 포함)
5. 영화음악의 경우 작곡가 이름 추출 (영화 제목 X)
6. 프로그램 섹션의 곡만 추출 (연주자 소개 부분 제외)
7. **곡 제목은 원문에 있는 그대로 한 가지 언어로만 출력한다.**
   - 한국어/영어가 병기된 경우 **영어 원제를 우선**한다.
   - 같은 곡을 두 row로 나누지 말 것.
8. **작품 연도, 부제, 별칭이 원문에 있으면 곡명에 그대로 포함한다.**
9. 응답 전에 추출한 곡 수가 원문 프로그램의 곡 수와 일치하는지 확인하고,
   중복이나 누락이 있으면 다시 추출한다.
10. **모든 정보(연도, 부제, 별칭, 편곡 표기 등)는 원문에 명시된 것만 사용한다.
    원문에 없는 정보를 일반 지식으로 보충하지 말 것.**

예시:

[예시 1] 단일 작곡가 + 한·영 병기
입력 일부:
  L. Berio :Wasserklavier (1965)
  루치아노 베리오 : 물의 클라비어
출력:
  {{"composers": ["L. Berio"], "title": "Wasserklavier (1965)"}}
  (한국어 병기는 같은 곡이므로 별도 row 만들지 않음)

[예시 2] 편곡 (`-` 또는 `Arr.` 표기)
입력 일부:
  J. S. Bach - F. Liszt :
  Variations on "Weinen, Klagen, Sorgen, Zagen"
출력:
  {{"composers": ["J. S. Bach"], "title": "Variations on \\"Weinen, Klagen, Sorgen, Zagen\\" (Arr. F. Liszt)"}}
  (편곡자는 composers에 넣지 않고 title 끝에 보존)

[예시 3] 공동작곡 (영화음악)
입력 일부:
  H. Zimmer & J. Powell : Kung Fu Panda 'Hero'
출력:
  {{"composers": ["H. Zimmer", "J. Powell"], "title": "Kung Fu Panda 'Hero'"}}

[예시 4] 부제·별칭 보존
입력 일부:
  Tchaikovsky : Piano Trio in A minor, Op. 50 "In Memory of a Great Artist"
출력:
  {{"composers": ["Tchaikovsky"], "title": "Piano Trio in A minor, Op. 50 \\"In Memory of a Great Artist\\""}}

JSON만 출력하고 다른 설명은 하지 마세요."""


def call_gemini(api_key: str, detail: str) -> list[dict]:
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "google/gemini-2.5-flash",
            "messages": [{"role": "user", "content": PROMPT_TEMPLATE.format(detail=detail)}],
            "temperature": 0,
        },
        timeout=120,
    )
    response.raise_for_status()
    text = response.json()["choices"][0]["message"]["content"].strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    parsed = json.loads(text)
    return parsed.get("pieces", [])


def main() -> int:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("OPENROUTER_API_KEY 환경변수를 설정해주세요.")
        return 1

    df = pd.read_csv(DATA / "sac_2026_05.csv")
    df = df[df["detail_text"].notna()].reset_index(drop=True)
    total = len(df)
    print(f"전체 공연 수 (detail 있음): {total}")

    rows = []
    failed = []
    out_csv = DATA / "작곡가_곡_5월_전체_v2.csv"

    for idx, row in df.iterrows():
        concert = row["PROGRAM_SUBJECT"]
        date = row["BEGIN_DATE"]
        print(f"[{idx+1}/{total}] {concert[:50]} ({date})")
        try:
            pieces = call_gemini(api_key, row["detail_text"])
        except Exception as e:
            print(f"  [error] {e}")
            failed.append({"idx": idx, "concert": concert, "error": str(e)})
            continue
        for p in pieces:
            composers = p.get("composers") or ([p["composer"]] if p.get("composer") else [])
            if not isinstance(composers, list):
                composers = [composers]
            rows.append(
                {
                    "공연명": concert,
                    "날짜": date,
                    "작곡가들": "; ".join(str(c) for c in composers),
                    "곡명": p.get("title", ""),
                }
            )
        if (idx + 1) % 20 == 0:
            pd.DataFrame(rows).to_csv(out_csv, index=False, encoding="utf-8-sig")
            print(f"  [중간 저장: {len(rows)}행]")
        sleep(0.7)

    out = pd.DataFrame(rows)
    out.to_csv(out_csv, index=False, encoding="utf-8-sig")
    if failed:
        with open(DATA / "failed_concerts.json", "w", encoding="utf-8") as f:
            json.dump(failed, f, ensure_ascii=False, indent=2)
        print(f"\n실패 {len(failed)}건 → failed_concerts.json")

    print(f"\n총 {len(out)}행, unique 작곡가 raw {out['작곡가'].nunique()}명")
    print(f"저장: {out_csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
