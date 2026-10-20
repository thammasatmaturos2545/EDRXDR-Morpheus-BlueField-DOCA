const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const cache = new Map();
function load(name) {
  if (cache.has(name)) return cache.get(name);
  const scope = { exports: {}, Buffer, Date, Set, Map, AbortSignal, fetch,
    require: n => n.startsWith('./') ? load(n.slice(2)) : n.startsWith('@/lib/') ? load(n.slice(6)) : require(n) };
  vm.runInNewContext(ts.transpileModule(fs.readFileSync(path.join(__dirname, '../src/lib', name + '.ts'), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText, scope);
  cache.set(name, scope.exports); return scope.exports;
}
const c = load('copilot-ai-reader');
const uid = '1'.padStart(64, '0');
const ai = { schema_version: 'live-severity-1', source_type: 'wazuh', processing_mode: 'live',
  analysis_engine: c.AI_SCOPE.engine, model_name: c.AI_SCOPE.model, event_uid: uid,
  production_ready: false, automated_response_allowed: false, threshold: .5,
  high_severity_score: 0, predicted_label: 'low_severity', source_topic: 'wazuh-alerts',
  source_partition: 0, source_offset: 1, input_topic: 'morpheus-input', input_partition: 0, input_offset: 1,
  scored_at_utc: '2026-10-20T00:00:00Z', wazuh_rule_id: '5501', wazuh_rule_level: 0 };
const hit = () => ({ _index: 'edrxdr-events-2026.10.20', _source: { ...ai, raw_json: 'PRIVATE' } });
const response = (hits = [hit()], total = hits.length) => ({ timed_out: false,
  _shards: { total: 1, successful: 1, failed: 0 }, hits: { total: { value: total, relation: 'eq' }, hits } });
const parse = value => c.parseCompleteAi([uid], { responses: [value] });
let count = 0;
async function test(name, fn) { await fn(); count++; console.log('PASS ' + name); }
async function main() {
  await test('exact keyword queries, live model scope, limits and NDJSON', () => {
    const lines = c.aiQuery([uid]).trim().split('\n').map(JSON.parse);
    assert.equal(lines[1].size, 2); assert.equal(lines[1].track_total_hits, true);
    assert.equal(lines[1].query.bool.filter[0].term['event_uid.keyword'], uid);
    for (const ids of [[], [uid, uid], ['bad'], Array(9).fill(uid)]) assert.throws(() => c.aiQuery(ids));
  });
  await test('zero preserved and raw source fields removed', () => {
    const result = parse(response()); assert.equal(result.complete, true);
    assert.equal(result.payload.events[0].high_severity_score, 0);
    assert.equal(JSON.stringify(result).includes('PRIVATE'), false);
  });
  await test('complete zero hits allowed; duplicate hits retained for conflict', () => {
    assert.equal(parse(response([])).payload.events.length, 0);
    assert.equal(parse(response([hit(), hit()], 10)).payload.events.length, 2);
  });
  await test('timeout, missing/partial shards and inexact counts rejected', () => {
    for (const change of [x => x.timed_out = true, x => delete x.timed_out,
      x => delete x._shards, x => x._shards.total = 0, x => x._shards.failed = 1,
      x => x._shards.successful = 0, x => x.hits.total.relation = 'gte',
      x => x.hits.total.value = 2, x => x.error = {}]) {
      const value = response(); change(value); assert.throws(() => parse(value));
    }
    assert.throws(() => c.parseCompleteAi([uid], { responses: [] }));
  });
  await test('foreign UID/index, replay, changed model and score mismatch rejected', () => {
    for (const change of [h => h._index = 'other-team-index', h => h._source.event_uid = '2'.padStart(64, '0'),
      h => h._source.processing_mode = 'replay', h => h._source.model_name = 'wrong',
      h => h._source.high_severity_score = 1]) {
      const h = hit(); change(h); assert.throws(() => parse(response([h])));
    }
  });
  await test('HTTP transport read-only namespace and response body bounds', async () => {
    const result = await c.readCompleteAi([uid], async (url, options) => {
      assert(url.startsWith('http://127.0.0.1:9200/edrxdr-events-*/_msearch?'));
      assert.equal(options.redirect, 'error'); assert.equal(options.cache, 'no-store');
      return new Response(JSON.stringify({ responses: [response()] }));
    }); assert.equal(result.complete, true);
    await assert.rejects(c.readCompleteAi([uid], async () => new Response(' '.repeat(1024 * 1024 + 1))));
    await assert.rejects(c.readCompleteAi([uid], async () => new Response('{}', { status: 503 })));
    await assert.rejects(c.readCompleteAi([uid], async () => new Response('not JSON')));
  });
  console.log(`PASS ${count} complete AI reader groups; synthetic offline only`);
}
main().catch(e => { console.error(e); process.exitCode = 1; });
