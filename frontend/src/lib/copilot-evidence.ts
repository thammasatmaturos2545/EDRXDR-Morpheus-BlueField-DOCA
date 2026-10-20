import { createHash } from 'node:crypto';
import { canonicalWazuhUid, lookupQuery, parseLookup, type SourceRef } from './uid-lookup';
import { validateNexusAi } from './nexus-soc';

export type AiStatus = 'matched' | 'not_scored' | 'conflict' | 'unavailable';
export type EvidenceStatus = 'matched' | 'not_found' | 'conflict' | 'unavailable' | 'source_unavailable';
type Obj = Record<string, unknown>;
export type EvidenceAccess = {
  // Set by authenticated server code from verified policy, never from request JSON.
  authenticated: boolean;
  sourceProject: string;
  allowedUids: ReadonlySet<string>;
};
export type EvidenceIO = {
  sourceProject: string; // Bound by the resolver-backed server adapter.
  lookup: (body: string) => Promise<unknown>;
  sources: (refs: SourceRef[]) => Promise<unknown>;
  // complete=true requires a bounded, full, non-partial read for the requested UIDs.
  // Do not obtain this by assuming a sampled snapshot or History page is complete.
  ai: (uids: string[]) => Promise<{ complete: boolean; payload: unknown }>;
};
type Fact = { event_uid: string; timestamp_utc: string | null; rule_id: string;
  wazuh_level: number; description: string; ai_status: AiStatus;
  ai_score: number | null; ai_label: string | null };
type Result = { event_uid: string; evidence_status: EvidenceStatus;
  source_ref: { index: string; id: string } | null; fact: Fact | null };
export class EvidenceError extends Error {
  constructor(public status: number, message: string) { super(message); }
}
const object = (v: unknown): v is Obj => !!v && typeof v === 'object' && !Array.isArray(v);
const UID = /^[0-9a-f]{64}$/;
const scoreless = (ai_status: AiStatus) => ({ ai_status, ai_score: null, ai_label: null });
const idPart = (v: unknown): string | null => typeof v === 'string' && v.trim() ? v.trim() :
  typeof v === 'number' && Number.isSafeInteger(v) ? String(v) : null;

export async function buildCopilotEvidence(request: unknown, access: EvidenceAccess, io: EvidenceIO) {
  if (!access.authenticated) throw new EvidenceError(401, 'Authentication required');
  if (!/^[a-z0-9][a-z0-9_-]*$/.test(access.sourceProject)) throw new EvidenceError(403, 'Source scope unavailable');
  if (io.sourceProject !== access.sourceProject) throw new EvidenceError(403, 'Source scope mismatch');
  if (!object(request) || Object.keys(request).join(',') !== 'event_uids' ||
    !Array.isArray(request.event_uids) || request.event_uids.length < 1 || request.event_uids.length > 8 ||
    request.event_uids.some(uid => typeof uid !== 'string' || !UID.test(uid)) ||
    new Set(request.event_uids).size !== request.event_uids.length) throw new EvidenceError(400, 'Invalid UID request');
  const uids = (request.event_uids as string[]).slice().sort();
  if (uids.some(uid => !access.allowedUids.has(uid))) throw new EvidenceError(403, 'Evidence access denied');
  // Request-count/body/provider time limits belong to the authenticated route; IO must
  // enforce its own deadlines. This builder never calls a provider, Docker or network itself.
  let lookup: ReturnType<typeof parseLookup>;
  try { lookup = parseLookup(uids, await io.lookup(lookupQuery(uids))); }
  catch { lookup = uids.map(uid => ({ uid, status: 'unavailable' as const })); }
  const refs = lookup.flatMap(row => row.status === 'matched' && row.ref ? [row.ref] : []);
  let docs: unknown[] = [];
  if (refs.length) {
    try {
      const body = await io.sources(refs);
      if (object(body) && Array.isArray(body.docs) && body.docs.length === refs.length) docs = body.docs;
    } catch { /* Missing source is reported per UID, never as a fabricated fact. */ }
  }
  let ai: ReturnType<typeof validateNexusAi> = [];
  let aiComplete = false;
  if (refs.length) {
    try {
      const result = await io.ai(refs.map(r => r.uid));
      if (result.complete === true) { ai = validateNexusAi(result.payload); aiComplete = true; }
    } catch { /* A malformed or partial AI read makes AI unavailable, not zero. */ }
  }
  const results: Result[] = lookup.map(row => {
    const base = { event_uid: row.uid, source_ref: row.ref ? { index: row.ref.index, id: row.ref.id } : null };
    if (row.status !== 'matched' || !row.ref) return { ...base, evidence_status: row.status as EvidenceStatus, fact: null };
    const position = refs.findIndex(ref => ref.uid === row.uid);
    const doc = docs[position];
    if (!object(doc) || doc._index !== row.ref.index || doc._id !== row.ref.id ||
      doc.error || doc.found !== true || !object(doc._source)) {
      return { ...base, evidence_status: 'source_unavailable', fact: null };
    }
    const raw = doc._source;
    if (canonicalWazuhUid(raw) !== row.uid) return { ...base, evidence_status: 'conflict', fact: null };
    const rule = object(raw.rule) ? raw.rule : {};
    const ruleId = idPart(rule.id);
    if (!ruleId || typeof rule.level !== 'number' || !Number.isInteger(rule.level) ||
      rule.level < 0 || rule.level > 15 || typeof rule.description !== 'string' || rule.description.length > 512) {
      return { ...base, evidence_status: 'source_unavailable', fact: null };
    }
    const aiRows = ai.filter(a => a.event_uid === row.uid);
    let fields: { ai_status: AiStatus; ai_score: number | null; ai_label: string | null };
    if (!aiComplete) fields = scoreless('unavailable');
    else if (!aiRows.length) fields = scoreless('not_scored');
    else if (aiRows.length !== 1 || idPart(aiRows[0].wazuh_rule_id) !== ruleId || aiRows[0].wazuh_rule_level !== rule.level ||
      typeof aiRows[0].high_severity_score !== 'number' || !Number.isFinite(aiRows[0].high_severity_score) ||
      (aiRows[0].high_severity_score as number) < 0 || (aiRows[0].high_severity_score as number) > 1 ||
      !['low_severity', 'high_severity'].includes(String(aiRows[0].predicted_label))) {
      fields = scoreless('conflict');
    } else fields = { ai_status: 'matched', ai_score: aiRows[0].high_severity_score as number,
      ai_label: aiRows[0].predicted_label as string };
    const timestamp = typeof raw.timestamp === 'string' && Number.isFinite(Date.parse(raw.timestamp)) ? raw.timestamp : null;
    // Rule description remains untrusted text; no raw_json/full_log/IP/user/agent/path fields.
    // Local-only evidence: this is NOT an external-provider anonymization policy.
    const fact: Fact = { event_uid: row.uid, timestamp_utc: timestamp, rule_id: ruleId,
      wazuh_level: rule.level, description: rule.description, ...fields };
    return { ...base, evidence_status: 'matched', fact };
  });
  const policyVersion = 'local-evidence-v1';
  const inputHash = createHash('sha256').update(JSON.stringify({ policy_version: policyVersion,
    source_project: access.sourceProject, results })).digest('hex');
  return { schema_version: policyVersion, source_project: access.sourceProject,
    observed_at: new Date().toISOString(), input_evidence_hash: inputHash, results,
    complete: results.every(r => r.evidence_status === 'matched'),
    external_transfer_allowed: false, production_ready: false, automated_response_allowed: false };
}
