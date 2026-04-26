'use client';

import Link from 'next/link';
import { useState, type ReactNode } from 'react';

// 뒤로가기 링크 - hover 시 색상 변경
export function BackLink({ href, children }: { href: string; children: ReactNode }) {
  const [hovered, setHovered] = useState(false);
  return (
    <Link
      href={href}
      className="inline-flex items-center gap-1.5 mb-6 text-[14px] font-medium transition-colors"
      style={{ color: hovered ? '#ffffff' : '#6e6e73', textDecoration: 'none' }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {children}
    </Link>
  );
}

// 외부 링크 버튼 - hover 시 배경색 변경
export function ExternalLinkButton({ href, children }: { href: string; children: ReactNode }) {
  const [hovered, setHovered] = useState(false);
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center justify-center gap-2 w-full py-3 rounded-full text-[15px] font-semibold transition-colors"
      style={{
        backgroundColor: hovered ? '#0077ED' : '#0071e3',
        color: '#ffffff',
        textDecoration: 'none',
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {children}
    </a>
  );
}
