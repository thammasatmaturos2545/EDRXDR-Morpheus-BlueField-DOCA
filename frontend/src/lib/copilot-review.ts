export const REVIEW_UIDS = Object.freeze([
  '014b61edf23ba795befa75a2f54ab6da9e5492ec9dd20e1b3d8b50423437585e',
  '0de4f324d1cdb1fe23680d9abf6fa70548fc52978136af474b4d3c03d46701fc',
  '5062c6e96485f0415cdbeeb57e2e899f18950aa85d79983b5c5c39591e9e62ef',
  '5c7313b7a07748f0bef12b0e6228c90c17c1d97746ffab9402574f77788a0441',
  '642321b4bae66721826a977d8913cf98ee413ba12963432ca087d0776d724f7d',
  '6ee6ed8c501cb7c3790aab62049d1926823fc4e92ca9181f78bfa11d0e39344b',
  '8e2fe7ec5b692949e46471e4d6dd0b9e04cbe5f42dafa49ad13f2370569efa4f',
  'ab444373341573048c7967e8a2e2468d4fadc5d16873e70c1cff597c18c16a4c',
]);
const object = (v: unknown): v is Record<string, unknown> => !!v && typeof v === 'object' && !Array.isArray(v);
const text = (v: unknown, max: number): string => {
  if (typeof v !== 'string' || !v.trim() || v.length > max) throw Error('Invalid review text');
  return v;
};
const hash = (v: unknown) => { const s = text(v, 64); if (!/^[0-9a-f]{64}$/.test(s)) throw Error('Invalid hash'); return s; };
const time = (v: unknown) => { const s = text(v, 64); if (!Number.isFinite(Date.parse(s))) throw Error('Invalid time'); return s; };
function claim(value: unknown, uid: string) {
  if (!object(value) || Object.keys(value).sort().join(',') !== 'evidence_uids,text' ||
    !Array.isArray(value.evidence_uids) || value.evidence_uids.length !== 1 || value.evidence_uids[0] !== uid) {
    throw Error('Invalid review citation');
  }
  return { text: text(value.text, 500), evidence_uids: [uid] };
}
function claims(value: unknown, uid: string) {
  if (!Array.isArray(value) || value.length > 3) throw Error('Invalid findings');
  return value.map(v => claim(v, uid));
}
export function parseCopilotReview(value: unknown) {
  if (!object(value) || value.provider !== 'local-vllm' || value.model !== 'nexus-gpt-oss-20b' ||
    value.model_revision !== '6cee5e81ee83917806bbde320786a8fb61efebee' ||
    value.prompt_version !== 'soc-local-th-v1' || value.production_ready !== false ||
    value.automated_response_allowed !== false || value.external_transfer_allowed !== false ||
    value.human_review_required !== true || !Array.isArray(value.results) || value.results.length !== 8) {
    throw Error('Invalid saved review contract');
  }
  const seen = new Set<string>();
  const results = value.results.map(row => {
    if (!object(row) || typeof row.event_uid !== 'string' || !REVIEW_UIDS.includes(row.event_uid) || seen.has(row.event_uid) ||
      row.status !== 'generated_unreviewed' || row.automated_response_allowed !== false ||
      !object(row.draft) || !object(row.trusted_evidence)) throw Error('Invalid review UID/status');
    const uid = row.event_uid, evidence = row.trusted_evidence;
    seen.add(uid);
    if (evidence.event_uid !== uid || evidence.evidence_status !== 'matched' ||
      !object(evidence.fact) || !object(evidence.source_ref)) throw Error('Unverified evidence');
    const fact = evidence.fact;
    if (fact.event_uid !== uid || fact.ai_status !== 'matched' ||
      typeof fact.ai_score !== 'number' || !Number.isFinite(fact.ai_score) || fact.ai_score < 0 || fact.ai_score > 1 ||
      typeof fact.wazuh_level !== 'number' || !Number.isInteger(fact.wazuh_level) || fact.wazuh_level < 0 || fact.wazuh_level > 15 ||
      fact.ai_label !== (fact.ai_score >= .5 ? 'high_severity' : 'low_severity')) throw Error('Invalid trusted score');
    const index = text(evidence.source_ref.index, 128);
    if (!/^wazuh-alerts-4\.x-\d{4}\.\d{2}\.\d{2}$/.test(index)) throw Error('Invalid source index');
    return { event_uid: uid, status: 'generated_unreviewed',
      draft: { summary_th: claim(row.draft.summary_th, uid), facts: claims(row.draft.facts, uid),
        hypotheses: claims(row.draft.hypotheses, uid), unknowns: claims(row.draft.unknowns, uid),
        suggested_checks: claims(row.draft.suggested_checks, uid) },
      evidence: { event_uid: uid, timestamp_utc: fact.timestamp_utc === null ? null : time(fact.timestamp_utc),
        rule_id: text(fact.rule_id, 128), wazuh_level: fact.wazuh_level,
        description: text(fact.description, 512), ai_status: 'matched', ai_score: fact.ai_score, ai_label: fact.ai_label,
        source_ref: { index, id: text(evidence.source_ref.id, 512) } } };
  }).sort((a, b) => a.event_uid.localeCompare(b.event_uid));
  return { provider: 'local-vllm', model: value.model, model_revision: value.model_revision,
    prompt_version: value.prompt_version, generated_at: time(value.finished_at),
    input_evidence_hash: hash(value.input_evidence_hash), input_file_sha256: hash(value.input_file_sha256),
    saved_review_only: true, human_review_required: true, production_ready: false,
    automated_response_allowed: false, external_transfer_allowed: false, results };
}
