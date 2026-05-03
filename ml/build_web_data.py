"""
웹 앱이 사용할 최종 JSON을 빌드한다.

입력:
  data/sac_2026_05.csv               (공연 메타: 장소, 시간, 가격 등)
  data/작곡가_곡_5월_최종.csv         (정규화된 작곡가-곡)

출력:
  data/concerts.json                 (공연별 nested, 웹앱이 그대로 import)
  data/composers.json                (작곡가 통계: canonical → 등장 횟수)
"""

import json
from pathlib import Path

import pandas as pd


DATA = Path(__file__).parent / "data"


def main() -> None:
    df = pd.read_csv(DATA / "작곡가_곡_5월_최종.csv")
    sac = pd.read_csv(DATA / "sac_2026_05.csv")
    sac = sac.dropna(subset=["PROGRAM_SUBJECT"]).drop_duplicates("PROGRAM_SUBJECT")

    concerts = []
    for name, group in df.groupby("공연명"):
        meta = sac[sac["PROGRAM_SUBJECT"] == name]
        pieces = []
        for _, r in group.iterrows():
            comps = (
                r["작곡가들"].split("; ")
                if pd.notna(r["작곡가들"]) and r["작곡가들"]
                else []
            )
            pieces.append({"composers": comps, "title": r["곡명"]})
        obj = {"name": name, "date": group["날짜"].iloc[0], "pieces": pieces}
        if not meta.empty:
            m = meta.iloc[0]
            for src, dst in [
                ("PLACE_NAME", "place"),
                ("PROGRAM_PLAYTIME", "runtime"),
                ("PRICE_INFO", "price"),
                ("BEGIN_DATE", "begin"),
                ("END_DATE", "end"),
            ]:
                if src in m and pd.notna(m[src]):
                    obj[dst] = m[src]
        concerts.append(obj)

    concerts.sort(key=lambda c: c.get("date", ""))

    with open(DATA / "concerts.json", "w", encoding="utf-8") as f:
        json.dump(concerts, f, ensure_ascii=False, separators=(",", ":"))

    composers: dict[str, int] = {}
    for c in concerts:
        unique_in_concert = {comp for p in c["pieces"] for comp in p["composers"]}
        for comp in unique_in_concert:
            composers[comp] = composers.get(comp, 0) + 1
    with open(DATA / "composers.json", "w", encoding="utf-8") as f:
        json.dump(
            sorted(
                [{"name": k, "count": v} for k, v in composers.items()],
                key=lambda x: -x["count"],
            ),
            f,
            ensure_ascii=False,
            separators=(",", ":"),
        )

    sz_concerts = (DATA / "concerts.json").stat().st_size
    sz_composers = (DATA / "composers.json").stat().st_size
    print(f"concerts.json:  {len(concerts):3d} 공연  ({sz_concerts/1024:.1f} KB)")
    print(f"composers.json: {len(composers):3d} 작곡가 ({sz_composers/1024:.1f} KB)")


if __name__ == "__main__":
    main()
