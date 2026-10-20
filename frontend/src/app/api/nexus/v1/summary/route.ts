import { NextResponse } from 'next/server';
import { requireHistoryAuth } from '@/lib/history-auth';
import { summarize, SummaryError } from '@/lib/nexus-summary/core';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
const headers = { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' };
let windowStarted = 0;
let requests = 0;
function reply(body: unknown, status: number) { return NextResponse.json(body, { status, headers }); }

export async function POST(request: Request) {
  const auth = await requireHistoryAuth(request);
  if (auth) return auth;
  // Explicit opt-in in an isolated candidate; unavailable by default.
  if (process.env.NEXUS_SUMMARY_MODE !== 'synthetic-mock') return reply({ error: 'Summary disabled' }, 503);
  const now = Date.now();
  if (now - windowStarted >= 60000) { windowStarted = now; requests = 0; }
  if (++requests > 10) return reply({ error: 'Summary rate limit' }, 429);
  if (new URL(request.url).search) return reply({ error: 'Invalid parameter' }, 400);
  if (request.headers.get('content-type')?.split(';')[0].trim().toLowerCase() !== 'application/json') {
    return reply({ error: 'Expected JSON' }, 415);
  }
  const reader = request.body?.getReader();
  if (!reader) return reply({ error: 'Missing request body' }, 400);
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    const bytes: Uint8Array[] = [];
    let size = 0;
    const raw = await Promise.race([
      (async () => {
        for (;;) {
          const chunk = await reader.read();
          if (chunk.done) break;
          size += chunk.value.byteLength;
          if (size > 4096) throw new SummaryError(413, 'Request too large');
          bytes.push(chunk.value);
        }
        return Buffer.concat(bytes).toString('utf8');
      })(),
      new Promise<never>((_, reject) => {
        timer = setTimeout(() => reject(new SummaryError(408, 'Request timeout')), 2000);
      }),
    ]);
    let input: unknown;
    try { input = JSON.parse(raw); } catch { throw new SummaryError(400, 'Invalid JSON'); }
    return reply(await summarize(input), 200);
  } catch (error) {
    return reply({ error: error instanceof SummaryError ? error.message : 'Summary unavailable' },
      error instanceof SummaryError ? error.status : 503);
  } finally {
    if (timer) clearTimeout(timer);
    void reader.cancel().catch(() => {});
  }
}
