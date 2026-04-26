import { cookies } from 'next/headers';
import crypto from 'crypto';

const COOKIE_NAME = 'admin_session';
const SESSION_MAX_AGE = 60 * 60 * 24 * 7; // 7 days

function getSessionToken(): string {
  const password = process.env.ADMIN_PASSWORD || '';
  return crypto.createHash('sha256').update(`opensac-admin:${password}`).digest('hex').slice(0, 32);
}

export async function isAuthenticated(): Promise<boolean> {
  const password = process.env.ADMIN_PASSWORD;
  if (!password) return false;

  const cookieStore = await cookies();
  const session = cookieStore.get(COOKIE_NAME);
  return session?.value === getSessionToken();
}

export function verifyPassword(input: string): boolean {
  const password = process.env.ADMIN_PASSWORD;
  if (!password) return false;
  return input === password;
}

export function createSessionCookie(): { name: string; value: string; maxAge: number; path: string; httpOnly: boolean; sameSite: 'lax' } {
  return {
    name: COOKIE_NAME,
    value: getSessionToken(),
    maxAge: SESSION_MAX_AGE,
    path: '/',
    httpOnly: true,
    sameSite: 'lax',
  };
}

export async function checkAdminAuth(): Promise<Response | null> {
  const authenticated = await isAuthenticated();
  if (!authenticated) {
    return Response.json({ error: 'Unauthorized' }, { status: 401 });
  }
  return null;
}
