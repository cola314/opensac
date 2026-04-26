import { sqlite } from './index';
import type { CrawledConcert } from '@/lib/crawler';

const insertStmt = sqlite.prepare(`
  INSERT OR REPLACE INTO concerts (sn, title, title_eng, begin_date, end_date, playtime, place_name, place_code, price_info, sale_state, detail_text, start_week, sac_url, crawled_at)
  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
`);

const rebuildFts = sqlite.transaction(() => {
  sqlite.exec("INSERT INTO concerts_fts(concerts_fts) VALUES('rebuild')");
});

export function importConcerts(concerts: CrawledConcert[]): number {
  const now = new Date().toISOString();
  let count = 0;

  const insertAll = sqlite.transaction(() => {
    for (const c of concerts) {
      insertStmt.run(
        c.sn,
        c.title,
        c.titleEng,
        c.beginDate,
        c.endDate,
        c.playtime,
        c.placeName,
        c.placeCode,
        c.priceInfo,
        c.saleState,
        c.detailText,
        c.startWeek,
        c.sacUrl,
        now
      );
      count++;
    }
  });

  insertAll();
  rebuildFts();

  return count;
}
