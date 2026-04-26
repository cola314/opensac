import React from 'react';

const WEEKDAY_MAP: Record<string, string> = {
  월: '월요일',
  화: '화요일',
  수: '수요일',
  목: '목요일',
  금: '금요일',
  토: '토요일',
  일: '일요일',
};

export function getWeekdayName(short: string): string {
  return WEEKDAY_MAP[short] ?? short;
}

export function formatDate(dateStr: string, weekday?: string): string {
  // dateStr: "2026.05.22"
  const parts = dateStr.split('.');
  if (parts.length < 3) return dateStr;
  const month = parseInt(parts[1], 10);
  const day = parseInt(parts[2], 10);
  const wd = weekday ? getWeekdayName(weekday) : '';
  return wd ? `${month}월 ${day}일 ${wd}` : `${month}월 ${day}일`;
}

export function formatDateRange(beginDate: string, endDate?: string | null): string {
  if (!endDate || endDate === beginDate) return '';
  const beginParts = beginDate.split('.');
  const endParts = endDate.split('.');
  if (beginParts.length < 3 || endParts.length < 3) return '';
  const bMonth = parseInt(beginParts[1], 10);
  const bDay = parseInt(beginParts[2], 10);
  const eMonth = parseInt(endParts[1], 10);
  const eDay = parseInt(endParts[2], 10);
  if (bMonth === eMonth) {
    return `${bMonth}월 ${bDay}일 – ${eDay}일`;
  }
  return `${bMonth}월 ${bDay}일 – ${eMonth}월 ${eDay}일`;
}

export function cleanDetailText(text: string | null | undefined): string {
  if (!text) return '';

  // Decode common HTML entities
  let cleaned = text
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&nbsp;/g, ' ')
    .replace(/&hellip;/g, '…')
    .replace(/&#\d+;/g, '');

  // Strip remaining HTML tags
  cleaned = cleaned.replace(/<[^>]+>/g, '');

  // Normalize whitespace — collapse runs of spaces but preserve newlines
  cleaned = cleaned
    .split('\n')
    .map((line) => line.replace(/\s{2,}/g, ' ').trim())
    .filter((line) => line.length > 0)
    .join('\n');

  // Insert line breaks at logical points if there are none
  if (!cleaned.includes('\n')) {
    // Break before common section markers
    cleaned = cleaned
      .replace(/(▶|◆|●|■|□|◇|▷|※|○|【|】|\[|\])/g, '\n$1')
      .replace(/([。.!?！？])\s+([가-힣A-Z])/g, '$1\n$2')
      .replace(/(프로그램|출연|지휘|협연|작품|Program|PROGRAM)/g, '\n$1');
  }

  // Remove leading/trailing blank lines
  return cleaned.trim();
}

export function truncateText(text: string, maxLen: number): string {
  const single = text.replace(/\n/g, ' ').replace(/\s{2,}/g, ' ').trim();
  if (single.length <= maxLen) return single;
  return single.slice(0, maxLen).trimEnd() + '…';
}

export function highlightText(text: string, query: string): React.ReactNode {
  if (!query || !query.trim()) return text;

  const terms = query
    .trim()
    .split(/\s+/)
    .filter((t) => t.length > 0)
    .map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));

  if (terms.length === 0) return text;

  const pattern = new RegExp(`(${terms.join('|')})`, 'gi');
  const parts = text.split(pattern);

  return React.createElement(
    React.Fragment,
    null,
    ...parts.map((part, i) => {
      if (pattern.test(part)) {
        return React.createElement(
          'mark',
          {
            key: i,
            style: {
              backgroundColor: 'rgba(0, 113, 227, 0.15)',
              color: '#0071e3',
              borderRadius: '2px',
              padding: '0 1px',
              fontWeight: 600,
            },
          },
          part
        );
      }
      return part;
    })
  );
}
