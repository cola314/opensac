-- SAC Classical Finder — SQLite 스키마
-- source of truth. 모든 추출/정규화 결과가 여기 누적된다.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS concerts (
    id              INTEGER PRIMARY KEY,
    program_code    TEXT UNIQUE NOT NULL,        -- 예술의전당 PROGRAM_CODE
    name            TEXT NOT NULL,
    date            TEXT NOT NULL,               -- "2026.05.22" (BEGIN_DATE)
    end_date        TEXT,
    place           TEXT,
    runtime         TEXT,
    price           TEXT,
    detail_text     TEXT,                        -- 원본 보존
    extracted_at    TIMESTAMP,                   -- LLM 추출 완료 시각 (NULL=미추출)
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_concerts_date ON concerts(date);

CREATE TABLE IF NOT EXISTS pieces (
    id           INTEGER PRIMARY KEY,
    concert_id   INTEGER NOT NULL,
    title        TEXT NOT NULL,
    position     INTEGER NOT NULL,               -- 프로그램 순서 (0부터)
    FOREIGN KEY (concert_id) REFERENCES concerts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_pieces_concert ON pieces(concert_id);

CREATE TABLE IF NOT EXISTS composers (
    id          INTEGER PRIMARY KEY,
    canonical   TEXT UNIQUE NOT NULL,            -- "Ludwig van Beethoven"
    display_ko  TEXT,                            -- "베토벤" (선택)
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS composer_aliases (
    id           INTEGER PRIMARY KEY,
    composer_id  INTEGER NOT NULL,
    alias        TEXT UNIQUE NOT NULL,           -- "베토벤", "L. v. Beethoven", etc.
    FOREIGN KEY (composer_id) REFERENCES composers(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_aliases_composer ON composer_aliases(composer_id);

CREATE TABLE IF NOT EXISTS piece_composers (
    piece_id     INTEGER NOT NULL,
    composer_id  INTEGER NOT NULL,
    position     INTEGER NOT NULL,               -- 공동작곡 순서 (0부터)
    PRIMARY KEY (piece_id, composer_id),
    FOREIGN KEY (piece_id) REFERENCES pieces(id) ON DELETE CASCADE,
    FOREIGN KEY (composer_id) REFERENCES composers(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_pc_composer ON piece_composers(composer_id);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    id              INTEGER PRIMARY KEY,
    month           TEXT NOT NULL,                -- "2026-05"
    started_at      TIMESTAMP NOT NULL,
    finished_at     TIMESTAMP,
    status          TEXT NOT NULL,                -- "running", "completed", "failed"
    concerts_total  INTEGER,
    concerts_new    INTEGER,
    pieces_added    INTEGER,
    composers_added INTEGER,
    error_message   TEXT,
    log             TEXT
);
