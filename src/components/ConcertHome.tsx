'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import ConcertCard, { Concert } from './ConcertCard';
import { formatDate, getWeekdayName } from '@/lib/utils';

interface Place {
  place_name: string;
  count: number;
}

interface ApiResponse {
  total: number;
  places: Place[];
  dates: Record<string, Concert[]>;
}

interface ConcertHomeProps {
  initialData: ApiResponse;
  initialYear: number;
  initialMonth: number;
}

function MonthNav({
  year,
  month,
  onPrev,
  onNext,
}: {
  year: number;
  month: number;
  onPrev: () => void;
  onNext: () => void;
}) {
  return (
    <div className="flex items-center gap-3">
      <button
        onClick={onPrev}
        className="w-8 h-8 rounded-full flex items-center justify-center transition-colors"
        style={{ border: '1px solid #d2d2d7', color: '#1d1d1f' }}
        onMouseEnter={(e) =>
          ((e.currentTarget as HTMLElement).style.backgroundColor = '#f5f5f7')
        }
        onMouseLeave={(e) =>
          ((e.currentTarget as HTMLElement).style.backgroundColor = 'transparent')
        }
        aria-label="이전 달"
      >
        <svg width="8" height="13" viewBox="0 0 8 13" fill="none">
          <path
            d="M7 1L1 6.5L7 12"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>
      <span
        className="text-[17px] font-semibold min-w-[100px] text-center"
        style={{ color: '#1d1d1f', letterSpacing: '-0.3px' }}
      >
        {year}년 {month}월
      </span>
      <button
        onClick={onNext}
        className="w-8 h-8 rounded-full flex items-center justify-center transition-colors"
        style={{ border: '1px solid #d2d2d7', color: '#1d1d1f' }}
        onMouseEnter={(e) =>
          ((e.currentTarget as HTMLElement).style.backgroundColor = '#f5f5f7')
        }
        onMouseLeave={(e) =>
          ((e.currentTarget as HTMLElement).style.backgroundColor = 'transparent')
        }
        aria-label="다음 달"
      >
        <svg width="8" height="13" viewBox="0 0 8 13" fill="none">
          <path
            d="M1 1L7 6.5L1 12"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>
    </div>
  );
}

function SearchBar({
  value,
  onChange,
  compact,
  onFocusChange,
}: {
  value: string;
  onChange: (v: string) => void;
  compact?: boolean;
  onFocusChange?: (focused: boolean) => void;
}) {
  return (
    <div className="relative" style={{ maxWidth: compact ? '300px' : '480px', width: '100%' }}>
      <div
        className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none"
        style={{ color: '#86868b' }}
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <circle cx="6.5" cy="6.5" r="5" stroke="currentColor" strokeWidth="1.5" />
          <path
            d="M10.5 10.5L14 14"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
        </svg>
      </div>
      <input
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="공연명, 연주자, 작곡가 검색"
        className="w-full pl-9 pr-4 transition-all duration-200"
        style={{
          height: compact ? '36px' : '44px',
          borderRadius: '980px',
          border: '1px solid #d2d2d7',
          backgroundColor: '#ffffff',
          color: '#1d1d1f',
          fontSize: compact ? '13px' : '15px',
          fontFamily: 'inherit',
          outline: 'none',
          paddingLeft: '36px',
          paddingRight: '16px',
        }}
        onFocus={(e) => {
          (e.currentTarget as HTMLElement).style.borderColor = '#0071e3';
          (e.currentTarget as HTMLElement).style.boxShadow =
            '0 0 0 3px rgba(0, 113, 227, 0.15)';
          onFocusChange?.(true);
        }}
        onBlur={(e) => {
          (e.currentTarget as HTMLElement).style.borderColor = '#d2d2d7';
          (e.currentTarget as HTMLElement).style.boxShadow = 'none';
          // blur 시에는 searchFocused를 false로 하지 않음 — compact 유지가 더 나은 UX
        }}
      />
      {value && (
        <button
          onClick={() => onChange('')}
          className="absolute right-3 top-1/2 -translate-y-1/2"
          style={{ color: '#86868b' }}
          aria-label="검색어 지우기"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <circle cx="7" cy="7" r="6.5" fill="#86868b" fillOpacity="0.2" />
            <path
              d="M4.5 4.5L9.5 9.5M9.5 4.5L4.5 9.5"
              stroke="#6e6e73"
              strokeWidth="1.3"
              strokeLinecap="round"
            />
          </svg>
        </button>
      )}
    </div>
  );
}

function EmptyState() {
  return (
    <div
      className="flex flex-col items-center justify-center py-24 gap-4"
      style={{ color: '#6e6e73' }}
    >
      <svg width="48" height="48" viewBox="0 0 48 48" fill="none" opacity="0.4">
        <path
          d="M24 4C12.95 4 4 12.95 4 24C4 35.05 12.95 44 24 44C35.05 44 44 35.05 44 24C44 12.95 35.05 4 24 4Z"
          stroke="currentColor"
          strokeWidth="2"
          fill="none"
        />
        <path
          d="M18 22C18 20.34 19.34 19 21 19H27C28.66 19 30 20.34 30 22V30H18V22Z"
          stroke="currentColor"
          strokeWidth="1.5"
          fill="none"
        />
        <path
          d="M21 19V17C21 15.34 22.34 14 24 14C25.66 14 27 15.34 27 17V19"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
        />
        <path d="M20 30V34" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        <path d="M28 30V34" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        <path
          d="M14 26C14 26 16 24 18 26C20 28 22 26 24 26C26 26 28 28 30 26C32 24 34 26 34 26"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
        />
      </svg>
      <div className="text-center">
        <p
          className="text-[17px] font-semibold"
          style={{ color: '#1d1d1f', marginBottom: '4px' }}
        >
          검색 결과가 없습니다
        </p>
        <p className="text-[14px]" style={{ color: '#6e6e73' }}>
          다른 검색어나 필터를 시도해보세요
        </p>
      </div>
    </div>
  );
}

export default function ConcertHome({
  initialData,
  initialYear,
  initialMonth,
}: ConcertHomeProps) {
  const [year, setYear] = useState(initialYear);
  const [month, setMonth] = useState(initialMonth);
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [selectedPlace, setSelectedPlace] = useState<string | null>(null);
  const [data, setData] = useState<ApiResponse>(initialData);
  const [loading, setLoading] = useState(false);
  const [heroCompact, setHeroCompact] = useState(false);
  const [searchFocused, setSearchFocused] = useState(false);

  const heroRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Scroll listener for hero compact mode
  useEffect(() => {
    const handleScroll = () => {
      const scrollY = window.scrollY;
      setHeroCompact(scrollY > 80);
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Also compact when there's a search query or search input is focused
  const isCompact = heroCompact || debouncedQuery.length > 0 || searchFocused;

  // Scroll to top when search is focused so sticky compact bar is visible
  useEffect(() => {
    if (searchFocused) {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }, [searchFocused]);

  // Debounce query
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setDebouncedQuery(query);
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query]);

  // Reset place filter when switching months
  const handlePrevMonth = useCallback(() => {
    setSelectedPlace(null);
    if (month === 1) {
      setYear((y) => y - 1);
      setMonth(12);
    } else {
      setMonth((m) => m - 1);
    }
  }, [month]);

  const handleNextMonth = useCallback(() => {
    setSelectedPlace(null);
    if (month === 12) {
      setYear((y) => y + 1);
      setMonth(1);
    } else {
      setMonth((m) => m + 1);
    }
  }, [month]);

  // Fetch data when filters change
  useEffect(() => {
    const controller = new AbortController();

    async function fetchData() {
      setLoading(true);
      try {
        const params = new URLSearchParams({
          year: String(year),
          month: String(month),
        });
        if (debouncedQuery) params.set('q', debouncedQuery);
        if (selectedPlace) params.set('place', selectedPlace);

        const res = await fetch(`/api/concerts?${params.toString()}`, {
          signal: controller.signal,
        });
        if (!res.ok) throw new Error('API error');
        const json: ApiResponse = await res.json();
        setData(json);
      } catch (err) {
        if ((err as Error).name !== 'AbortError') {
          console.error('Failed to fetch concerts:', err);
        }
      } finally {
        setLoading(false);
      }
    }

    fetchData();
    return () => controller.abort();
  }, [year, month, debouncedQuery, selectedPlace]);

  const sortedDates = Object.keys(data.dates).sort();

  // Build place filter options with counts from current results
  const placeCounts = new Map<string, number>();
  for (const concerts of Object.values(data.dates)) {
    for (const c of concerts) {
      if (c.place_name) {
        placeCounts.set(c.place_name, (placeCounts.get(c.place_name) ?? 0) + 1);
      }
    }
  }

  // All places from initial data for stable filter list, but counts from current results
  const allPlaces = data.places;

  return (
    <div className="min-h-screen" style={{ backgroundColor: '#ffffff' }}>
      {/* Sticky Nav / Compact Hero */}
      <header
        className="sticky top-0 z-50 transition-all duration-300"
        style={{
          backgroundColor: isCompact
            ? 'rgba(255,255,255,0.85)'
            : 'transparent',
          backdropFilter: isCompact ? 'blur(20px) saturate(180%)' : 'none',
          WebkitBackdropFilter: isCompact ? 'blur(20px) saturate(180%)' : 'none',
          borderBottom: isCompact ? '1px solid rgba(210,210,215,0.5)' : 'none',
        }}
      >
        <div
          className="mx-auto flex items-center gap-4 transition-all duration-300"
          style={{
            maxWidth: '960px',
            padding: isCompact ? '12px 20px' : '0 20px',
          }}
        >
          {isCompact && (
            <span
              className="text-[15px] font-semibold whitespace-nowrap"
              style={{ color: '#1d1d1f', letterSpacing: '-0.2px', flexShrink: 0 }}
            >
              예술의전당
            </span>
          )}
          {isCompact && (
            <SearchBar value={query} onChange={setQuery} compact onFocusChange={setSearchFocused} />
          )}
          {isCompact && (
            <div className="ml-auto">
              <MonthNav
                year={year}
                month={month}
                onPrev={handlePrevMonth}
                onNext={handleNextMonth}
              />
            </div>
          )}
        </div>
      </header>

      {/* Hero Section */}
      <section
        ref={heroRef}
        className="transition-all duration-500"
        style={{
          backgroundColor: '#000000',
          padding: isCompact ? '40px 20px 36px' : '72px 20px 60px',
          marginTop: isCompact ? '-56px' : '0',
        }}
      >
        <div className="mx-auto" style={{ maxWidth: '960px' }}>
          {!isCompact && (
            <>
              <p
                className="text-[13px] font-semibold uppercase tracking-widest mb-3"
                style={{ color: '#6e6e73', letterSpacing: '0.1em' }}
              >
                Seoul Arts Center
              </p>
              <h1
                className="font-semibold leading-tight mb-3"
                style={{
                  fontSize: 'clamp(32px, 5vw, 52px)',
                  color: '#ffffff',
                  letterSpacing: '-0.5px',
                  lineHeight: 1.07,
                }}
              >
                예술의전당
                <br />
                클래식 공연
              </h1>
              <p
                className="mb-8"
                style={{
                  color: '#6e6e73',
                  fontSize: '17px',
                  lineHeight: 1.47,
                  maxWidth: '400px',
                }}
              >
                콘서트홀, 오페라하우스, 리사이틀홀의<br />
                공연 일정을 한눈에 확인하세요.
              </p>
            </>
          )}

          <div className="flex flex-col gap-4">
            {!isCompact && (
              <SearchBar value={query} onChange={setQuery} onFocusChange={setSearchFocused} />
            )}
            {!isCompact && (
              <MonthNav
                year={year}
                month={month}
                onPrev={handlePrevMonth}
                onNext={handleNextMonth}
              />
            )}
          </div>
        </div>
      </section>

      {/* Filter Chips + Content */}
      <main style={{ backgroundColor: '#f5f5f7', minHeight: '60vh' }}>
        <div
          className="mx-auto"
          style={{ maxWidth: '960px', padding: '24px 20px 48px' }}
        >
          {/* Place filter chips */}
          {allPlaces.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-6">
              <button
                onClick={() => setSelectedPlace(null)}
                className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full text-[13px] font-medium transition-all duration-150"
                style={{
                  backgroundColor: selectedPlace === null ? '#1d1d1f' : '#ffffff',
                  color: selectedPlace === null ? '#ffffff' : '#1d1d1f',
                  border: `1px solid ${selectedPlace === null ? '#1d1d1f' : '#d2d2d7'}`,
                }}
              >
                전체
                <span
                  className="text-[11px] font-semibold px-1.5 py-0.5 rounded-full"
                  style={{
                    backgroundColor:
                      selectedPlace === null ? 'rgba(255,255,255,0.2)' : '#f5f5f7',
                    color: selectedPlace === null ? '#ffffff' : '#6e6e73',
                  }}
                >
                  {data.total}
                </span>
              </button>
              {allPlaces.map((p) => {
                const currentCount = placeCounts.get(p.place_name) ?? 0;
                const isActive = selectedPlace === p.place_name;
                return (
                  <button
                    key={p.place_name}
                    onClick={() =>
                      setSelectedPlace(isActive ? null : p.place_name)
                    }
                    className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full text-[13px] font-medium transition-all duration-150"
                    style={{
                      backgroundColor: isActive ? '#1d1d1f' : '#ffffff',
                      color: isActive ? '#ffffff' : '#1d1d1f',
                      border: `1px solid ${isActive ? '#1d1d1f' : '#d2d2d7'}`,
                    }}
                  >
                    {p.place_name}
                    <span
                      className="text-[11px] font-semibold px-1.5 py-0.5 rounded-full"
                      style={{
                        backgroundColor: isActive
                          ? 'rgba(255,255,255,0.2)'
                          : '#f5f5f7',
                        color: isActive ? '#ffffff' : '#6e6e73',
                      }}
                    >
                      {currentCount}
                    </span>
                  </button>
                );
              })}
            </div>
          )}

          {/* Results summary */}
          <div className="flex items-center justify-between mb-4">
            <p
              className="text-[13px]"
              style={{ color: '#6e6e73' }}
            >
              {loading ? (
                <span className="animate-pulse">불러오는 중…</span>
              ) : (
                <>
                  {debouncedQuery && (
                    <span className="font-semibold" style={{ color: '#1d1d1f' }}>
                      &ldquo;{debouncedQuery}&rdquo;{' '}
                    </span>
                  )}
                  총{' '}
                  <span className="font-semibold" style={{ color: '#1d1d1f' }}>
                    {data.total}
                  </span>
                  개 공연
                </>
              )}
            </p>
          </div>

          {/* Concert list grouped by date */}
          {loading ? (
            <div className="flex flex-col gap-6">
              {[1, 2, 3].map((i) => (
                <div key={i} className="animate-pulse">
                  <div
                    className="h-5 w-32 rounded mb-3"
                    style={{ backgroundColor: '#d2d2d7' }}
                  />
                  <div className="flex flex-col gap-3">
                    {[1, 2].map((j) => (
                      <div
                        key={j}
                        className="h-24 rounded-2xl"
                        style={{ backgroundColor: '#d2d2d7' }}
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : sortedDates.length === 0 ? (
            <EmptyState />
          ) : (
            <div className="flex flex-col gap-8">
              {sortedDates.map((dateStr) => {
                const concerts = data.dates[dateStr];
                const firstConcert = concerts[0];
                const weekday = firstConcert?.start_week ?? '';
                const formattedDate = formatDate(dateStr, weekday);

                return (
                  <section key={dateStr}>
                    {/* Date header */}
                    <div
                      className="flex items-center gap-3 mb-3 pb-2"
                      style={{ borderBottom: '1px solid #d2d2d7' }}
                    >
                      <h2
                        className="text-[15px] font-semibold"
                        style={{ color: '#1d1d1f', letterSpacing: '-0.1px' }}
                      >
                        {formattedDate}
                      </h2>
                      <span
                        className="text-[12px] font-medium px-2 py-0.5 rounded-full"
                        style={{
                          backgroundColor: '#e8e8ed',
                          color: '#6e6e73',
                        }}
                      >
                        {concerts.length}개
                      </span>
                    </div>

                    {/* Cards */}
                    <div className="flex flex-col gap-3">
                      {concerts.map((concert) => (
                        <ConcertCard
                          key={concert.sn}
                          concert={concert}
                          query={debouncedQuery}
                        />
                      ))}
                    </div>
                  </section>
                );
              })}
            </div>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer
        className="py-8 text-center"
        style={{ backgroundColor: '#f5f5f7', borderTop: '1px solid #d2d2d7' }}
      >
        <p className="text-[12px]" style={{ color: '#86868b' }}>
          데이터 출처:{' '}
          <a
            href="https://www.sac.or.kr"
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: '#0066cc' }}
          >
            예술의전당 공식 웹사이트
          </a>
        </p>
      </footer>
    </div>
  );
}
