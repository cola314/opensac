import { NextRequest } from 'next/server';
import { checkAdminAuth } from '@/lib/admin-auth';
import { sqlite } from '@/db/index';
import { runPipeline } from '@/lib/ml-pipeline';

export const dynamic = 'force-dynamic';

export async function POST(request: NextRequest) {
  const authError = await checkAdminAuth();
  if (authError) return authError;

  const body = await request.json().catch(() => ({}));
  const sns: string[] = body.sns;

  if (!sns || !Array.isArray(sns) || sns.length === 0) {
    return Response.json({ error: 'sns array required' }, { status: 400 });
  }

  if (sns.length > 200) {
    return Response.json({ error: 'Too many items (max 200)' }, { status: 400 });
  }

  const placeholders = sns.map(() => '?').join(',');
  const concerts = sqlite.prepare(
    `SELECT sn, title, detail_text FROM concerts WHERE sn IN (${placeholders})`
  ).all(...sns) as Array<{ sn: string; title: string; detail_text: string | null }>;

  const items = concerts
    .filter((c) => c.detail_text)
    .map((c) => ({ sn: c.sn, title: c.title, detail_text: c.detail_text! }));

  if (items.length === 0) {
    return Response.json({ error: 'No concerts with detail text found' }, { status: 404 });
  }

  try {
    const results = await runPipeline(items);

    const deleteStmt = sqlite.prepare('DELETE FROM programs WHERE concert_sn = ?');
    const insertStmt = sqlite.prepare(
      'INSERT INTO programs (concert_sn, composer, piece, created_at) VALUES (?, ?, ?, ?)'
    );
    const now = new Date().toISOString();

    const upsertAll = sqlite.transaction(() => {
      for (const result of results) {
        deleteStmt.run(result.sn);
        for (const program of result.programs) {
          insertStmt.run(result.sn, program.composer, program.piece, now);
        }
      }
    });
    upsertAll();

    const totalPrograms = results.reduce((sum, r) => sum + r.programs.length, 0);

    return Response.json({
      ok: true,
      processed: results.length,
      totalPrograms,
      errors: results.filter((r) => r.error).length,
    });
  } catch (error) {
    console.error('Pipeline error:', error);
    return Response.json(
      { error: 'Pipeline failed', message: String(error) },
      { status: 500 }
    );
  }
}
