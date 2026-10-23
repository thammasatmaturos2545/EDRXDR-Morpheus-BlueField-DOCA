import { buildCopilotEvidence, type EvidenceAccess, type EvidenceIO } from './copilot-evidence';

type Envelope = Awaited<ReturnType<typeof buildCopilotEvidence>>;
type Claim = { text: string; evidence_uids: string[] };
export type Draft = { summary_th: Claim; facts: Claim[]; hypotheses: Claim[];
  unknowns: Claim[]; suggested_checks: Claim[] };
export type SummaryProvider = {
  // Trusted server adapter; no provider endpoint or model supplied by browser.
  name: 'mock' | 'local-vllm'; model: string; revision: string;
  generate: (input: Readonly<Record<string, unknown>>, signal: AbortSignal) => Promise<unknown>;
};
const object = (v: unknown): v is Record<string, unknown> => !!v && typeof v === 'object' && !Array.isArray(v);
const exact = (v: Record<string, unknown>, keys: string[]) =>
  Object.keys(v).sort().join(',') === keys.slice().sort().join(',');
export function validateCopilotDraft(value: unknown, uid: string): Draft {
  if (!object(value) || !exact(value, ['summary_th','facts','hypotheses','unknowns','suggested_checks'])) throw Error('Draft schema');
  function claim(v: unknown): Claim {
    if (!object(v) || !exact(v, ['text','evidence_uids']) || typeof v.text !== 'string' ||
      !v.text.trim() || v.text.length > 500 || !Array.isArray(v.evidence_uids) ||
      v.evidence_uids.length !== 1 || v.evidence_uids[0] !== uid ||
      /[<>%\x00-\x08\x0b\x0c\x0e-\x1f]|https?:\/\/|```/i.test(v.text) ||
      /(?:คะแนน|score|probability|ความน่าจะเป็น)[^\n]{0,24}[0-9๐-๙]|[0-9๐-๙][^\n]{0,12}(?:คะแนน|\/100)/i.test(v.text)) throw Error('Draft claim');
    return { text: v.text, evidence_uids: [uid] };
  }
  function claims(v: unknown): Claim[] {
    if (!Array.isArray(v) || v.length > 3) throw Error('Draft findings');
    return v.map(claim);
  }
  const summary = claim(value.summary_th);
  if (!/[\u0e00-\u0e7f]/.test(summary.text)) throw Error('Draft language');
  return { summary_th: summary, facts: claims(value.facts), hypotheses: claims(value.hypotheses),
    unknowns: claims(value.unknowns), suggested_checks: claims(value.suggested_checks) };
}

// Rebuild evidence for every request. No client evidence, hash or old summary is accepted.
// Transport implementation and GPU reservation enforcement are separate server concerns.
export async function generateCopilotDraft(request: unknown, access: EvidenceAccess, io: EvidenceIO,
  provider: SummaryProvider, timeoutMs = 15000) {
  if (!Number.isInteger(timeoutMs) || timeoutMs < 1 || timeoutMs > 90000) throw Error('Invalid timeout');
  if (!['mock','local-vllm'].includes(provider.name) || !provider.model || provider.model.length > 128 ||
    !provider.revision || provider.revision.length > 128) throw Error('Invalid provider');
  const evidence: Envelope = await buildCopilotEvidence(request, access, io);
  const base = { evidence, provider: provider.name, model: provider.model, model_revision: provider.revision,
    prompt_version: 'soc-evidence-th-v2', input_evidence_hash: evidence.input_evidence_hash,
    human_review_required: true, production_ready: false, automated_response_allowed: false,
    external_transfer_allowed: false };
  if (evidence.results.length !== 1 || !evidence.complete || !evidence.results[0].fact) {
    return { ...base, summary_status: 'insufficient_evidence', draft: null };
  }
  const fact = evidence.results[0].fact;
  // Scores and raw source fields stay in trusted sidecar, never generated text.
  const projected = Object.freeze({ event_uid: fact.event_uid, timestamp_utc: fact.timestamp_utc,
    rule_id: fact.rule_id, wazuh_level: fact.wazuh_level, description: fact.description, ai_status: fact.ai_status });
  const controller = new AbortController();
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    const output = await Promise.race([Promise.resolve().then(() => provider.generate(projected, controller.signal)),
      new Promise<never>((_, reject) => { timer = setTimeout(() => {
        controller.abort(); reject(Error('Provider timeout'));
      }, timeoutMs); })]);
    const draft = validateCopilotDraft(output, fact.event_uid);
    return { ...base, summary_status: provider.name === 'mock' ? 'mock_unreviewed' : 'generated_unreviewed',
      generated_at: new Date().toISOString(), draft };
  } catch { return { ...base, summary_status: 'unavailable', draft: null }; }
  finally { if (timer) clearTimeout(timer); controller.abort(); }
}
