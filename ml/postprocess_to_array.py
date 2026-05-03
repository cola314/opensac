"""
기존 562행 추출(단일 작곡가 string) → 새 스키마(작곡가 배열 + 편곡자 표기 title 보존).

처리 룰:
- "A & B", "A, B", "A/B"     → 공동작곡, 배열에 모두 포함
- "A - B"                     → 편곡, 작곡가는 [A], title 끝에 "(Arr. B)" 추가
                                 (이미 title에 Arr 표기 있으면 중복 추가 안 함)
- 정규화 매핑 그대로 적용 (composer_mapping_full.json)
"""

import json
import re
import sys
from pathlib import Path

import pandas as pd

DATA = Path(__file__).parent / "data"


def split_composers(raw: str) -> tuple[list[str], str | None]:
    """
    raw 작곡가 문자열을 (composers 리스트, arranger or None)로 분해.
    """
    if not raw or pd.isna(raw):
        return [], None
    raw = str(raw).strip()

    # 1) "A - B" 편곡 형태 (양쪽이 모두 그럴듯한 이름일 때만)
    if " - " in raw and " & " not in raw and ", " not in raw:
        parts = [p.strip() for p in raw.split(" - ")]
        if len(parts) == 2 and all(parts):
            return [parts[0]], parts[1]

    # 2) 공동작곡 split
    parts = re.split(r"\s*[&,/]\s*", raw)
    parts = [p.strip() for p in parts if p.strip()]
    return parts, None


def main() -> int:
    df = pd.read_csv(DATA / "작곡가_곡_5월_전체_정규화.csv")
    mapping = json.load(open(DATA / "composer_mapping_full.json", encoding="utf-8"))

    new_rows = []
    for _, row in df.iterrows():
        raw = row["작곡가"]
        title = str(row["곡명"]) if pd.notna(row["곡명"]) else ""
        composers, arranger = split_composers(raw)

        # canonical 매핑 적용
        canon_composers = [mapping.get(c, c) for c in composers]

        new_title = title
        if arranger:
            arr_canon = mapping.get(arranger, arranger)
            if "Arr" not in title and "arr" not in title:
                new_title = f"{title} (Arr. {arr_canon})".strip()

        new_rows.append(
            {
                "공연명": row["공연명"],
                "날짜": row["날짜"],
                "작곡가들": "; ".join(canon_composers),
                "곡명": new_title,
            }
        )

    out = pd.DataFrame(new_rows)
    out.to_csv(DATA / "작곡가_곡_5월_최종.csv", index=False, encoding="utf-8-sig")

    # 통계: composer explode 기준 unique
    exploded = out.assign(작곡가=out["작곡가들"].str.split("; ")).explode("작곡가")
    exploded = exploded[exploded["작곡가"].notna() & (exploded["작곡가"] != "")]

    print(f"행 수: {len(out)}")
    print(f"composer 펼친 행 수: {len(exploded)}")
    print(f"unique canonical 작곡가: {exploded['작곡가'].nunique()}명")

    print("\n=== TOP 20 ===")
    for c, n in exploded["작곡가"].value_counts().head(20).items():
        print(f"  {n:3d}  {c}")

    print("\n=== 변경된 row 샘플 (split 또는 arranger 추가) ===")
    changed = out[
        out["작곡가들"].str.contains(";", na=False)
        | out["곡명"].str.contains(r"\(Arr\.", na=False, regex=True)
    ].head(15)
    for _, r in changed.iterrows():
        print(f"  - composers=[{r['작곡가들']}]")
        print(f"    title: {r['곡명'][:80]}")

    print(f"\n저장: 작곡가_곡_5월_최종.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
