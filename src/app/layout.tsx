import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
  weight: ['300', '400', '500', '600', '700'],
});

export const metadata: Metadata = {
  title: '예술의전당 클래식 공연 검색 | OpenSAC',
  description: '예술의전당 클래식 공연 정보를 쉽게 검색하고 찾아보세요.',
  keywords: '예술의전당, 클래식, 공연, 콘서트, 오페라, SAC',
  openGraph: {
    title: '예술의전당 클래식 공연 검색',
    description: '예술의전당 클래식 공연 정보를 쉽게 검색하고 찾아보세요.',
    locale: 'ko_KR',
    type: 'website',
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" className={`${inter.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col bg-white text-[#1d1d1f]">
        {children}
      </body>
    </html>
  );
}
