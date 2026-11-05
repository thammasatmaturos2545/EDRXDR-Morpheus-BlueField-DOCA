import { NextResponse } from 'next/server';
import { runDecisionReview } from '@/lib/decision-review';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
let inFlight = 0;
const headers = { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' };
function reply(body: unknown, status: number) {
  return NextResponse.json(body, { status, headers: status === 401
    ? { ...headers, 'WWW-Authenticate': 'Basic realm="NEXUS Named Reviewers", charset="UTF-8"' } : headers });
}

async function readBody(request: Request) {
  const length = request.headers.get('content-length');
  if (length !== null && (!/^\d+$/.test(length) || Number(length) > 4096)) throw Error();
  if (!/^application\/json(?:\s*;\s*charset=utf-8)?$/i.test(request.headers.get('content-type') || '')) throw Error();
  if (!request.body) throw Error();
  const reader = request.body.getReader();
  const chunks: Uint8Array[] = [];
  let bytes = 0;
  const deadline = Date.now() + 3000;
  try {
    for (;;) {
      const remaining = deadline - Date.now();
      if (remaining <= 0) throw Error();
      let timer: ReturnType<typeof setTimeout> | undefined;
      const result = await Promise.race([
        reader.read(),
        new Promise<never>((_, reject) => { timer = setTimeout(() => reject(Error()), remaining); }),
      ]).finally(() => clearTimeout(timer));
      if (result.done) break;
      bytes += result.value.byteLength;
      if (bytes > 4096) throw Error();
      chunks.push(result.value);
    }
    return JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(Buffer.concat(chunks)));
  } finally {
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}

async function handle(request: Request, write: boolean) {
  if (process.env.NEXUS_DECISION_REVIEW_ENABLED !== '1') return reply({ error: 'DECISION_REVIEW_DISABLED' }, 503);
  const hash = process.env.NEXUS_DECISION_CATALOG_SHA256 || '';
  if (!/^[a-f0-9]{64}$/.test(hash)) return reply({ error: 'CATALOG_NOT_PINNED' }, 503);
  const url = new URL(request.url);
  if (url.search) return reply({ error: 'QUERY_NOT_SUPPORTED' }, 400);
  const authorization = request.headers.get('authorization') || '';
  if (authorization.length > 512 || !/^Basic [A-Za-z0-9+/]+={0,2}$/.test(authorization))
    return reply({ error: 'AUTH_REQUIRED' }, 401);
  // Browser requests must be same-origin; never trust forwarded host headers here.
  const site = request.headers.get('sec-fetch-site');
  const origin = request.headers.get('origin');
  if ((site && !['same-origin', 'none'].includes(site)) ||
      (origin !== null && origin !== url.origin) || (write && origin !== url.origin))
    return reply({ error: 'ORIGIN_REJECTED' }, 403);
  if (inFlight >= 2) return reply({ error: 'DECISION_REVIEW_BUSY' }, 503);
  inFlight++;
  try {
    let body: unknown = null;
    if (write) {
      try { body = await readBody(request); }
      catch { return reply({ error: 'INVALID_OR_OVERSIZED_BODY' }, 400); }
    }
    const result = await runDecisionReview({ method: write ? 'POST' : 'GET', authorization, body }, hash);
    return reply(result.body, result.status);
  } catch { return reply({ error: 'DECISION_REVIEW_UNAVAILABLE' }, 503); }
  finally { inFlight--; }
}

export async function GET(request: Request) { return handle(request, false); }
export async function POST(request: Request) { return handle(request, true); }
