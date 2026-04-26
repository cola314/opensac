import { db, sqlite } from './index';
import { concerts } from './schema';
import { eq, and, like, sql } from 'drizzle-orm';

export interface ConcertFilters {
  year?: number;
  month?: number;
  query?: string;
  place?: string;
}

export function getConcerts(filters: ConcertFilters) {
  const { year, month, query, place } = filters;

  // If there's a search query, use FTS5
  if (query && query.trim()) {
    const ftsQuery = query.trim().split(/\s+/).map(t => `"${t}"`).join(' OR ');

    let sql_str = `
      SELECT c.* FROM concerts c
      INNER JOIN concerts_fts fts ON c.id = fts.rowid
      WHERE concerts_fts MATCH ?
    `;
    const params: any[] = [ftsQuery];

    if (year && month) {
      const monthStr = String(month).padStart(2, '0');
      sql_str += ` AND c.begin_date LIKE ?`;
      params.push(`${year}.${monthStr}%`);
    }
    if (place) {
      sql_str += ` AND c.place_name = ?`;
      params.push(place);
    }

    sql_str += ` ORDER BY c.begin_date, c.playtime`;

    const stmt = sqlite.prepare(sql_str);
    return stmt.all(...params);
  }

  // No search query — regular filtering
  let sql_str = `SELECT * FROM concerts WHERE 1=1`;
  const params: any[] = [];

  if (year && month) {
    const monthStr = String(month).padStart(2, '0');
    sql_str += ` AND begin_date LIKE ?`;
    params.push(`${year}.${monthStr}%`);
  }
  if (place) {
    sql_str += ` AND place_name = ?`;
    params.push(place);
  }

  sql_str += ` ORDER BY begin_date, playtime`;

  const stmt = sqlite.prepare(sql_str);
  return stmt.all(...params);
}

export function getConcertBySn(sn: string) {
  return sqlite.prepare('SELECT * FROM concerts WHERE sn = ?').get(sn);
}

export function hasMonthData(year: number, month: number): boolean {
  const monthStr = String(month).padStart(2, '0');
  const row = sqlite.prepare(
    'SELECT COUNT(*) as cnt FROM concerts WHERE begin_date LIKE ?'
  ).get(`${year}.${monthStr}%`) as { cnt: number } | undefined;
  return (row?.cnt ?? 0) > 0;
}

export function getProgramsBySn(sn: string) {
  return sqlite.prepare(
    'SELECT composer, piece FROM programs WHERE concert_sn = ? ORDER BY id'
  ).all(sn) as Array<{ composer: string; piece: string }>;
}

export function getProgramsBySnList(sns: string[]) {
  if (sns.length === 0) return {};
  const placeholders = sns.map(() => '?').join(',');
  const rows = sqlite.prepare(
    `SELECT concert_sn, composer, piece FROM programs WHERE concert_sn IN (${placeholders}) ORDER BY id`
  ).all(...sns) as Array<{ concert_sn: string; composer: string; piece: string }>;

  const map: Record<string, Array<{ composer: string; piece: string }>> = {};
  for (const row of rows) {
    if (!map[row.concert_sn]) map[row.concert_sn] = [];
    map[row.concert_sn].push({ composer: row.composer, piece: row.piece });
  }
  return map;
}

const KNOWN_PLACES = ['콘서트홀', '리사이틀홀', 'IBK기업은행챔버홀', '인춘아트홀'];

export function getPlaces(filters?: { year?: number; month?: number; query?: string }) {
  let sql_str: string;
  const params: any[] = [];

  if (filters?.query && filters.query.trim()) {
    const ftsQuery = filters.query.trim().split(/\s+/).map(t => `"${t}"`).join(' OR ');
    sql_str = `
      SELECT c.place_name, COUNT(*) as count FROM concerts c
      INNER JOIN concerts_fts fts ON c.id = fts.rowid
      WHERE concerts_fts MATCH ? AND c.place_name IN (${KNOWN_PLACES.map(() => '?').join(',')})
    `;
    params.push(ftsQuery, ...KNOWN_PLACES);
    if (filters.year && filters.month) {
      const monthStr = String(filters.month).padStart(2, '0');
      sql_str += ` AND c.begin_date LIKE ?`;
      params.push(`${filters.year}.${monthStr}%`);
    }
  } else {
    sql_str = `SELECT place_name, COUNT(*) as count FROM concerts WHERE place_name IN (${KNOWN_PLACES.map(() => '?').join(',')})`;
    params.push(...KNOWN_PLACES);
    if (filters?.year && filters?.month) {
      const monthStr = String(filters.month).padStart(2, '0');
      sql_str += ` AND begin_date LIKE ?`;
      params.push(`${filters.year}.${monthStr}%`);
    }
  }

  sql_str += ` GROUP BY place_name ORDER BY count DESC`;
  return sqlite.prepare(sql_str).all(...params);
}
