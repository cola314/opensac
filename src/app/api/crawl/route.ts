import { NextRequest } from 'next/server';
import { crawlMonth } from '@/lib/crawler';
import { importConcerts } from '@/db/import';

export const dynamic = 'force-dynamic';

export async function POST(request: NextRequest) {
  const authHeader = request.headers.get('authorization');
  const secret = process.env.CRAWL_SECRET;
  if (secret && authHeader !== `Bearer ${secret}`) {
    return Response.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const body = await request.json().catch(() => ({}));
  const year = body.year || new Date().getFullYear();
  const month = body.month || new Date().getMonth() + 1;

  try {
    const concerts = await crawlMonth(year, month);
    const count = importConcerts(concerts);

    return Response.json({
      ok: true,
      year,
      month,
      crawled: concerts.length,
      imported: count,
    });
  } catch (error) {
    console.error('Crawl error:', error);
    return Response.json(
      { error: 'Crawl failed', message: String(error) },
      { status: 500 }
    );
  }
}
