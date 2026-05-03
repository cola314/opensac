"""SQLite 연결·헬퍼."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "sac.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """스키마 적용 (idempotent)."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))


def upsert_concert(
    conn: sqlite3.Connection,
    program_code: str,
    name: str,
    date: str,
    end_date: str | None,
    place: str | None,
    runtime: str | None,
    price: str | None,
    detail_text: str | None,
) -> tuple[int, bool]:
    """concert UPSERT. (concert_id, is_new) 반환."""
    cur = conn.execute("SELECT id FROM concerts WHERE program_code = ?", (program_code,))
    row = cur.fetchone()
    if row:
        conn.execute(
            """UPDATE concerts SET name=?, date=?, end_date=?, place=?, runtime=?, price=?,
               detail_text=?, updated_at=CURRENT_TIMESTAMP WHERE id=?""",
            (name, date, end_date, place, runtime, price, detail_text, row["id"]),
        )
        return row["id"], False
    cur = conn.execute(
        """INSERT INTO concerts (program_code, name, date, end_date, place, runtime, price, detail_text)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (program_code, name, date, end_date, place, runtime, price, detail_text),
    )
    return cur.lastrowid, True


def get_or_create_composer(conn: sqlite3.Connection, canonical: str, display_ko: str | None = None) -> int:
    cur = conn.execute("SELECT id FROM composers WHERE canonical = ?", (canonical,))
    row = cur.fetchone()
    if row:
        return row["id"]
    cur = conn.execute(
        "INSERT INTO composers (canonical, display_ko) VALUES (?, ?)",
        (canonical, display_ko),
    )
    return cur.lastrowid


def add_alias(conn: sqlite3.Connection, composer_id: int, alias: str) -> None:
    """alias INSERT (이미 있으면 무시)."""
    conn.execute(
        "INSERT OR IGNORE INTO composer_aliases (composer_id, alias) VALUES (?, ?)",
        (composer_id, alias),
    )


def lookup_alias(conn: sqlite3.Connection, alias: str) -> int | None:
    cur = conn.execute("SELECT composer_id FROM composer_aliases WHERE alias = ?", (alias,))
    row = cur.fetchone()
    return row["composer_id"] if row else None


def get_unmapped_aliases(conn: sqlite3.Connection, names: list[str]) -> list[str]:
    """names 중 alias 테이블에 없는 것만 반환."""
    if not names:
        return []
    placeholders = ",".join("?" * len(names))
    cur = conn.execute(
        f"SELECT alias FROM composer_aliases WHERE alias IN ({placeholders})",
        names,
    )
    known = {r["alias"] for r in cur.fetchall()}
    return [n for n in names if n not in known]
