import { NextRequest, NextResponse } from 'next/server';
import { getConcerts, getPlaces } from '@/db/queries';

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;

  const year = searchParams.get('year') ? parseInt(searchParams.get('year')!) : undefined;
  const month = searchParams.get('month') ? parseInt(searchParams.get('month')!) : undefined;
  const query = searchParams.get('q') || undefined;
  const place = searchParams.get('place') || undefined;

  try {
    const concerts = getConcerts({ year, month, query, place });
    const places = getPlaces({ year, month, query });

    // Group concerts by date
    const grouped: Record<string, any[]> = {};
    for (const concert of concerts as any[]) {
      const date = concert.begin_date;
      if (!grouped[date]) grouped[date] = [];
      grouped[date].push(concert);
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
