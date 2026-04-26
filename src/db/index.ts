import { drizzle } from 'drizzle-orm/better-sqlite3';
import Database from 'better-sqlite3';
import { mkdirSync } from 'fs';
import { dirname } from 'path';
import * as schema from './schema';

const dbPath = process.env.DATABASE_URL || './data/opensac.db';

mkdirSync(dirname(dbPath), { recursive: true });

const sqlite = new Database(dbPath);
sqlite.pragma('journal_mode = WAL');
sqlite.pragma('busy_timeout = 10000');

// Check if schema already initialized (skip heavy DDL if tables exist)
const tableCheck = sqlite.prepare("SELECT count(*) as cnt FROM sqlite_master WHERE type='table' AND name='concerts'").get() as { cnt: number };

if (tableCheck.cnt === 0) {
  // Fresh DB — initialize schema
  sqlite.exec(`
    CREATE TABLE concerts (
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
      crawled_at TEXT NOT NULL,
      programs_text TEXT DEFAULT ''
    );
  `);

  sqlite.exec(`
    CREATE VIRTUAL TABLE concerts_fts USING fts5(
      title, detail_text, programs_text, content=concerts, content_rowid=id
    );
  `);

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

  sqlite.exec(`
    CREATE TABLE programs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      concert_sn TEXT NOT NULL,
      composer TEXT NOT NULL,
      piece TEXT NOT NULL,
      created_at TEXT NOT NULL
    );
  `);
  sqlite.exec(`CREATE INDEX idx_programs_sn ON programs(concert_sn);`);
} else {
  // Existing DB — apply migrations only
  try {
    sqlite.exec(`ALTER TABLE concerts ADD COLUMN programs_text TEXT DEFAULT ''`);
  } catch {
    // Already exists
  }

  // Ensure programs table exists
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

  // FTS migration: check if programs_text column exists in FTS
  const ftsInfo = sqlite.prepare("SELECT sql FROM sqlite_master WHERE name = 'concerts_fts'").get() as { sql: string } | undefined;
  if (!ftsInfo || !ftsInfo.sql?.includes('programs_text')) {
    sqlite.exec(`DROP TABLE IF EXISTS concerts_fts`);
    sqlite.exec(`
      CREATE VIRTUAL TABLE concerts_fts USING fts5(
        title, detail_text, programs_text, content=concerts, content_rowid=id
      );
    `);
    sqlite.exec("INSERT INTO concerts_fts(concerts_fts) VALUES('rebuild')");

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
  }

  // Test FTS integrity
  try {
    sqlite.prepare("SELECT count(*) FROM concerts_fts").get();
  } catch {
    sqlite.exec(`DROP TABLE IF EXISTS concerts_fts`);
    sqlite.exec(`
      CREATE VIRTUAL TABLE concerts_fts USING fts5(
        title, detail_text, programs_text, content=concerts, content_rowid=id
      );
    `);
    sqlite.exec("INSERT INTO concerts_fts(concerts_fts) VALUES('rebuild')");
  }
}

export const db = drizzle(sqlite, { schema });
export { sqlite };
