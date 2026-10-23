const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const cache = new Map();
function load(name) {
  if (cache.has(name)) return cache.get(name);
  const scope = { exports: {}, Buffer, Date, Set, Map, Response, URL, TextDecoder, setTimeout, clearTimeout,
    require: n => n.startsWith('./') ? load(n.slice(2)) : n.startsWith('@/lib/') ? load(n.slice(6)) : require(n) };
  vm.runInNewContext(ts.transpileModule(fs.readFileSync(path.join(__dirname, '../src/lib', name + '.ts'), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText, scope);
  cache.set(name, scope.exports); return scope.exports;
}
const { createEvidenceHandler } = load('copilot-evidence-http');
const uid = '1'.repeat(64);
const req = (body = { event_uids: [uid] }, extra = {}) => new Request('http://local/evidence', {
  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), ...extra,
});
let calls = 0;
const deps = { auth: async () => null,
  policy: () => ({ enabled: true, project: 'wazuh', uids: [uid] }),
  io: project => ({ sourceProject: project,
    lookup: async () => { calls++; throw Error('synthetic outage'); },
    sources: async () => { throw Error('Unexpected source read'); },
    ai: async () => { throw Error('Unexpected AI read'); } }) };
(async () => {
  let handler = createEvidenceHandler({ ...deps, auth: async () => new Response('Denied', { status: 401 }),
    policy: () => { throw Error('Auth must run first'); } });
  assert.equal((await handler(req())).status, 401);
  assert.equal((await createEvidenceHandler({ ...deps, policy: () => ({ enabled: false }) })(req())).status, 503);
  for (const uids of [[], [uid, uid], ['bad'], Array(101).fill(uid)]) {
    assert.equal((await createEvidenceHandler({ ...deps, policy: () => ({ enabled: true, project: 'wazuh', uids }) })(req())).status, 503);
  }
  console.log('PASS auth first; disabled and invalid server policy prevent IO');
  for (const [body, status] of [[{}, 400], [{ event_uids: [] }, 400], [{ event_uids: [uid, uid] }, 400],
    [{ event_uids: ['2'.repeat(64)] }, 403], [{ event_uids: [uid], evidence: {} }, 400]]) {
    assert.equal((await createEvidenceHandler(deps)(req(body))).status, status);
  }
  assert.equal(calls, 0);
  console.log('PASS exact server allowlist; browser evidence and invalid UIDs rejected before IO');
  assert.equal((await createEvidenceHandler(deps)(new Request('http://local/evidence?x=1', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' }))).status, 400);
  assert.equal((await createEvidenceHandler(deps)(req({}, { body: '{' }))).status, 400);
  assert.equal((await createEvidenceHandler(deps)(req({}, { headers: { 'Content-Type': 'text/plain' } }))).status, 415);
  assert.equal((await createEvidenceHandler(deps)(req({}, { body: 'x'.repeat(4097) }))).status, 413);
  assert.equal((await createEvidenceHandler(deps)(req({}, { headers: { 'Content-Type': 'application/json', 'Content-Length': '4097' } }))).status, 413);
  console.log('PASS query, malformed JSON, media type and streamed/declared body bounds');
  const result = await createEvidenceHandler(deps)(req());
  assert.equal(result.status, 200); assert.equal(result.headers.get('cache-control'), 'no-store');
  const data = await result.json();
  assert.equal(data.results[0].evidence_status, 'unavailable');
  assert.equal(data.results[0].fact, null); assert.equal(data.complete, false);
  assert.equal(data.summary_status, 'not_requested'); assert.equal(data.evidence_only, true);
  assert.equal(data.automated_response_allowed, false);
  console.log('PASS actual builder outage stays unavailable; no generated summary or fabricated fact');
  handler = createEvidenceHandler(deps);
  for (let i = 0; i < 12; i++) assert.equal((await handler(req())).status, 200);
  assert.equal((await handler(req())).status, 429);
  let release;
  handler = createEvidenceHandler({ ...deps, io: project => ({ ...deps.io(project),
    lookup: () => new Promise(resolve => { release = resolve; }) }) });
  const first = handler(req());
  await new Promise(resolve => setTimeout(resolve, 20));
  assert.equal((await handler(req())).status, 429);
  release({}); await first;
  console.log('PASS per-process request budget and one in-flight operation');
  const stream = new ReadableStream({ start() {}, cancel() {} });
  const slow = req({}, { body: stream, duplex: 'half' });
  assert.equal((await createEvidenceHandler(deps)(slow)).status, 408);
  console.log('PASS stalled request body times out; synthetic offline only');
})().catch(error => { console.error(error); process.exitCode = 1; });
