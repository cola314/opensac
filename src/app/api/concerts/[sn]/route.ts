import { NextRequest, NextResponse } from 'next/server';
import { getConcertBySn, getProgramsBySn } from '@/db/queries';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ sn: string }> }
) {
  const { sn } = await params;

  try {
    const concert = getConcertBySn(sn);

    if (!concert) {
      return NextResponse.json(
        { error: 'Concert not found' },
        { status: 404 }
      );
    }

    const programs = getProgramsBySn(sn);
    return NextResponse.json({ ...concert, programs });
  } catch (error) {
    console.error('Concert detail error:', error);
    return NextResponse.json(
      { error: 'Failed to fetch concert' },
      { status: 500 }
    );
  }
}
