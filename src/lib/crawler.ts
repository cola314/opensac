import * as cheerio from 'cheerio';

interface SacEvent {
  SN: string;
  PROGRAM_SUBJECT: string;
  PROGRAM_SUBJECT_ENG?: string;
  BEGIN_DATE: string;
  END_DATE?: string;
  PROGRAM_PLAYTIME?: string;
  PLACE_NAME?: string;
  PLACE_CODE?: string;
  PRICE_INFO?: string;
  SALE_STATE_CODE_NAME?: string;
  START_WEEK?: string;
}

export interface CrawledConcert {
  sn: string;
  title: string;
  titleEng: string | null;
  beginDate: string;
  endDate: string | null;
  playtime: string | null;
  placeName: string | null;
  placeCode: string | null;
  priceInfo: string | null;
  saleState: string | null;
  startWeek: string | null;
  detailText: string | null;
  sacUrl: string;
}

/**
 * Fetch concert calendar from SAC API for a given year/month.
 * categoryPrimary=2 is "음악" (classical music).
 */
export async function fetchSacCalendar(
  year: number,
  month: number,
  categoryPrimary = 2
): Promise<SacEvent[]> {
  const url = 'https://www.sac.or.kr/site/main/program/getProgramCalList';
  const body = new URLSearchParams({
    searchYear: String(year),
    searchMonth: String(month).padStart(2, '0'),
    searchFirstDay: '1',
    searchLastDay: '31',
    CATEGORY_PRIMARY: String(categoryPrimary),
  });

  const resp = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
      'User-Agent': 'opensac-crawler/1.0',
    },
    body: body.toString(),
  });

  if (!resp.ok) {
    throw new Error(`SAC API error: ${resp.status} ${resp.statusText}`);
  }

  const data = await resp.json();
  const events: SacEvent[] = [];

  for (const [key, value] of Object.entries(data)) {
    if (key === 'result') continue;
    if (Array.isArray(value)) {
      for (const event of value) {
        events.push(event as SacEvent);
      }
    }
  }

  return events;
}

/**
 * Fetch detail page for a concert and extract "작품소개" text.
 */
export async function fetchDetail(sn: string): Promise<string | null> {
  const url = `https://www.sac.or.kr/site/main/show/show_view?SN=${sn}`;

  const resp = await fetch(url, {
    headers: { 'User-Agent': 'Mozilla/5.0' },
  });

  if (!resp.ok) return null;

  const html = await resp.text();
  const $ = cheerio.load(html);

  const tabItems = $('.cwa-tab li');
  const tabs = $('.cwa-tab-list .ctl-sub');

  if (tabItems.length === 0 || tabs.length === 0) return null;

  let introIndex = -1;
  tabItems.each((i, el) => {
    if ($(el).text().trim() === '작품소개') {
      introIndex = i;
    }
  });

  if (introIndex < 0 || introIndex >= tabs.length) return null;

  return $(tabs[introIndex]).text().trim() || null;
}

/**
 * Crawl all concerts for a given year/month and return structured data.
 * Fetches calendar list, then detail pages in parallel (with concurrency limit).
 */
export async function crawlMonth(
  year: number,
  month: number
): Promise<CrawledConcert[]> {
  const events = await fetchSacCalendar(year, month);

  // Deduplicate by SN
  const uniqueEvents = new Map<string, SacEvent>();
  for (const e of events) {
    if (e.SN && !uniqueEvents.has(e.SN)) {
      uniqueEvents.set(e.SN, e);
    }
  }

  const entries = Array.from(uniqueEvents.values());

  // Fetch details with concurrency limit of 5
  const concurrency = 5;
  const results: CrawledConcert[] = [];

  for (let i = 0; i < entries.length; i += concurrency) {
    const batch = entries.slice(i, i + concurrency);
    const details = await Promise.all(
      batch.map(async (event) => {
        const detailText = await fetchDetail(event.SN).catch(() => null);
        return {
          sn: event.SN,
          title: event.PROGRAM_SUBJECT,
          titleEng: event.PROGRAM_SUBJECT_ENG || null,
          beginDate: event.BEGIN_DATE,
          endDate: event.END_DATE || null,
          playtime: event.PROGRAM_PLAYTIME || null,
          placeName: event.PLACE_NAME || null,
          placeCode: event.PLACE_CODE || null,
          priceInfo: event.PRICE_INFO || null,
          saleState: event.SALE_STATE_CODE_NAME || null,
          startWeek: event.START_WEEK || null,
          detailText,
          sacUrl: `https://www.sac.or.kr/site/main/show/show_view?SN=${event.SN}`,
        } satisfies CrawledConcert;
      })
    );
    results.push(...details);
  }

  return results;
}
