"""
6개 공연에 대해 수동 라벨링 vs Gemini Flash 라벨링 품질 비교.

manual_extraction.py에서 다룬 공연들과 동일한 행에 대해서만 Gemini Flash
모델을 호출하고, 결과를 두 CSV로 저장한 뒤 간단한 비교 통계를 출력한다.
"""

import json
import os
import sys
from pathlib import Path
from time import sleep

import pandas as pd
import requests

DATA = Path(__file__).parent / "data"


TARGET_CONCERTS = [
    "KT와 함께하는 예술의전당 마음을 담은 클래식(5월)",
    "트리오 크레도 제2회 정기연주회",
    "공원영 피아노 독주회",
    "클라라 주미 강 & 김선욱 듀오 리사이틀",
    "앙상블 뮤비스의 예술로의 초대 I",
]

PROMPT_TEMPLATE = """다음은 클래식 음악 공연의 프로그램 정보입니다.
이 텍스트에서 **작곡가 이름**과 **곡 제목**을 추출해주세요.

공연 정보:
{detail}

다음 JSON 형식으로 응답해주세요:
{{
  "pieces": [
    {{"composer": "작곡가 이름", "title": "곡 제목"}}
  ]
}}

규칙:
1. 작곡가는 풀네임 또는 성만 (예: "베토벤", "Ludwig van Beethoven", "쇼팽")
2. 곡 제목은 가능한 한 완전하게 (번호, 조성, 작품번호 포함)
3. 영화음악의 경우 작곡가 이름 추출 (영화 제목 X)
4. 프로그램 섹션의 곡만 추출 (연주자 소개 부분 제외)
5. **곡 제목은 원문에 있는 그대로 한 가지 언어로만 출력한다.**
   - 한국어/영어가 병기된 경우 **영어 원제를 우선**한다.
   - 같은 곡을 두 row로 나누지 말 것 (위반시 곡 수가 2배가 되어 실패).
6. **작품 연도, 부제, 별칭이 원문에 있으면 곡명에 그대로 포함한다.**
   예: "Wasserklavier (1965)", "Prelude Op. 28, No. 15 - 빗방울 전주곡"
7. 응답 전에 추출한 곡 수가 원문 프로그램의 곡 수와 일치하는지 확인하고,
   중복이나 누락이 있으면 다시 추출한다.

예시:
입력 텍스트 일부:
  L. Berio: Wasserklavier (1965) / 루치아노 베리오: 물의 클라비어
출력:
  {{"composer": "Luciano Berio", "title": "Wasserklavier (1965)"}}
  (한국어 병기는 같은 곡이므로 별도 row 만들지 않음)

JSON만 출력하고 다른 설명은 하지 마세요."""


def call_gemini_flash(api_key: str, detail: str) -> list[dict]:
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
    sub = df[df["PROGRAM_SUBJECT"].isin(TARGET_CONCERTS)].copy()
    print(f"매칭된 공연 수: {len(sub)} (목표 {len(TARGET_CONCERTS)})")
    for name in TARGET_CONCERTS:
        hit = (sub["PROGRAM_SUBJECT"] == name).sum()
        print(f"  - {name}: {hit}건")

    rows = []
    for _, row in sub.iterrows():
        detail = row["detail_text"]
        if pd.isna(detail):
            print(f"[skip] detail 없음: {row['PROGRAM_SUBJECT']}")
            continue
        concert = row["PROGRAM_SUBJECT"]
        date = row["BEGIN_DATE"]
        print(f"\n>> {concert} ({date})")
        try:
            pieces = call_gemini_flash(api_key, detail)
        except Exception as e:
            print(f"  [error] {e}")
            continue
        for p in pieces:
            rows.append(
                {
                    "공연명": concert,
                    "날짜": date,
                    "작곡가": p.get("composer", ""),
                    "곡명": p.get("title", ""),
                }
            )
            print(f"  - {p.get('composer')}: {str(p.get('title'))[:60]}")
        sleep(1)

    out = pd.DataFrame(rows)
    out.to_csv(DATA / "작곡가_곡_gemini_flash_v2_샘플.csv", index=False, encoding="utf-8-sig")
    print(f"\n저장 완료: data/작곡가_곡_gemini_flash_v2_샘플.csv ({len(out)}행)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
