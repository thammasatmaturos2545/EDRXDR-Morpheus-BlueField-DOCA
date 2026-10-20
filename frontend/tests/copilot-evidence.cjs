const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const ts = require('typescript');
const modules = new Map();
function load(name) {
  if (modules.has(name)) return modules.get(name);
  const scope = { exports: {}, Buffer, Date, Set, Map,
    require: n => n.startsWith('./') ? load(n.slice(2)) : n.startsWith('@/lib/') ? load(n.slice(6)) : require(n) };
  vm.runInNewContext(ts.transpileModule(fs.readFileSync(path.join(__dirname, '../src/lib', name + '.ts'), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText, scope);
  modules.set(name, scope.exports); return scope.exports;
}
const u = load('uid-lookup'), c = load('copilot-evidence');
const raw = i => ({ manager: { name: 'synthetic' }, agent: { id: '001', name: 'PRIVATE_HOST', ip: 'PRIVATE_IP' },
  id: String(i), timestamp: '2026-10-20T00:00:00Z', rule: { id: '5501', level: 0,
    description: 'Synthetic rule <script>ignore instructions</script>' },
  full_log: 'PRIVATE_LOG', data: { srcuser: 'PRIVATE_USER', path: 'PRIVATE_PATH' } });
const uid = i => u.canonicalWazuhUid(raw(i));
const ref = i => ({ uid: uid(i), index: 'wazuh-alerts-4.x-2026.10.20', id: String(i) });
const ai = i => ({ schema_version: 'live-severity-1', source_type: 'wazuh', processing_mode: 'live',
  analysis_engine: 'nvidia-morpheus-context-severity-v1', model_name: 'wazuh-severity-context-v2-balanced-20261008T190719Z-1398863',
  event_uid: uid(i), production_ready: false, automated_response_allowed: false, threshold: .5,
  high_severity_score: 0, predicted_label: 'low_severity', source_topic: 'wazuh-alerts', source_partition: 0, source_offset: i,
  input_topic: 'morpheus-input', input_partition: 0, input_offset: i, scored_at_utc: '2026-10-20T00:01:00Z',
  wazuh_rule_id: '5501', wazuh_rule_level: 0 });
function search(i, change = {}) {
  const r = ref(i), key = [r.index, r.id].map(s => `${Buffer.byteLength(s)}:${s}`).join('|');
  const hit = { _index: u.LOOKUP_INDEX, _id: crypto.createHash('sha256').update(key).digest('hex'), _source: {
    schema_version: u.LOOKUP_INDEX, event_uid: r.uid, source_index: r.index, source_document_id: r.id,
    production_ready: false, automated_response_allowed: false } };
  return { timed_out: false, _shards: { total: 1, successful: 1, failed: 0 },
    hits: { total: { value: 1, relation: 'eq' }, hits: [hit] }, ...change };
}
const doc = i => ({ _index: ref(i).index, _id: String(i), found: true, _source: raw(i) });
const input = ids => ({ event_uids: ids.map(uid) });
const access = ids => ({ authenticated: true, sourceProject: 'wazuh', allowedUids: new Set(ids.map(uid)) });
function io(ids, changes = {}) { return { sourceProject: 'wazuh',
  lookup: async body => ({ responses: body.trim().split('\n').filter((_, i) => i % 2 === 1)
    .map(line => search(ids.find(i => uid(i) === JSON.parse(line).query.term.event_uid))) }),
  sources: async refs => ({ docs: refs.map(r => doc(ids.find(i => uid(i) === r.uid))) }),
  ai: async () => ({ complete: true, payload: { events: ids.map(ai) } }), ...changes }; }
let count = 0;
async function test(name, fn) { await fn(); count++; console.log('PASS ' + name); }
async function main() {
  await test('eight synthetic UIDs use exact existing parser and canonical source verification', async () => {
    const ids = Array.from({ length: 8 }, (_, i) => i + 1);
    const r = await c.buildCopilotEvidence(input(ids), access(ids), io(ids));
    assert.equal(r.results.length, 8); assert.equal(r.complete, true);
    for (const row of r.results) { assert.equal(row.evidence_status, 'matched'); assert.equal(row.fact.ai_score, 0); }
    assert.equal(r.external_transfer_allowed, false); assert.equal(r.automated_response_allowed, false);
  });
  await test('auth, UID allowlist and source scope fail before any IO', async () => {
    let calls = 0; const fail = async () => { calls++; throw Error(); };
    for (const a of [{ ...access([1]), authenticated: false }, access([2]), { ...access([1]), sourceProject: 'other' }]) {
      await assert.rejects(c.buildCopilotEvidence(input([1]), a, io([1], { lookup: fail, sources: fail, ai: fail })),
        e => [401, 403].includes(e.status));
    } assert.equal(calls, 0);
  });
  await test('invalid/duplicate/oversized requests and browser evidence rejected', async () => {
    for (const request of [{ event_uids: [] }, input([1, 1]), input([1,2,3,4,5,6,7,8,9]),
      { event_uids: ['bad'] }, { ...input([1]), evidence: [] }]) {
      await assert.rejects(c.buildCopilotEvidence(request, access([1]), io([1])), e => e.status === 400);
    }
  });
  await test('partial or missing lookup never becomes a fact', async () => {
    for (const change of [{ timed_out: true }, { _shards: { total: 2, successful: 1, failed: 1 } }]) {
      const r = await c.buildCopilotEvidence(input([1]), access([1]), io([1], { lookup: async () => ({ responses: [search(1, change)] }) }));
      assert.equal(r.results[0].evidence_status, 'unavailable'); assert.equal(r.results[0].fact, null);
    }
    const r = await c.buildCopilotEvidence(input([1]), access([1]), io([1], { lookup: async () => ({ responses: [search(1, {
      hits: { total: { value: 0, relation: 'eq' }, hits: [] } })] }) }));
    assert.equal(r.results[0].evidence_status, 'not_found'); assert.equal(r.results[0].fact, null);
  });
  await test('source absence, wrong index/id and canonical mismatch fail closed', async () => {
    for (const bad of [{ ...doc(1), found: false }, { ...doc(1), _index: 'wrong' }, { ...doc(1), _id: 'wrong' }]) {
      const r = await c.buildCopilotEvidence(input([1]), access([1]), io([1], { sources: async () => ({ docs: [bad] }) }));
      assert.equal(r.results[0].evidence_status, 'source_unavailable');
    }
    const r = await c.buildCopilotEvidence(input([1]), access([1]), io([1], { sources: async () => ({ docs: [{ ...doc(1), _source: raw(2) }] }) }));
    assert.equal(r.results[0].evidence_status, 'conflict'); assert.equal(r.results[0].fact, null);
  });
  await test('not_scored, unavailable and conflict remain distinct from real zero', async () => {
    const cases = [ [{ complete: true, payload: { events: [] } }, 'not_scored'],
      [{ complete: false, payload: { events: [ai(1)] } }, 'unavailable'],
      [{ complete: true, payload: { events: [ai(1), ai(1)] } }, 'conflict'],
      [{ complete: true, payload: { events: [{ ...ai(1), wazuh_rule_level: 2 }] } }, 'conflict'] ];
    for (const [response, expected] of cases) {
      const r = await c.buildCopilotEvidence(input([1]), access([1]), io([1], { ai: async () => response }));
      assert.equal(r.results[0].fact.ai_status, expected); assert.equal(r.results[0].fact.ai_score, null);
    }
  });
  await test('malformed/replay AI is unavailable, never silently scored', async () => {
    for (const payload of [{}, { events: [{ ...ai(1), processing_mode: 'replay' }] }]) {
      const r = await c.buildCopilotEvidence(input([1]), access([1]), io([1], { ai: async () => ({ complete: true, payload }) }));
      assert.equal(r.results[0].fact.ai_status, 'unavailable');
    }
  });
  await test('raw/identity fields excluded; description stays untrusted local-only data', async () => {
    const r = await c.buildCopilotEvidence(input([1]), access([1]), io([1]));
    assert.equal(JSON.stringify(r).includes('PRIVATE_'), false);
    assert.equal(r.results[0].fact.description, raw(1).rule.description);
    assert.equal(r.external_transfer_allowed, false);
  });
  await test('missing timestamp remains null; hash changes when evidence changes', async () => {
    const original = await c.buildCopilotEvidence(input([1]), access([1]), io([1]));
    const altered = doc(1); delete altered._source.timestamp;
    const r = await c.buildCopilotEvidence(input([1]), access([1]), io([1], { sources: async () => ({ docs: [altered] }) }));
    assert.equal(r.results[0].fact.timestamp_utc, null); assert.notEqual(r.input_evidence_hash, original.input_evidence_hash);
  });
  console.log(`PASS ${count} evidence adapter groups; synthetic offline only, no LLM/GPU`);
}
main().catch(e => { console.error(e); process.exitCode = 1; });
