import { NextRequest } from 'next/server';
import { verifyPassword, createSessionCookie } from '@/lib/admin-auth';

export const dynamic = 'force-dynamic';

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => ({}));
  const { password } = body;

  if (!password || !verifyPassword(password)) {
    return Response.json({ error: 'Invalid password' }, { status: 401 });
  }

  const cookie = createSessionCookie();
  const response = Response.json({ ok: true });
  response.headers.set(
    'Set-Cookie',
    `${cookie.name}=${cookie.value}; Max-Age=${cookie.maxAge}; Path=${cookie.path}; HttpOnly; SameSite=${cookie.sameSite}`
  );
  return response;
}
