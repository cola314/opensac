'use client';

import Link from 'next/link';
import { notFound } from 'next/navigation';
import { cleanDetailText, formatDate, formatDateRange, getWeekdayName } from '@/lib/utils';

interface Concert {
  id: number;
  sn: string;
  title: string;
  title_eng?: string | null;
  begin_date: string;
  end_date?: string | null;
  playtime?: string | null;
  place_name?: string | null;
  place_code?: string | null;
  price_info?: string | null;
  sale_state?: string | null;
  detail_text?: string | null;
  start_week?: string | null;
  sac_url?: string | null;
  crawled_at: string;
}

async function getConcert(sn: string): Promise<Concert | null> {
  try {
    const baseUrl =
      process.env.NEXT_PUBLIC_BASE_URL ||
      (process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : 'http://localhost:3000');

    const res = await fetch(`${baseUrl}/api/concerts/${sn}`, {
      cache: 'no-store',
    });

    if (res.status === 404) return null;
    if (!res.ok) throw new Error('Fetch failed');
    return res.json();
  } catch {
    return null;
  }
}

export default async function ConcertDetailPage({
  params,
}: {
  params: Promise<{ sn: string }>;
}) {
  const { sn } = await params;
  const concert = await getConcert(sn);

  if (!concert) {
    notFound();
  }

  const cleanedDetail = cleanDetailText(concert.detail_text);
  const detailParagraphs = cleanedDetail.split('\n').filter((l) => l.trim());
  const formattedDate = formatDate(concert.begin_date, concert.start_week ?? undefined);
  const dateRange = formatDateRange(concert.begin_date, concert.end_date);

  return (
    <div className="min-h-screen" style={{ backgroundColor: '#f5f5f7' }}>
      {/* Dark header */}
      <header style={{ backgroundColor: '#000000' }}>
        <div
          className="mx-auto"
          style={{ maxWidth: '760px', padding: '24px 20px 0' }}
        >
          {/* Back nav */}
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 mb-6 text-[14px] font-medium transition-colors"
            style={{ color: '#6e6e73', textDecoration: 'none' }}
            onMouseEnter={(e) =>
              ((e.currentTarget as HTMLElement).style.color = '#ffffff')
            }
            onMouseLeave={(e) =>
              ((e.currentTarget as HTMLElement).style.color = '#6e6e73')
            }
          >
            <svg width="7" height="12" viewBox="0 0 7 12" fill="none">
              <path
                d="M6 1L1 6L6 11"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            공연 목록
          </Link>

          {/* Concert header content */}
          <div style={{ paddingBottom: '40px' }}>
            {/* Place badge */}
            {concert.place_name && (
              <span
                className="inline-block px-3 py-1 rounded-full text-[12px] font-semibold mb-4"
                style={{
                  backgroundColor: 'rgba(0, 113, 227, 0.2)',
                  color: '#2997ff',
                  border: '1px solid rgba(41, 151, 255, 0.3)',
                }}
              >
                {concert.place_name}
              </span>
            )}

            <h1
              className="font-semibold leading-tight mb-3"
              style={{
                fontSize: 'clamp(24px, 4vw, 36px)',
                color: '#ffffff',
                letterSpacing: '-0.4px',
                lineHeight: 1.1,
              }}
            >
              {concert.title}
            </h1>

            {concert.title_eng && (
              <p
                className="text-[15px] mb-5"
                style={{ color: '#6e6e73', letterSpacing: '-0.1px' }}
              >
                {concert.title_eng}
              </p>
            )}

            {/* Meta row */}
            <div className="flex flex-wrap gap-x-6 gap-y-2">
              <div className="flex items-center gap-2">
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 14 14"
                  fill="none"
                  style={{ color: '#6e6e73', flexShrink: 0 }}
                >
                  <rect
                    x="1"
                    y="2.5"
                    width="12"
                    height="10.5"
                    rx="2"
                    stroke="currentColor"
                    strokeWidth="1.2"
                  />
                  <path
                    d="M4.5 1V3M9.5 1V3"
                    stroke="currentColor"
                    strokeWidth="1.2"
                    strokeLinecap="round"
                  />
                  <path d="M1 6H13" stroke="currentColor" strokeWidth="1.2" />
                </svg>
                <span className="text-[14px]" style={{ color: '#d2d2d7' }}>
                  {dateRange || formattedDate}
                </span>
              </div>

              {concert.playtime && (
                <div className="flex items-center gap-2">
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 14 14"
                    fill="none"
                    style={{ color: '#6e6e73', flexShrink: 0 }}
                  >
                    <circle
                      cx="7"
                      cy="7"
                      r="6"
                      stroke="currentColor"
                      strokeWidth="1.2"
                    />
                    <path
                      d="M7 4V7.5L9.5 9"
                      stroke="currentColor"
                      strokeWidth="1.2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                  <span className="text-[14px]" style={{ color: '#d2d2d7' }}>
                    {concert.playtime}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Body content */}
      <main
        className="mx-auto"
        style={{ maxWidth: '760px', padding: '32px 20px 64px' }}
      >
        <div className="flex flex-col gap-6">
          {/* Sale state card */}
          {concert.sale_state && (
            <div
              className="rounded-2xl p-5"
              style={{
                backgroundColor: '#ffffff',
                border: '1px solid #d2d2d7',
              }}
            >
              <div className="flex items-center justify-between">
                <span
                  className="text-[13px] font-semibold uppercase tracking-wider"
                  style={{ color: '#86868b' }}
                >
                  예매 상태
                </span>
                <span
                  className="px-3 py-1 rounded-full text-[13px] font-semibold"
                  style={{
                    backgroundColor: concert.sale_state.includes('예매')
                      ? 'rgba(0, 113, 227, 0.1)'
                      : 'rgba(110, 110, 115, 0.1)',
                    color: concert.sale_state.includes('예매')
                      ? '#0071e3'
                      : '#6e6e73',
                    border: `1px solid ${
                      concert.sale_state.includes('예매')
                        ? 'rgba(0, 113, 227, 0.2)'
                        : 'rgba(110, 110, 115, 0.2)'
                    }`,
                  }}
                >
                  {concert.sale_state}
                </span>
              </div>
            </div>
          )}

          {/* Price card */}
          {concert.price_info && (
            <div
              className="rounded-2xl p-5"
              style={{
                backgroundColor: '#ffffff',
                border: '1px solid #d2d2d7',
              }}
            >
              <h2
                className="text-[13px] font-semibold uppercase tracking-wider mb-3"
                style={{ color: '#86868b' }}
              >
                가격
              </h2>
              <p
                className="text-[15px] leading-relaxed"
                style={{ color: '#1d1d1f' }}
              >
                {concert.price_info}
              </p>
            </div>
          )}

          {/* Program / detail card */}
          {detailParagraphs.length > 0 && (
            <div
              className="rounded-2xl p-5"
              style={{
                backgroundColor: '#ffffff',
                border: '1px solid #d2d2d7',
              }}
            >
              <h2
                className="text-[13px] font-semibold uppercase tracking-wider mb-4"
                style={{ color: '#86868b' }}
              >
                작품 소개
              </h2>
              <div className="flex flex-col gap-3">
                {detailParagraphs.map((para, i) => (
                  <p
                    key={i}
                    className="text-[15px] leading-relaxed"
                    style={{ color: '#1d1d1f' }}
                  >
                    {para}
                  </p>
                ))}
              </div>
            </div>
          )}

          {/* SAC link */}
          {concert.sac_url && (
            <a
              href={concert.sac_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center gap-2 w-full py-3 rounded-full text-[15px] font-semibold transition-colors"
              style={{
                backgroundColor: '#0071e3',
                color: '#ffffff',
                textDecoration: 'none',
              }}
              onMouseEnter={(e) =>
                ((e.currentTarget as HTMLElement).style.backgroundColor = '#0066cc')
              }
              onMouseLeave={(e) =>
                ((e.currentTarget as HTMLElement).style.backgroundColor = '#0071e3')
              }
            >
              예술의전당 공식 페이지에서 보기
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path
                  d="M2 7H12M8 3L12 7L8 11"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </a>
          )}

          {/* Crawled at */}
          <p className="text-center text-[11px]" style={{ color: '#86868b' }}>
            데이터 수집:{' '}
            {new Date(concert.crawled_at).toLocaleDateString('ko-KR', {
              year: 'numeric',
              month: 'long',
              day: 'numeric',
            })}
          </p>
        </div>
      </main>
    </div>
  );
}
