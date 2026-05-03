"""
postprocess_to_array.py 결과의 composer들을 다시 unique로 모아 LLM 정규화.
split로 새로 생긴 이름들이 canonical로 매핑되도록 보정.
"""

import json
import os
import sys
from pathlib import Path
from time import sleep

import pandas as pd
import requests

DATA = Path(__file__).parent / "data"


def call(api_key: str, names: list[str]) -> dict[str, str]:
    prompt = f"""다음은 클래식 작곡가 이름 목록입니다 (한국어/영어/약어 혼재).
각 이름을 canonical 영어 풀네임으로 매핑해주세요.

규칙:
- canonical 형식: "Ludwig van Beethoven" (Wikipedia/IMSLP 표준)
- diacritics 보존: "Antonín Dvořák", "Frédéric Chopin"
- 같은 사람이면 모두 동일 canonical로
- 동명이인 주의 (Johann Strauss vs Richard Strauss). 맥락이 부족하면 가장 유명한 사람으로.
- 영화음악/현대 작곡가도 가능한 풀네임으로 (예: "H. Zimmer" → "Hans Zimmer", "J. Powell" → "John Powell")
- 도저히 모르는 이름은 입력 그대로 출력

입력:
{json.dumps(names, ensure_ascii=False, indent=2)}

JSON: {{"입력": "canonical", ...}}  (모든 입력 반드시 포함)"""

    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": "google/gemini-2.5-flash",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        },
        timeout=180,
    )
    resp.raise_for_status()
    text = resp.json()["choices"][0]["message"]["content"].strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)


def main() -> int:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return 1

    df = pd.read_csv(DATA / "작곡가_곡_5월_최종.csv")
    exploded = df.assign(작곡가=df["작곡가들"].str.split("; ")).explode("작곡가")
    unique = sorted(exploded["작곡가"].dropna().astype(str).unique().tolist())
    unique = [u for u in unique if u]
    print(f"split 후 unique: {len(unique)}명")

    chunk = 80
    mapping: dict[str, str] = {}
    for i in range(0, len(unique), chunk):
        part = unique[i : i + chunk]
        print(f"[chunk {i//chunk + 1}] {len(part)}명")
        try:
            mapping.update(call(api_key, part))
            print(f"  누적 {len(mapping)}")
        except Exception as e:
            print(f"  [error] {e}")
        sleep(1)

    # 적용
    def remap(s: str) -> str:
        parts = [p.strip() for p in str(s).split(";") if p.strip()]
        return "; ".join(mapping.get(p, p) for p in parts)

    df["작곡가들"] = df["작곡가들"].apply(remap)
    df.to_csv(DATA / "작곡가_곡_5월_최종.csv", index=False, encoding="utf-8-sig")
    with open(DATA / "composer_mapping_full.json", "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

    exploded2 = df.assign(작곡가=df["작곡가들"].str.split("; ")).explode("작곡가")
    exploded2 = exploded2[exploded2["작곡가"].notna() & (exploded2["작곡가"] != "")]
    print(f"\n최종 unique canonical 작곡가: {exploded2['작곡가'].nunique()}명")
    print("\n=== TOP 20 ===")
    for c, n in exploded2["작곡가"].value_counts().head(20).items():
        print(f"  {n:3d}  {c}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
