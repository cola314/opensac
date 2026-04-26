import { NextRequest, NextResponse } from 'next/server';
import { getConcerts, getPlaces, hasMonthData, getProgramsBySnList } from '@/db/queries';
import { crawlMonth } from '@/lib/crawler';
import { importConcerts } from '@/db/import';
import { getInMemoryLock } from '@/lib/lock';

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;

  const year = searchParams.get('year') ? parseInt(searchParams.get('year')!) : undefined;
  const month = searchParams.get('month') ? parseInt(searchParams.get('month')!) : undefined;
  const query = searchParams.get('q') || undefined;
  const place = searchParams.get('place') || undefined;

  try {
    // Lazy crawl: if year/month specified but no data exists, crawl on-demand
    if (year && month && !hasMonthData(year, month)) {
      const lock = getInMemoryLock();
      const key = `${year}-${month}`;
      const { acquired } = await lock.acquire(key);
      try {
        if (acquired) {
          const crawled = await crawlMonth(year, month);
          if (crawled.length > 0) {
            importConcerts(crawled);
          }
        }
        // acquired=false면 이미 다른 요청이 크롤링 완료한 상태
      } catch (e) {
        console.error(`Lazy crawl failed for ${year}-${month}:`, e);
      } finally {
        if (acquired) lock.release(key);
      }
    }

    const concerts = getConcerts({ year, month, query, place }) as any[];
    const places = getPlaces({ year, month, query });

    // Attach programs to each concert
    const sns = concerts.map((c: any) => c.sn);
    const programsMap = getProgramsBySnList(sns);

    // Group concerts by date
    const grouped: Record<string, any[]> = {};
    for (const concert of concerts) {
      const date = concert.begin_date;
      if (!grouped[date]) grouped[date] = [];
      grouped[date].push({
        ...concert,
        programs: programsMap[concert.sn] || [],
      });
    }

    return NextResponse.json({
      total: (concerts as any[]).length,
      places,
      dates: grouped,
    });
  } catch (error) {
    console.error('Concert search error:', error);
    return NextResponse.json(
      { error: 'Failed to fetch concerts' },
      { status: 500 }
    );
  }
}
