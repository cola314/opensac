'use client';

import React from 'react';
import Link from 'next/link';
import { truncateText, highlightText, formatDateRange } from '@/lib/utils';

export interface Concert {
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

interface ConcertCardProps {
  concert: Concert;
  query?: string;
  onClick?: (concert: Concert) => void;
}

function SaleBadge({ state }: { state?: string | null }) {
  if (!state) return null;

  const isOnSale =
    state.includes('예매') ||
    state.includes('판매') ||
    state.includes('오픈');
  const isUpcoming =
    state.includes('예정') || state.includes('준비') || state.includes('대기');

  if (isOnSale) {
    return (
      <span
        className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold tracking-wide"
        style={{
          backgroundColor: 'rgba(0, 113, 227, 0.1)',
          color: '#0071e3',
          border: '1px solid rgba(0, 113, 227, 0.2)',
        }}
      >
        예매중
      </span>
    );
  }

  if (isUpcoming) {
    return (
      <span
        className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold tracking-wide"
        style={{
          backgroundColor: 'rgba(110, 110, 115, 0.1)',
          color: '#6e6e73',
          border: '1px solid rgba(110, 110, 115, 0.2)',
        }}
      >
        예매예정
      </span>
    );
  }

  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold tracking-wide"
      style={{
        backgroundColor: 'rgba(110, 110, 115, 0.08)',
        color: '#86868b',
        border: '1px solid rgba(110, 110, 115, 0.15)',
      }}
    >
      {state}
    </span>
  );
}

export default function ConcertCard({ concert, query, onClick }: ConcertCardProps) {
  const programPreview = concert.detail_text
    ? truncateText(
        concert.detail_text
          .replace(/&amp;/g, '&')
          .replace(/&lt;/g, '<')
          .replace(/&gt;/g, '>')
          .replace(/&quot;/g, '"')
          .replace(/&#39;/g, "'")
          .replace(/&nbsp;/g, ' ')
          .replace(/&#\d+;/g, '')
          .replace(/<[^>]+>/g, ''),
        100
      )
    : null;

  const dateRange = formatDateRange(concert.begin_date, concert.end_date);

  const handleClick = (e: React.MouseEvent) => {
    if (onClick) {
      e.preventDefault();
      onClick(concert);
    }
  };

  return (
    <Link
      href={`/concerts/${concert.sn}`}
      onClick={handleClick}
      className="group block"
      style={{ textDecoration: 'none' }}
    >
      <article
        className="flex flex-col gap-2 px-4 py-4 rounded-2xl transition-all duration-200 cursor-pointer"
        style={{
          backgroundColor: '#ffffff',
          border: '1px solid #d2d2d7',
        }}
        onMouseEnter={(e) => {
          (e.currentTarget as HTMLElement).style.backgroundColor = '#f5f5f7';
          (e.currentTarget as HTMLElement).style.borderColor = '#86868b';
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLElement).style.backgroundColor = '#ffffff';
          (e.currentTarget as HTMLElement).style.borderColor = '#d2d2d7';
        }}
      >
        {/* Top row: time + badges */}
        <div className="flex items-center gap-2 flex-wrap">
          {concert.playtime && (
            <span
              className="text-[13px] font-semibold tabular-nums"
              style={{ color: '#0071e3' }}
            >
              {concert.playtime}
            </span>
          )}
          {dateRange && (
            <span className="text-[12px]" style={{ color: '#6e6e73' }}>
              {dateRange}
            </span>
          )}
          <div className="ml-auto">
            <SaleBadge state={concert.sale_state} />
          </div>
        </div>

        {/* Title */}
        <h3
          className="text-[15px] font-semibold leading-snug"
          style={{ color: '#1d1d1f', letterSpacing: '-0.2px' }}
        >
          {query ? highlightText(concert.title, query) : concert.title}
        </h3>

        {/* Place */}
        {concert.place_name && (
          <div className="flex items-center gap-1">
            <svg
              width="12"
              height="12"
              viewBox="0 0 12 12"
              fill="none"
              style={{ flexShrink: 0, color: '#86868b' }}
            >
              <path
                d="M6 1C4.07 1 2.5 2.57 2.5 4.5C2.5 7.25 6 11 6 11C6 11 9.5 7.25 9.5 4.5C9.5 2.57 7.93 1 6 1ZM6 5.75C5.31 5.75 4.75 5.19 4.75 4.5C4.75 3.81 5.31 3.25 6 3.25C6.69 3.25 7.25 3.81 7.25 4.5C7.25 5.19 6.69 5.75 6 5.75Z"
                fill="currentColor"
              />
            </svg>
            <span className="text-[13px]" style={{ color: '#6e6e73' }}>
              {concert.place_name}
            </span>
          </div>
        )}

        {/* Program preview */}
        {programPreview && (
          <p
            className="text-[13px] leading-relaxed"
            style={{ color: '#6e6e73' }}
          >
            {query ? highlightText(programPreview, query) : programPreview}
          </p>
        )}

        {/* Price */}
        {concert.price_info && (
          <p
            className="text-[13px] font-medium"
            style={{ color: '#424245' }}
          >
            {concert.price_info.length > 60
              ? concert.price_info.slice(0, 60) + '…'
              : concert.price_info}
          </p>
        )}
      </article>
    </Link>
  );
}
