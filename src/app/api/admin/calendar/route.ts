import { NextRequest } from 'next/server';
import { checkAdminAuth } from '@/lib/admin-auth';
import { sqlite } from '@/db/index';

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  const authError = await checkAdminAuth();
  if (authError) return authError;

  const { searchParams } = new URL(request.url);
  const year = parseInt(searchParams.get('year') || String(new Date().getFullYear()));
  const month = parseInt(searchParams.get('month') || String(new Date().getMonth() + 1));
  const monthStr = String(month).padStart(2, '0');
  const prefix = `${year}.${monthStr}`;

  const rows = sqlite.prepare(`
    SELECT
      c.sn,
      c.title,
      c.begin_date,
      c.place_name,
      c.detail_text,
      COUNT(p.id) as program_count
    FROM concerts c
    LEFT JOIN programs p ON c.sn = p.concert_sn
    WHERE c.begin_date LIKE ?
    GROUP BY c.sn
    ORDER BY c.begin_date, c.playtime
  `).all(`${prefix}%`) as Array<{
    sn: string;
    title: string;
    begin_date: string;
    place_name: string;
    detail_text: string | null;
    program_count: number;
  }>;

  const dates: Record<string, Array<{
    sn: string;
    title: string;
    placeName: string;
    processed: boolean;
    programCount: number;
    hasDetailText: boolean;
  }>> = {};

  let total = 0;
  let processed = 0;

  for (const row of rows) {
    const date = row.begin_date;
    if (!dates[date]) dates[date] = [];

    const isProcessed = row.program_count > 0;
    dates[date].push({
      sn: row.sn,
      title: row.title,
      placeName: row.place_name || '',
      processed: isProcessed,
      programCount: row.program_count,
      hasDetailText: !!row.detail_text,
    });

    total++;
    if (isProcessed) processed++;
  }

  return Response.json({
    year,
    month,
    dates,
    stats: { total, processed, pending: total - processed },
  });
}
