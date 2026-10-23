import { buildCopilotEvidence, EvidenceError, type EvidenceIO } from './copilot-evidence';

type Policy = { enabled: boolean; project: string; uids: string[] };
type Dependencies = {
  auth: (request: Request) => Promise<Response | null>;
  policy: () => Policy;
  io: (project: string) => EvidenceIO;
};
const headers = { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' };
const reply = (body: unknown, status: number) => Response.json(body, { status, headers });

async function boundedJson(request: Request) {
  if (request.headers.get('content-type')?.split(';')[0].trim().toLowerCase() !== 'application/json') {
    throw new EvidenceError(415, 'JSON required');
  }
  const length = request.headers.get('content-length');
  if (length !== null && (!/^\d+$/.test(length) || Number(length) > 4096)) {
    throw new EvidenceError(413, 'Request too large');
  }
  if (!request.body) throw new EvidenceError(400, 'Invalid JSON');
  const reader = request.body.getReader();
  let timer: ReturnType<typeof setTimeout> | undefined;
  const chunks: Uint8Array[] = [];
  let size = 0;
  const read = async () => {
    for (;;) {
      const part = await reader.read();
      if (part.done) break;
      size += part.value.byteLength;
      if (size > 4096) throw new EvidenceError(413, 'Request too large');
      chunks.push(part.value);
    }
    try { return JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(Buffer.concat(chunks))); }
    catch { throw new EvidenceError(400, 'Invalid JSON'); }
  };
  try {
    return await Promise.race([read(), new Promise<never>((_, reject) => {
      timer = setTimeout(() => reject(new EvidenceError(408, 'Request timeout')), 5000);
    })]);
  } finally {
    if (timer) clearTimeout(timer);
    void reader.cancel().catch(() => {});
  }
}

// One in-flight request and twelve admitted requests/minute per process.
// This is a local preview bound, not distributed rate limiting.
export function createEvidenceHandler(deps: Dependencies) {
  let busy = false, windowStart = 0, count = 0;
  return async function POST(request: Request): Promise<Response> {
    const denial = await deps.auth(request);
    if (denial) return denial;
    let policy: Policy;
    try {
      policy = deps.policy();
      if (!policy.enabled) return reply({ error: 'Copilot evidence disabled' }, 503);
      if (!/^[a-z0-9][a-z0-9_-]*$/.test(policy.project) || !Array.isArray(policy.uids) ||
        policy.uids.length < 1 || policy.uids.length > 100 || new Set(policy.uids).size !== policy.uids.length ||
        policy.uids.some(uid => typeof uid !== 'string' || !/^[0-9a-f]{64}$/.test(uid))) {
        throw Error('Invalid policy');
      }
    } catch { return reply({ error: 'Evidence policy unavailable' }, 503); }
    if (new URL(request.url).search) return reply({ error: 'Invalid parameter' }, 400);
    const now = Date.now();
    if (now - windowStart >= 60000) { windowStart = now; count = 0; }
    if (busy || count >= 12) return reply({ error: 'Evidence request limit' }, 429);
    busy = true; count++;
    try {
      const body = await boundedJson(request);
      const result = await buildCopilotEvidence(body, { authenticated: true,
        sourceProject: policy.project, allowedUids: new Set(policy.uids) }, deps.io(policy.project));
      return reply({ ...result, evidence_only: true, summary_status: 'not_requested' }, 200);
    } catch (error) {
      return error instanceof EvidenceError ? reply({ error: error.message }, error.status) :
        reply({ error: 'Copilot evidence unavailable' }, 503);
    } finally { busy = false; }
  };
}
