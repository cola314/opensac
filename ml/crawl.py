"""
예술의전당 음악당 프로그램 크롤링 → data/sac_YYYY_MM.csv 생성.

사용:
  python crawl.py --year 2026 --month 6
  (DATA_DIR 환경변수로 출력 위치 변경 가능)
"""

import argparse
import os
import sys
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

DATA = Path(os.environ.get("DATA_DIR") or (Path(__file__).parent / "data"))


def fetch_calendar(year: int, month: int, category_primary: int = 2) -> dict:
    url = "https://www.sac.or.kr/site/main/program/getProgramCalList"
    payload = {
        "searchYear": str(year),
        "searchMonth": f"{month:02d}",
        "searchFirstDay": "1",
        "searchLastDay": "31",
        "CATEGORY_PRIMARY": str(category_primary),
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "User-Agent": "python-requests/2.x",
    }
    r = requests.post(url, data=payload, headers=headers, timeout=60)
    r.raise_for_status()
    return r.json()


def fetch_detail(sn: int) -> str | None:
    url = f"https://www.sac.or.kr/site/main/show/show_view?SN={sn}"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    first_tab = soup.find(class_="cwa-tab")
    if not first_tab:
        return None
    li_texts = [li.get_text(strip=True) for li in first_tab.find_all("li")]
    container = soup.find(class_="cwa-tab-list")
    if not container:
        return None
    tabs = container.find_all("div", class_="ctl-sub")
    try:
        idx = li_texts.index("작품소개")
    except ValueError:
        return None
    if idx >= len(tabs):
        return None
    return tabs[idx].get_text(strip=True)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--year", type=int, required=True)
    p.add_argument("--month", type=int, required=True)
    args = p.parse_args()

    DATA.mkdir(parents=True, exist_ok=True)
    out = DATA / f"sac_{args.year}_{args.month:02d}.csv"

    print(f"[1/2] 캘린더 fetch: {args.year}-{args.month:02d}")
    cal = fetch_calendar(args.year, args.month)
    flat = []
    for day, events in cal.items():
        if day == "result":
            continue
        for ev in events:
            ev2 = ev.copy()
            ev2["day"] = day
            flat.append(ev2)
    df = pd.DataFrame(flat)
    print(f"  {len(df)}개 공연 발견")
    if df.empty:
        print("  조회 결과 없음")
        return 1

    print(f"[2/2] detail 페이지 fetch ({len(df)}건)")
    details = []
    for i, sn in enumerate(df["SN"], 1):
        try:
            text = fetch_detail(sn)
        except Exception as e:
            print(f"  [{i}/{len(df)}] SN={sn} 실패: {e}")
            text = None
        details.append(text)
        if i % 10 == 0:
            print(f"  진행: {i}/{len(df)}")
    df["detail_text"] = details

    df.to_csv(out, encoding="utf-8", index=False)
    print(f"\n저장: {out}  ({len(df)}건)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
