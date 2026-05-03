"""
5월 전체(562행) 작곡가를 canonical 영어 풀네임으로 정규화.
269명을 한 번에 매핑하기 위해 청크로 나눠 호출 후 결과 머지.
"""

import json
import os
import sys
from pathlib import Path
from time import sleep

import pandas as pd
import requests

DATA = Path(__file__).parent / "data"

CHUNK_SIZE = 80


def call(api_key: str, names: list[str]) -> dict[str, str]:
    prompt = f"""다음은 클래식 작곡가 이름 목록입니다 (한국어/영어/약어 혼재).
각 이름을 canonical 영어 풀네임으로 매핑해주세요.

규칙:
- canonical 형식: "Ludwig van Beethoven" (Wikipedia/IMSLP 표준)
- diacritics 보존: "Antonín Dvořák", "Frédéric Chopin"
- 같은 사람이면 모두 동일 canonical로
- 동명이인 주의 (Johann Strauss vs Richard Strauss). 맥락이 부족하면 가장 유명한 사람으로.
- 작곡가가 아닌 이름(연주자, 편곡자 등으로 추정)도 받은 그대로 매핑은 시도하되,
  도저히 모르는 이름은 입력 그대로 출력해도 된다.

입력 이름 목록:
{json.dumps(names, ensure_ascii=False, indent=2)}

다음 JSON 형식으로 응답:
{{"입력 이름": "canonical 영어 풀네임", ...}}

JSON만 출력. 입력 이름 모두 반드시 포함."""

    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
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
        print("OPENROUTER_API_KEY 필요")
        return 1

    df = pd.read_csv(DATA / "작곡가_곡_5월_전체_v2.csv")
    unique = sorted(df["작곡가"].dropna().astype(str).unique().tolist())
    print(f"unique 작곡가 수: {len(unique)}")

    mapping: dict[str, str] = {}
    for i in range(0, len(unique), CHUNK_SIZE):
        chunk = unique[i : i + CHUNK_SIZE]
        print(f"\n[chunk {i//CHUNK_SIZE + 1}] {len(chunk)}명 매핑 중...")
        try:
            part = call(api_key, chunk)
            mapping.update(part)
            print(f"  성공: {len(part)}건 (누적 {len(mapping)})")
        except Exception as e:
            print(f"  [error] {e}")
        sleep(1)

    df["작곡가_정규화"] = df["작곡가"].map(mapping).fillna(df["작곡가"])
    canon_count = df["작곡가_정규화"].nunique()
    print(f"\n정규화 후 unique canonical 작곡가: {canon_count}명")

    df.to_csv(DATA / "작곡가_곡_5월_전체_정규화.csv", index=False, encoding="utf-8-sig")
    with open(DATA / "composer_mapping_full.json", "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

    top = df["작곡가_정규화"].value_counts().head(20)
    print("\n=== 등장 횟수 TOP 20 ===")
    for c, n in top.items():
        print(f"  {n:3d}  {c}")

    print(f"\n저장: 작곡가_곡_5월_전체_정규화.csv, composer_mapping_full.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
