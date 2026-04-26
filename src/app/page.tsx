import ConcertHome from '@/components/ConcertHome';

async function getInitialData(year: number, month: number) {
  try {
    const params = new URLSearchParams({
      year: String(year),
      month: String(month),
    });
    // Use absolute URL for server-side fetch
    const baseUrl =
      process.env.NEXT_PUBLIC_BASE_URL ||
      (process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : 'http://localhost:3000');

    const res = await fetch(`${baseUrl}/api/concerts?${params.toString()}`, {
      cache: 'no-store',
    });

    if (!res.ok) throw new Error('Failed to fetch initial data');
    return res.json();
  } catch (err) {
    console.error('Server-side fetch failed:', err);
    return { total: 0, places: [], dates: {} };
  }
}

export default async function HomePage() {
  const now = new Date();
  const year = now.getFullYear();
  const month = now.getMonth() + 1;

  const initialData = await getInitialData(year, month);

  return (
    <ConcertHome
      initialData={initialData}
      initialYear={year}
      initialMonth={month}
    />
  );
}
