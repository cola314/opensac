"""
SAC Classical Finder — 단일 파이프라인 entrypoint.

사용:
  python run_pipeline.py --month 2026-05 --csv data/sac_2026_05.csv
  python run_pipeline.py --month 2026-06               # csv 자동 탐색 (data/sac_2026_06.csv)
  python run_pipeline.py --month 2026-05 --force       # 기존 추출도 재실행

동작:
  1. SQLite 스키마 init (idempotent)
  2. CSV 로드 → concerts UPSERT (program_code 기준 중복 방지)
  3. 신규 공연만 LLM 추출 (또는 --force로 전체 재추출)
  4. 신규 작곡가 이름만 LLM 정규화 → composers + aliases 누적
  5. piece_composers 링크
  6. pipeline_runs에 실행 기록
  7. (Express 호환용) data/concerts.json, composers.json 빌드

환경변수:
  OPENROUTER_API_KEY 필요
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from time import sleep

import pandas as pd
import requests

from db import (
    DB_PATH,
    SCHEMA_PATH,
    add_alias,
    connect,
    get_or_create_composer,
    init_db,
    lookup_alias,
    upsert_concert,
)
from extract_full_may import PROMPT_TEMPLATE, call_gemini

DATA = Path(__file__).parent / "data"


def split_composer_string(raw: str) -> list[str]:
    """LLM 출력의 단일 composer string을 방어적으로 split.

    "H. Zimmer & J. Powell" → ["H. Zimmer", "J. Powell"]
    이미 array로 들어왔으면 호출자가 처리.
    """
    parts = re.split(r"\s*[&,/]\s*", str(raw).strip())
    return [p for p in (s.strip() for s in parts) if p]


def normalize_composer_names(
    conn, names: list[str], api_key: str, chunk_size: int = 80
) -> dict[str, int]:
    """names → composer_id 매핑. DB에 없는 것만 LLM 호출."""
    result: dict[str, int] = {}
    unknown: list[str] = []
    for n in names:
        cid = lookup_alias(conn, n)
        if cid:
            result[n] = cid
        else:
            unknown.append(n)

    if not unknown:
        return result

    print(f"  신규 작곡가 {len(unknown)}명 정규화 중...")
    for i in range(0, len(unknown), chunk_size):
        chunk = unknown[i : i + chunk_size]
        mapping = _llm_normalize(api_key, chunk)
        for raw_name, canonical in mapping.items():
            cid = get_or_create_composer(conn, canonical)
            add_alias(conn, cid, raw_name)
            result[raw_name] = cid
        sleep(1)
    return result


def _llm_normalize(api_key: str, names: list[str]) -> dict[str, str]:
    prompt = f"""다음은 클래식 작곡가 이름 목록입니다 (한국어/영어/약어 혼재).
각 이름을 canonical 영어 풀네임으로 매핑해주세요.

규칙:
- canonical 형식: "Ludwig van Beethoven" (Wikipedia/IMSLP 표준)
- diacritics 보존: "Antonín Dvořák", "Frédéric Chopin"
- 같은 사람이면 모두 동일 canonical로
- 동명이인 주의 (Johann Strauss vs Richard Strauss). 맥락이 부족하면 가장 유명한 사람으로.
- 영화음악/현대 작곡가도 가능한 풀네임으로 (예: "H. Zimmer" → "Hans Zimmer")
- 도저히 모르는 이름은 입력 그대로 출력

입력:
{json.dumps(names, ensure_ascii=False, indent=2)}

JSON: {{"입력": "canonical", ...}}  (모든 입력 반드시 포함)
JSON만 출력."""

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


def export_to_json(conn) -> tuple[int, int]:
    """Express 호환용 JSON 빌드. (concerts_count, composers_count) 반환."""
    rows = conn.execute(
        """SELECT c.id, c.name, c.date, c.place, c.runtime, c.price
           FROM concerts c
           WHERE c.extracted_at IS NOT NULL
           ORDER BY c.date"""
    ).fetchall()
    concerts_out = []
    for c in rows:
        pieces_rows = conn.execute(
            """SELECT id, title, position FROM pieces
               WHERE concert_id = ? ORDER BY position""",
            (c["id"],),
        ).fetchall()
        pieces = []
        for p in pieces_rows:
            comp_rows = conn.execute(
                """SELECT cm.canonical FROM piece_composers pc
                   JOIN composers cm ON pc.composer_id = cm.id
                   WHERE pc.piece_id = ? ORDER BY pc.position""",
                (p["id"],),
            ).fetchall()
            pieces.append({"composers": [r["canonical"] for r in comp_rows], "title": p["title"]})
        obj = {"name": c["name"], "date": c["date"], "pieces": pieces}
        for k in ("place", "runtime", "price"):
            if c[k]:
                obj[k] = c[k]
        concerts_out.append(obj)

    composers_rows = conn.execute(
        """SELECT cm.canonical, COUNT(DISTINCT p.concert_id) as cnt
           FROM composers cm
           JOIN piece_composers pc ON pc.composer_id = cm.id
           JOIN pieces p ON p.id = pc.piece_id
           JOIN concerts c ON c.id = p.concert_id
           WHERE c.extracted_at IS NOT NULL
           GROUP BY cm.id
           ORDER BY cnt DESC"""
    ).fetchall()
    composers_out = [{"name": r["canonical"], "count": r["cnt"]} for r in composers_rows]

    (DATA / "concerts.json").write_text(
        json.dumps(concerts_out, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    (DATA / "composers.json").write_text(
        json.dumps(composers_out, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    return len(concerts_out), len(composers_out)


def run(month: str, csv_path: Path, force: bool, api_key: str) -> int:
    init_db()
    conn = connect()

    started_at = datetime.utcnow().isoformat()
    cur = conn.execute(
        "INSERT INTO pipeline_runs (month, started_at, status) VALUES (?, ?, 'running')",
        (month, started_at),
    )
    run_id = cur.lastrowid
    conn.commit()

    log_lines = []

    def log(msg: str) -> None:
        print(msg)
        log_lines.append(msg)

    try:
        df = pd.read_csv(csv_path)
        df = df[df["detail_text"].notna()].reset_index(drop=True)
        log(f"CSV 로드: {len(df)} 공연 (detail 있음)")

        new_count = 0
        skipped = 0
        pieces_added = 0
        composers_added_set: set[int] = set()

        for idx, row in df.iterrows():
            program_code = str(row["PROGRAM_CODE"])
            concert_id, is_new = upsert_concert(
                conn,
                program_code=program_code,
                name=row["PROGRAM_SUBJECT"],
                date=row["BEGIN_DATE"],
                end_date=row.get("END_DATE") if pd.notna(row.get("END_DATE")) else None,
                place=row.get("PLACE_NAME") if pd.notna(row.get("PLACE_NAME")) else None,
                runtime=row.get("PROGRAM_PLAYTIME") if pd.notna(row.get("PROGRAM_PLAYTIME")) else None,
                price=row.get("PRICE_INFO") if pd.notna(row.get("PRICE_INFO")) else None,
                detail_text=row["detail_text"],
            )

            already_extracted = conn.execute(
                "SELECT extracted_at FROM concerts WHERE id = ?", (concert_id,)
            ).fetchone()["extracted_at"]

            if already_extracted and not force:
                skipped += 1
                continue

            log(f"[{idx+1}/{len(df)}] LLM 추출: {row['PROGRAM_SUBJECT'][:50]}")
            try:
                pieces = call_gemini(api_key, row["detail_text"])
            except Exception as e:
                log(f"  [error] {e}")
                continue

            if force:
                conn.execute("DELETE FROM pieces WHERE concert_id = ?", (concert_id,))

            all_composer_names: list[str] = []
            for p in pieces:
                comps = p.get("composers") or ([p.get("composer", "")] if p.get("composer") else [])
                if not isinstance(comps, list):
                    comps = [comps]
                expanded = []
                for c in comps:
                    expanded.extend(split_composer_string(c))
                all_composer_names.extend(expanded)

            existing_composer_count = conn.execute("SELECT COUNT(*) as n FROM composers").fetchone()["n"]
            name_to_id = normalize_composer_names(conn, all_composer_names, api_key)
            new_composers_now = (
                conn.execute("SELECT COUNT(*) as n FROM composers").fetchone()["n"]
                - existing_composer_count
            )
            composers_added_set.update(range(new_composers_now))

            for pos, p in enumerate(pieces):
                title = p.get("title", "")
                cur = conn.execute(
                    "INSERT INTO pieces (concert_id, title, position) VALUES (?, ?, ?)",
                    (concert_id, title, pos),
                )
                piece_id = cur.lastrowid
                pieces_added += 1
                comps = p.get("composers") or ([p.get("composer", "")] if p.get("composer") else [])
                if not isinstance(comps, list):
                    comps = [comps]
                seen: set[int] = set()
                cpos = 0
                for c in comps:
                    for split_name in split_composer_string(c):
                        cid = name_to_id.get(split_name)
                        if cid is None or cid in seen:
                            continue
                        conn.execute(
                            "INSERT INTO piece_composers (piece_id, composer_id, position) VALUES (?, ?, ?)",
                            (piece_id, cid, cpos),
                        )
                        seen.add(cid)
                        cpos += 1

            conn.execute(
                "UPDATE concerts SET extracted_at = CURRENT_TIMESTAMP WHERE id = ?", (concert_id,)
            )
            conn.commit()
            new_count += 1
            sleep(0.7)

        log(f"\n신규 추출: {new_count}, skip: {skipped}, 곡 추가: {pieces_added}")

        c_cnt, comp_cnt = export_to_json(conn)
        log(f"JSON export: {c_cnt} 공연, {comp_cnt} 작곡가")

        conn.execute(
            """UPDATE pipeline_runs SET finished_at=CURRENT_TIMESTAMP, status='completed',
               concerts_total=?, concerts_new=?, pieces_added=?, composers_added=?, log=?
               WHERE id=?""",
            (len(df), new_count, pieces_added, len(composers_added_set), "\n".join(log_lines), run_id),
        )
        conn.commit()
        return 0

    except Exception as e:
        conn.execute(
            """UPDATE pipeline_runs SET finished_at=CURRENT_TIMESTAMP, status='failed',
               error_message=?, log=? WHERE id=?""",
            (str(e), "\n".join(log_lines), run_id),
        )
        conn.commit()
        raise
    finally:
        conn.close()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--month", required=True, help="YYYY-MM (예: 2026-05)")
    p.add_argument("--csv", help="입력 CSV 경로 (생략 시 data/sac_YYYY_MM.csv 자동 탐색)")
    p.add_argument("--force", action="store_true", help="이미 추출한 공연도 재실행")
    args = p.parse_args()

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("OPENROUTER_API_KEY 환경변수 필요", file=sys.stderr)
        return 1

    csv_path = Path(args.csv) if args.csv else DATA / f"sac_{args.month.replace('-', '_')}.csv"
    if not csv_path.exists():
        print(f"CSV 파일 없음: {csv_path}", file=sys.stderr)
        return 1

    return run(args.month, csv_path, args.force, api_key)


if __name__ == "__main__":
    sys.exit(main())
