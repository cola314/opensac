import { drizzle } from 'drizzle-orm/better-sqlite3';
import Database from 'better-sqlite3';
import * as schema from './schema';

const dbPath = process.env.DATABASE_URL || './data/opensac.db';
const sqlite = new Database(dbPath);

// Enable WAL mode for better concurrent read performance
sqlite.pragma('journal_mode = WAL');

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

// Create FTS5 virtual table if not exists
sqlite.exec(`
  CREATE VIRTUAL TABLE IF NOT EXISTS concerts_fts USING fts5(
    title, detail_text, content=concerts, content_rowid=id
  );
`);

// Triggers to keep FTS in sync
sqlite.exec(`
  CREATE TRIGGER IF NOT EXISTS concerts_ai AFTER INSERT ON concerts BEGIN
    INSERT INTO concerts_fts(rowid, title, detail_text) VALUES (new.id, new.title, new.detail_text);
  END;
`);
sqlite.exec(`
  CREATE TRIGGER IF NOT EXISTS concerts_ad AFTER DELETE ON concerts BEGIN
    INSERT INTO concerts_fts(concerts_fts, rowid, title, detail_text) VALUES('delete', old.id, old.title, old.detail_text);
  END;
`);
sqlite.exec(`
  CREATE TRIGGER IF NOT EXISTS concerts_au AFTER UPDATE ON concerts BEGIN
    INSERT INTO concerts_fts(concerts_fts, rowid, title, detail_text) VALUES('delete', old.id, old.title, old.detail_text);
    INSERT INTO concerts_fts(rowid, title, detail_text) VALUES (new.id, new.title, new.detail_text);
  END;
`);

export const db = drizzle(sqlite, { schema });
export { sqlite };
