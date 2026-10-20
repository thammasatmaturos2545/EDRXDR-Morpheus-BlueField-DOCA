import { NextResponse } from 'next/server';
import { requireHistoryAuth } from '@/lib/history-auth';
import { parseCopilotReview } from '@/lib/copilot-review';
import { open, realpath } from 'node:fs/promises';
import { constants } from 'node:fs';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
// Single reviewed report, never a path supplied by the browser. Disabled by default.
const REPORT = '/mnt/nexus-copilot-mQTssj/results/summary-eight-vone0xsh/result.json';
const headers = { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' };
function reply(body: unknown, status: number) { return NextResponse.json(body, { status, headers }); }
export async function GET(request: Request) {
  const auth = await requireHistoryAuth(request);
  if (auth) return auth;
  if (process.env.NEXUS_COPILOT_REVIEW !== 'saved-eight') return reply({ error: 'Copilot review disabled' }, 503);
  if (new URL(request.url).search) return reply({ error: 'Invalid parameter' }, 400);
  try {
    if (await realpath(REPORT) !== REPORT) throw Error('Unexpected report path');
    const file = await open(REPORT, constants.O_RDONLY | constants.O_NOFOLLOW);
    try {
      const info = await file.stat();
      if (!info.isFile() || info.size > 256 * 1024) throw Error('Report limit');
      const buffer = Buffer.alloc(256 * 1024 + 1);
      let offset = 0;
      for (;;) {
        const { bytesRead } = await file.read(buffer, offset, buffer.length - offset, null);
        offset += bytesRead;
        if (!bytesRead || offset === buffer.length) break;
      }
      if (offset > 256 * 1024) throw Error('Report limit');
      return reply(parseCopilotReview(JSON.parse(buffer.subarray(0, offset).toString('utf8'))), 200);
    } finally { await file.close(); }
  } catch { return reply({ error: 'Saved Copilot review unavailable' }, 503); }
}
