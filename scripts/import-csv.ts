import Database from 'better-sqlite3';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const csvPath = process.argv[2];
if (!csvPath) {
  console.error('Usage: npx tsx scripts/import-csv.ts <path-to-csv>');
  process.exit(1);
}

const dbPath = process.env.DATABASE_URL || './data/opensac.db';
const db = new Database(dbPath);

// Create table
db.exec(`
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

db.exec(`
  CREATE VIRTUAL TABLE IF NOT EXISTS concerts_fts USING fts5(
    title, detail_text, content=concerts, content_rowid=id
  );
`);

// Parse CSV
const raw = readFileSync(resolve(csvPath), 'utf-8');
const lines = raw.split('\n');
const headers = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g, ''));

const insert = db.prepare(`
  INSERT OR REPLACE INTO concerts (sn, title, title_eng, begin_date, end_date, playtime, place_name, place_code, price_info, sale_state, detail_text, start_week, sac_url, crawled_at)
  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
`);

// Simple CSV parser that handles quoted fields
function parseCSVLine(line: string): string[] {
  const result: string[] = [];
  let current = '';
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    if (char === '"') {
      if (inQuotes && line[i + 1] === '"') {
        current += '"';
        i++;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (char === ',' && !inQuotes) {
      result.push(current);
      current = '';
    } else {
      current += char;
    }
  }
  result.push(current);
  return result;
}

function getField(fields: string[], name: string): string {
  const idx = headers.indexOf(name);
  return idx >= 0 ? (fields[idx] || '').trim() : '';
}

const insertMany = db.transaction((dataLines: string[]) => {
  // Clear FTS
  db.exec("INSERT INTO concerts_fts(concerts_fts) VALUES('delete-all')");

  let count = 0;
  for (const line of dataLines) {
    if (!line.trim()) continue;
    const fields = parseCSVLine(line);

    const sn = getField(fields, 'SN');
    if (!sn) continue;

    insert.run(
      sn,
      getField(fields, 'PROGRAM_SUBJECT'),
      getField(fields, 'PROGRAM_SUBJECT_ENG'),
      getField(fields, 'BEGIN_DATE'),
      getField(fields, 'END_DATE'),
      getField(fields, 'PROGRAM_PLAYTIME'),
      getField(fields, 'PLACE_NAME'),
      getField(fields, 'PLACE_CODE'),
      getField(fields, 'PRICE_INFO'),
      getField(fields, 'SALE_STATE_CODE_NAME'),
      getField(fields, 'detail_text'),
      getField(fields, 'START_WEEK'),
      `https://www.sac.or.kr/site/main/show/show_view?SN=${sn}`,
      new Date().toISOString()
    );
    count++;
  }

  // Rebuild FTS index
  db.exec("INSERT INTO concerts_fts(concerts_fts) VALUES('rebuild')");

  return count;
});

const count = insertMany(lines.slice(1));
console.log(`Imported ${count} concerts into ${dbPath}`);

db.close();
