import { drizzle } from 'drizzle-orm/better-sqlite3';
import Database from 'better-sqlite3';
import * as schema from './schema';

const dbPath = process.env.DATABASE_URL || './data/opensac.db';
const sqlite = new Database(dbPath);

// Enable WAL mode for better concurrent read performance
sqlite.pragma('journal_mode = WAL');
sqlite.pragma('busy_timeout = 5000');

// Create concerts table if not exists
sqlite.exec(`
  CREATE TABLE IF NOT EXISTS concerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sn TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    title_eng TEXT,
    begin_date TEXT NOT NULL,
    end_date TEXT,
    playtime TEXT,
    place_name TEXT,
    place_code TEXT,
    price_info TEXT,
    sale_state TEXT,
    detail_text TEXT,
    start_week TEXT,
    sac_url TEXT,
    crawled_at TEXT NOT NULL
  );
`);

// Recreate FTS5 if schema changed (add programs_text column)
const ftsInfo = sqlite.prepare("SELECT sql FROM sqlite_master WHERE name = 'concerts_fts'").get() as { sql: string } | undefined;
if (ftsInfo && !ftsInfo.sql?.includes('programs_text')) {
  sqlite.exec(`DROP TABLE IF EXISTS concerts_fts`);
}

sqlite.exec(`
  CREATE VIRTUAL TABLE IF NOT EXISTS concerts_fts USING fts5(
    title, detail_text, programs_text, content=concerts, content_rowid=id
  );
`);

// Add programs_text column if not exists
try {
  sqlite.exec(`ALTER TABLE concerts ADD COLUMN programs_text TEXT DEFAULT ''`);
} catch {
  // Column already exists
}

// Triggers to keep FTS in sync (drop and recreate to handle schema changes)
sqlite.exec(`DROP TRIGGER IF EXISTS concerts_ai`);
sqlite.exec(`DROP TRIGGER IF EXISTS concerts_ad`);
sqlite.exec(`DROP TRIGGER IF EXISTS concerts_au`);
sqlite.exec(`
  CREATE TRIGGER concerts_ai AFTER INSERT ON concerts BEGIN
    INSERT INTO concerts_fts(rowid, title, detail_text, programs_text) VALUES (new.id, new.title, new.detail_text, new.programs_text);
  END;
`);
sqlite.exec(`
  CREATE TRIGGER concerts_ad AFTER DELETE ON concerts BEGIN
    INSERT INTO concerts_fts(concerts_fts, rowid, title, detail_text, programs_text) VALUES('delete', old.id, old.title, old.detail_text, old.programs_text);
  END;
`);
sqlite.exec(`
  CREATE TRIGGER concerts_au AFTER UPDATE ON concerts BEGIN
    INSERT INTO concerts_fts(concerts_fts, rowid, title, detail_text, programs_text) VALUES('delete', old.id, old.title, old.detail_text, old.programs_text);
    INSERT INTO concerts_fts(rowid, title, detail_text, programs_text) VALUES (new.id, new.title, new.detail_text, new.programs_text);
  END;
`);

// Create programs table if not exists
sqlite.exec(`
  CREATE TABLE IF NOT EXISTS programs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    concert_sn TEXT NOT NULL,
    composer TEXT NOT NULL,
    piece TEXT NOT NULL,
    created_at TEXT NOT NULL
  );
`);
sqlite.exec(`CREATE INDEX IF NOT EXISTS idx_programs_sn ON programs(concert_sn);`);

export const db = drizzle(sqlite, { schema });
export { sqlite };
