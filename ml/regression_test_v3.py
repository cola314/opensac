"""
v3 프롬프트 (few-shot 보강 + composers 배열 스키마) 회귀 테스트.
5개 공연만 돌려서 출력 형식·곡 수가 정상인지 확인.
"""

import json
import os
import sys
from pathlib import Path
from time import sleep

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_full_may import PROMPT_TEMPLATE, call_gemini

DATA = Path(__file__).parent / "data"


TARGET = [
    "KT와 함께하는 예술의전당 마음을 담은 클래식(5월)",
    "트리오 크레도 제2회 정기연주회",
    "공원영 피아노 독주회",
    "클라라 주미 강 & 김선욱 듀오 리사이틀",
    "앙상블 뮤비스의 예술로의 초대 I",
]

EXPECTED_COUNTS = {
    "KT와 함께하는 예술의전당 마음을 담은 클래식(5월)": 4,
    "트리오 크레도 제2회 정기연주회": 2,
    "공원영 피아노 독주회": 11,
    "클라라 주미 강 & 김선욱 듀오 리사이틀": 4,
    "앙상블 뮤비스의 예술로의 초대 I": 3,
}


def main() -> int:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return 1

    df = pd.read_csv(DATA / "sac_2026_05.csv")
    sub = df[df["PROGRAM_SUBJECT"].isin(TARGET)]

    results = {}
    rows = []
    for _, r in sub.iterrows():
        concert = r["PROGRAM_SUBJECT"]
        print(f"\n>> {concert}")
        try:
            pieces = call_gemini(api_key, r["detail_text"])
        except Exception as e:
            print(f"  [error] {e}")
            continue
        results[concert] = len(pieces)
        for p in pieces:
            comps = p.get("composers") or ([p.get("composer", "")] if p.get("composer") else [])
            print(f"  - {comps} | {str(p.get('title', ''))[:70]}")
            rows.append({
                "공연명": concert,
                "작곡가들": "; ".join(comps) if isinstance(comps, list) else str(comps),
                "곡명": p.get("title", ""),
            })
        sleep(1)

    print("\n=== 곡 수 검증 ===")
    ok = True
    for concert, expected in EXPECTED_COUNTS.items():
        actual = results.get(concert, 0)
        mark = "OK" if actual == expected else "FAIL"
        if actual != expected:
            ok = False
        print(f"  [{mark}] {concert}: 기대 {expected}, 실제 {actual}")

    print("\n총평:", "PASS" if ok else "FAIL")
    pd.DataFrame(rows).to_csv(DATA / "regression_v3_샘플.csv", index=False, encoding="utf-8-sig")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
