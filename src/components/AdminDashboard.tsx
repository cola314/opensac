'use client';

import { useState, useEffect, useCallback } from 'react';

interface ConcertItem {
  sn: string;
  title: string;
  placeName: string;
  processed: boolean;
  programCount: number;
  hasDetailText: boolean;
}

interface CalendarData {
  year: number;
  month: number;
  dates: Record<string, ConcertItem[]>;
  stats: { total: number; processed: number; pending: number };
}

export default function AdminDashboard() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [data, setData] = useState<CalendarData | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [selectedSns, setSelectedSns] = useState<Set<string>>(new Set());
  const [processing, setProcessing] = useState(false);
  const [processResult, setProcessResult] = useState<string | null>(null);

  const fetchCalendar = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/admin/calendar?year=${year}&month=${month}`);
      if (res.status === 401) {
        window.location.reload();
        return;
      }
      const json: CalendarData = await res.json();
      setData(json);
    } catch (err) {
      console.error('Failed to fetch calendar:', err);
    } finally {
      setLoading(false);
    }
  }, [year, month]);

  useEffect(() => {
    fetchCalendar();
    setSelectedDate(null);
    setSelectedSns(new Set());
  }, [fetchCalendar]);

  function handlePrevMonth() {
    if (month === 1) { setYear(y => y - 1); setMonth(12); }
    else setMonth(m => m - 1);
  }

  function handleNextMonth() {
    if (month === 12) { setYear(y => y + 1); setMonth(1); }
    else setMonth(m => m + 1);
  }

  function toggleSn(sn: string) {
    setSelectedSns(prev => {
      const next = new Set(prev);
      if (next.has(sn)) next.delete(sn);
      else next.add(sn);
      return next;
    });
  }

  function selectAllForDate(date: string) {
    if (!data) return;
    const concerts = data.dates[date] || [];
    const unprocessed = concerts.filter(c => !c.processed && c.hasDetailText);
    const allSelected = unprocessed.every(c => selectedSns.has(c.sn));

    setSelectedSns(prev => {
      const next = new Set(prev);
      if (allSelected) {
        unprocessed.forEach(c => next.delete(c.sn));
      } else {
        unprocessed.forEach(c => next.add(c.sn));
      }
      return next;
    });
  }

  async function handleProcess() {
    if (selectedSns.size === 0) return;
    setProcessing(true);
    setProcessResult(null);

    try {
      const res = await fetch('/api/admin/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sns: Array.from(selectedSns) }),
      });
      const json = await res.json();
      if (res.ok) {
        setProcessResult(`${json.processed}건 처리 완료 (프로그램 ${json.totalPrograms}개 추출)`);
        setSelectedSns(new Set());
        await fetchCalendar();
      } else {
        setProcessResult(`오류: ${json.error || json.message}`);
      }
    } catch (err) {
      setProcessResult(`오류: ${String(err)}`);
    } finally {
      setProcessing(false);
    }
  }

  // Build calendar grid
  const firstDay = new Date(year, month - 1, 1).getDay(); // 0=Sun
  const daysInMonth = new Date(year, month, 0).getDate();
  const calendarDays: Array<{ day: number; dateStr: string } | null> = [];
  for (let i = 0; i < firstDay; i++) calendarDays.push(null);
  for (let d = 1; d <= daysInMonth; d++) {
    const mm = String(month).padStart(2, '0');
    const dd = String(d).padStart(2, '0');
    calendarDays.push({ day: d, dateStr: `${year}.${mm}.${dd}` });
  }

  const selectedConcerts = selectedDate && data ? (data.dates[selectedDate] || []) : [];

  return (
    <div className="min-h-screen" style={{ backgroundColor: '#f5f5f7' }}>
      {/* Header */}
      <header
        className="sticky top-0 z-50"
        style={{
          backgroundColor: 'rgba(255,255,255,0.85)',
          backdropFilter: 'blur(20px) saturate(180%)',
          WebkitBackdropFilter: 'blur(20px) saturate(180%)',
          borderBottom: '1px solid rgba(210,210,215,0.5)',
        }}
      >
        <div className="mx-auto flex items-center justify-between" style={{ maxWidth: '960px', padding: '12px 20px' }}>
          <span className="text-[15px] font-semibold" style={{ color: '#1d1d1f', letterSpacing: '-0.2px' }}>
            Admin
          </span>

          <div className="flex items-center gap-3">
            <button
              onClick={handlePrevMonth}
              className="w-8 h-8 rounded-full flex items-center justify-center"
              style={{ border: '1px solid #d2d2d7', color: '#1d1d1f' }}
            >
              <svg width="8" height="13" viewBox="0 0 8 13" fill="none">
                <path d="M7 1L1 6.5L7 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
            <span className="text-[17px] font-semibold min-w-[100px] text-center" style={{ color: '#1d1d1f' }}>
              {year}년 {month}월
            </span>
            <button
              onClick={handleNextMonth}
              className="w-8 h-8 rounded-full flex items-center justify-center"
              style={{ border: '1px solid #d2d2d7', color: '#1d1d1f' }}
            >
              <svg width="8" height="13" viewBox="0 0 8 13" fill="none">
                <path d="M1 1L7 6.5L1 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          </div>

          {data && (
            <div className="flex items-center gap-3 text-[13px]" style={{ color: '#6e6e73' }}>
              <span>{data.stats.total}건</span>
              <span style={{ color: '#34c759' }}>{data.stats.processed} 완료</span>
              <span style={{ color: '#0071e3' }}>{data.stats.pending} 대기</span>
            </div>
          )}
        </div>
      </header>

      <main className="mx-auto" style={{ maxWidth: '960px', padding: '24px 20px 120px' }}>
        {loading ? (
          <div className="flex items-center justify-center py-24">
            <span className="text-[15px] animate-pulse" style={{ color: '#6e6e73' }}>불러오는 중...</span>
          </div>
        ) : (
          <div className="flex gap-6" style={{ flexWrap: 'wrap' }}>
            {/* Calendar Grid */}
            <div style={{ flex: '1 1 480px', minWidth: '320px' }}>
              <div
                className="rounded-2xl overflow-hidden"
                style={{ backgroundColor: '#ffffff', border: '1px solid #d2d2d7' }}
              >
                {/* Weekday headers */}
                <div className="grid grid-cols-7 text-center text-[12px] font-medium py-2" style={{ color: '#86868b', borderBottom: '1px solid #e8e8ed' }}>
                  {['일', '월', '화', '수', '목', '금', '토'].map(d => (
                    <div key={d}>{d}</div>
                  ))}
                </div>

                {/* Days */}
                <div className="grid grid-cols-7">
                  {calendarDays.map((cell, i) => {
                    if (!cell) return <div key={`e${i}`} style={{ padding: '8px', minHeight: '72px' }} />;

                    const concerts = data?.dates[cell.dateStr] || [];
                    const total = concerts.length;
                    const processedCount = concerts.filter(c => c.processed).length;
                    const isSelected = selectedDate === cell.dateStr;
                    const isToday = cell.dateStr === `${now.getFullYear()}.${String(now.getMonth() + 1).padStart(2, '0')}.${String(now.getDate()).padStart(2, '0')}`;

                    let dotColor = 'transparent';
                    if (total > 0) {
                      if (processedCount === total) dotColor = '#34c759';
                      else if (processedCount > 0) dotColor = '#ff9f0a';
                      else dotColor = '#0071e3';
                    }

                    return (
                      <button
                        key={cell.dateStr}
                        onClick={() => setSelectedDate(isSelected ? null : cell.dateStr)}
                        className="flex flex-col items-center gap-1 transition-colors"
                        style={{
                          padding: '8px 4px',
                          minHeight: '72px',
                          backgroundColor: isSelected ? 'rgba(0,113,227,0.08)' : 'transparent',
                          borderRadius: '0',
                          border: 'none',
                          cursor: total > 0 ? 'pointer' : 'default',
                        }}
                      >
                        <span
                          className="text-[14px] font-medium flex items-center justify-center"
                          style={{
                            color: isToday ? '#0071e3' : total > 0 ? '#1d1d1f' : '#86868b',
                            width: '28px',
                            height: '28px',
                            borderRadius: '50%',
                            backgroundColor: isToday ? 'rgba(0,113,227,0.1)' : 'transparent',
                          }}
                        >
                          {cell.day}
                        </span>
                        {total > 0 && (
                          <>
                            <span className="text-[11px] font-medium" style={{ color: '#6e6e73' }}>
                              {total}건
                            </span>
                            <div
                              style={{
                                width: '6px',
                                height: '6px',
                                borderRadius: '50%',
                                backgroundColor: dotColor,
                              }}
                            />
                          </>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Legend */}
              <div className="flex items-center gap-4 mt-3 text-[12px]" style={{ color: '#6e6e73' }}>
                <span className="flex items-center gap-1">
                  <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#34c759', display: 'inline-block' }} />
                  전부 완료
                </span>
                <span className="flex items-center gap-1">
                  <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#ff9f0a', display: 'inline-block' }} />
                  일부 완료
                </span>
                <span className="flex items-center gap-1">
                  <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#0071e3', display: 'inline-block' }} />
                  미처리
                </span>
              </div>
            </div>

            {/* Concert list panel */}
            <div style={{ flex: '1 1 360px', minWidth: '280px' }}>
              {selectedDate ? (
                <div
                  className="rounded-2xl overflow-hidden"
                  style={{ backgroundColor: '#ffffff', border: '1px solid #d2d2d7' }}
                >
                  <div className="flex items-center justify-between px-4 py-3" style={{ borderBottom: '1px solid #e8e8ed' }}>
                    <h3 className="text-[15px] font-semibold" style={{ color: '#1d1d1f' }}>
                      {selectedDate}
                    </h3>
                    {selectedConcerts.some(c => !c.processed && c.hasDetailText) && (
                      <button
                        onClick={() => selectAllForDate(selectedDate)}
                        className="text-[13px] font-medium"
                        style={{ color: '#0071e3', border: 'none', background: 'none', cursor: 'pointer' }}
                      >
                        미처리 전체선택
                      </button>
                    )}
                  </div>

                  <div className="flex flex-col">
                    {selectedConcerts.length === 0 ? (
                      <div className="px-4 py-8 text-center text-[14px]" style={{ color: '#6e6e73' }}>
                        이 날짜에 공연이 없습니다
                      </div>
                    ) : (
                      selectedConcerts.map((concert) => (
                        <label
                          key={concert.sn}
                          className="flex items-start gap-3 px-4 py-3 transition-colors"
                          style={{
                            borderBottom: '1px solid #f0f0f0',
                            cursor: concert.hasDetailText ? 'pointer' : 'default',
                            backgroundColor: selectedSns.has(concert.sn) ? 'rgba(0,113,227,0.04)' : 'transparent',
                          }}
                        >
                          <input
                            type="checkbox"
                            checked={selectedSns.has(concert.sn)}
                            onChange={() => toggleSn(concert.sn)}
                            disabled={!concert.hasDetailText}
                            className="mt-1"
                            style={{ accentColor: '#0071e3', width: '16px', height: '16px' }}
                          />
                          <div className="flex-1 min-w-0">
                            <p
                              className="text-[14px] font-medium truncate"
                              style={{ color: '#1d1d1f' }}
                            >
                              {concert.title}
                            </p>
                            <div className="flex items-center gap-2 mt-1">
                              {concert.placeName && (
                                <span className="text-[12px]" style={{ color: '#6e6e73' }}>
                                  {concert.placeName}
                                </span>
                              )}
                              {concert.processed ? (
                                <span
                                  className="text-[11px] font-medium px-1.5 py-0.5 rounded-full"
                                  style={{ backgroundColor: 'rgba(52,199,89,0.1)', color: '#34c759' }}
                                >
                                  {concert.programCount}곡 추출
                                </span>
                              ) : concert.hasDetailText ? (
                                <span
                                  className="text-[11px] font-medium px-1.5 py-0.5 rounded-full"
                                  style={{ backgroundColor: 'rgba(0,113,227,0.08)', color: '#0071e3' }}
                                >
                                  대기
                                </span>
                              ) : (
                                <span
                                  className="text-[11px] font-medium px-1.5 py-0.5 rounded-full"
                                  style={{ backgroundColor: '#f5f5f7', color: '#86868b' }}
                                >
                                  텍스트 없음
                                </span>
                              )}
                            </div>
                          </div>
                        </label>
                      ))
                    )}
                  </div>
                </div>
              ) : (
                <div
                  className="rounded-2xl flex items-center justify-center"
                  style={{
                    backgroundColor: '#ffffff',
                    border: '1px solid #d2d2d7',
                    minHeight: '200px',
                  }}
                >
                  <p className="text-[14px]" style={{ color: '#86868b' }}>
                    날짜를 선택하세요
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {/* Floating action bar */}
      {selectedSns.size > 0 && (
        <div
          className="fixed bottom-0 left-0 right-0 z-50"
          style={{
            backgroundColor: 'rgba(255,255,255,0.9)',
            backdropFilter: 'blur(20px) saturate(180%)',
            WebkitBackdropFilter: 'blur(20px) saturate(180%)',
            borderTop: '1px solid rgba(210,210,215,0.5)',
          }}
        >
          <div className="mx-auto flex items-center justify-between" style={{ maxWidth: '960px', padding: '12px 20px' }}>
            <div className="flex items-center gap-3">
              <span className="text-[14px] font-medium" style={{ color: '#1d1d1f' }}>
                {selectedSns.size}건 선택됨
              </span>
              <span className="text-[13px]" style={{ color: '#6e6e73' }}>
                예상 비용: ~${(selectedSns.size * 0.0004).toFixed(4)}
              </span>
            </div>

            {processResult && (
              <span className="text-[13px] font-medium" style={{ color: processResult.startsWith('오류') ? '#ff3b30' : '#34c759' }}>
                {processResult}
              </span>
            )}

            <div className="flex items-center gap-2">
              <button
                onClick={() => { setSelectedSns(new Set()); setProcessResult(null); }}
                className="px-4 py-2 rounded-full text-[13px] font-medium"
                style={{ border: '1px solid #d2d2d7', color: '#1d1d1f', background: 'none', cursor: 'pointer' }}
              >
                취소
              </button>
              <button
                onClick={handleProcess}
                disabled={processing}
                className="px-5 py-2 rounded-full text-[13px] font-semibold"
                style={{
                  backgroundColor: processing ? '#86868b' : '#0071e3',
                  color: '#ffffff',
                  border: 'none',
                  cursor: processing ? 'default' : 'pointer',
                }}
              >
                {processing ? '처리 중...' : `${selectedSns.size}건 처리 실행`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
