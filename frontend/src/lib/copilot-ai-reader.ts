import { validateNexusAi } from './nexus-soc';

export const AI_SCOPE = Object.freeze({ schema: 'live-severity-1',
  model: 'wazuh-severity-context-v2-balanced-20261008T190719Z-1398863',
  engine: 'nvidia-morpheus-context-severity-v1', mode: 'live', uid_field: 'event_uid.keyword' });
const fields = ['schema_version', 'source_type', 'processing_mode', 'analysis_engine', 'model_name',
  'event_uid', 'production_ready', 'automated_response_allowed', 'threshold', 'high_severity_score',
  'predicted_label', 'source_topic', 'source_partition', 'source_offset', 'input_topic', 'input_partition',
  'input_offset', 'scored_at_utc', 'wazuh_rule_id', 'wazuh_rule_level'];
const object = (v: unknown): v is Record<string, unknown> => !!v && typeof v === 'object' && !Array.isArray(v);
function checkUids(uids: string[]) {
  if (!Array.isArray(uids) || uids.length < 1 || uids.length > 8 || new Set(uids).size !== uids.length ||
    uids.some(u => typeof u !== 'string' || !/^[0-9a-f]{64}$/.test(u))) throw Error('Invalid AI UID request');
}
export function aiQuery(uids: string[]) {
  checkUids(uids);
  return uids.map(uid => JSON.stringify({}) + '\n' + JSON.stringify({ size: 2, track_total_hits: true,
    _source: fields, query: { bool: { filter: [
      { term: { 'event_uid.keyword': uid } }, { term: { 'schema_version.keyword': AI_SCOPE.schema } },
      { term: { 'source_type.keyword': 'wazuh' } }, { term: { 'processing_mode.keyword': AI_SCOPE.mode } },
      { term: { 'analysis_engine.keyword': AI_SCOPE.engine } }, { term: { 'model_name.keyword': AI_SCOPE.model } },
      { term: { production_ready: false } }, { term: { automated_response_allowed: false } },
    ] } } }) + '\n').join('');
}
export function parseCompleteAi(uids: string[], body: unknown) {
  checkUids(uids);
  if (!object(body) || !Array.isArray(body.responses) || body.responses.length !== uids.length) throw Error('Invalid AI response');
  const events: Record<string, unknown>[] = [];
  body.responses.forEach((response: unknown, i: number) => {
    if (!object(response) || response.error || response.timed_out !== false ||
      !object(response._shards) || !object(response.hits)) throw Error('Incomplete AI search');
    const shards = response._shards, total = response.hits.total, hits = response.hits.hits;
    if (!Number.isSafeInteger(shards.total) || (shards.total as number) < 1 ||
      shards.successful !== shards.total || shards.failed !== 0 ||
      !object(total) || total.relation !== 'eq' || !Number.isSafeInteger(total.value) ||
      (total.value as number) < 0 || !Array.isArray(hits) || hits.length !== Math.min(total.value as number, 2)) {
      throw Error('Incomplete AI count or shards');
    }
    for (const hit of hits) {
      if (!object(hit) || typeof hit._index !== 'string' || !/^edrxdr-events-[a-z0-9._-]+$/.test(hit._index) ||
        !object(hit._source) || hit._source.event_uid !== uids[i]) throw Error('Unexpected AI source');
      const projected: Record<string, unknown> = {};
      for (const key of fields) if (Object.hasOwn(hit._source, key)) projected[key] = hit._source[key];
      events.push(projected);
    }
  });
  validateNexusAi({ events }); // Validate provenance, current model, score/label and live-only flags.
  // Two valid hits are retained so the evidence builder marks that UID conflict.
  return { complete: true, payload: { events } };
}
export async function readCompleteAi(uids: string[], fetcher: typeof fetch = fetch) {
  const body = aiQuery(uids);
  // Fixed local read-only namespace, never an endpoint supplied by browser/LLM.
  const response = await fetcher('http://127.0.0.1:9200/edrxdr-events-*/_msearch?allow_no_indices=false&ignore_unavailable=false', {
    method: 'POST', headers: { 'Content-Type': 'application/x-ndjson' }, body,
    cache: 'no-store', redirect: 'error', signal: AbortSignal.timeout(6000),
  });
  if (!response.ok || !response.body) throw Error('AI read unavailable');
  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let size = 0;
  try {
    for (;;) {
      const chunk = await reader.read();
      if (chunk.done) break;
      size += chunk.value.byteLength;
      if (size > 1024 * 1024) throw Error('AI response too large');
      chunks.push(chunk.value);
    }
  } finally { void reader.cancel().catch(() => {}); }
  return parseCompleteAi(uids, JSON.parse(Buffer.concat(chunks).toString('utf8')));
}
