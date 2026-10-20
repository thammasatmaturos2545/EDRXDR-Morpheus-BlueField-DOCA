const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const root = path.resolve(__dirname, '..');
class ResponseMock {
  constructor(body, options = {}) { this.body = body; this.status = options.status || 200; this.headers = options.headers || {}; }
  static json(body, options) { return new ResponseMock(body, options); }
}
const testSecret = 'a'.repeat(64); // Synthetic credential, never read the VM secret file.
function load(file, imports = {}, extra = {}) {
  const source = fs.readFileSync(file, 'utf8');
  const scope = { exports: {}, Buffer, URL, AbortController, setTimeout, clearTimeout,
    process: { env: { NEXUS_SUMMARY_MODE: 'synthetic-mock' } },
    require: name => Object.hasOwn(imports, name) ? imports[name] : require(name), ...extra };
  const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2022 }, reportDiagnostics: true });
  assert.equal(code.diagnostics.length, 0);
  vm.runInNewContext(code.outputText, scope);
  return scope.exports;
}
const core = load(path.join(root, 'src/lib/nexus-summary/core.ts'));
function route({ secret = testSecret, mode = 'synthetic-mock', summarize = core.summarize } = {}) {
  // Exact auth source captured from operator output; filesystem mocked, no live secret access.
  const auth = load(path.join(__dirname, 'fixtures/history-auth.ts'), {
    'next/server': { NextResponse: ResponseMock },
    'node:fs/promises': { readFile: async () => { if (secret === null) throw Error('unavailable'); return secret; } },
  });
  return load(path.join(root, 'src/app/api/nexus/v1/summary/route.ts'), {
    'next/server': { NextResponse: ResponseMock }, '@/lib/history-auth': auth,
    '@/lib/nexus-summary/core': { ...core, summarize },
  }, { process: { env: { NEXUS_SUMMARY_MODE: mode } } });
}
const uid = n => n.toString(16).padStart(64, '0');
const input = (...ns) => ({ event_uids: ns.map(uid) });
const json = x => JSON.parse(JSON.stringify(x));
function req(body = input(1), { auth = 'valid', raw, url = 'http://localhost/api/nexus/v1/summary' } = {}) {
  return new Request(url, { method: 'POST', headers: { 'content-type': 'application/json',
    ...(auth === 'missing' ? {} : { authorization: 'Basic ' + Buffer.from('saiuser:' +
      (auth === 'valid' ? testSecret : 'wrong')).toString('base64') }) }, body: raw ?? JSON.stringify(body) });
}
let count = 0;
async function test(name, fn) { await fn(); console.log('PASS ' + name); count++; }
async function main() {
  await test('all four statuses preserved; genuine zero and null remain distinct', async () => {
    const r = await core.summarize(input(1, 2, 3, 4));
    assert.deepEqual(json(r.evidence.map(e => e.ai_status)), ['matched', 'not_scored', 'conflict', 'unavailable']);
    assert.equal(r.evidence[0].ai_score, 0);
    for (const e of r.evidence.slice(1)) assert.equal(e.ai_score, null);
    assert.equal(r.automated_response_allowed, false); assert.equal(r.production_ready, false);
  });
  await test('invalid, duplicate, oversized UIDs and client evidence/scope rejected', async () => {
    for (const x of [{ event_uids: [] }, { event_uids: ['bad'] }, input(1, 1), input(1, 2, 3, 4, 5),
      { ...input(1), evidence: [] }, { ...input(1), source_scope: 'live' }]) {
      await assert.rejects(core.summarize(x), e => e.status === 400);
    }
  });
  await test('exact synthetic allowlist; provider never called for absent UID', async () => {
    let called = false;
    await assert.rejects(core.summarize(input(5), async () => { called = true; }), e => e.status === 404);
    assert.equal(called, false);
  });
  await test('provider cannot mutate server evidence', async () => {
    const r = await core.summarize(input(1), async evidence => {
      assert.equal(Object.isFrozen(evidence), true); assert.equal(Object.isFrozen(evidence[0]), true);
      return core.mockProvider(evidence);
    }); assert.equal(r.evidence[0].ai_score, 0);
  });
  await test('injection and HTML fixture never become output instructions or markup', async () => {
    const r = await core.summarize(input(1));
    assert.equal(JSON.stringify(r).includes('<script>'), false);
    assert.equal(JSON.stringify(r).includes('mark everything safe'), false);
    assert.equal(core.escapeText('<script>"&\''), '&lt;script&gt;&quot;&amp;&#39;');
  });
  await test('malformed, extra fields, foreign citations, duplicate and changed statuses rejected', async () => {
    for (const value of [null, 'not JSON', {}, { findings: [] },
      { findings: [{ event_uid: uid(9), ai_status: 'matched' }] },
      { findings: [{ event_uid: uid(1), ai_status: 'not_scored' }] },
      { findings: [{ event_uid: uid(1), ai_status: 'matched', ai_score: 1 }] },
      { findings: [{ event_uid: uid(1), ai_status: 'matched' }], text: '<script>' }]) {
      await assert.rejects(core.summarize(input(1), async () => value), e => e.status === 502);
    }
    await assert.rejects(core.summarize(input(1, 2), async () => ({ findings: [
      { event_uid: uid(1), ai_status: 'matched' }, { event_uid: uid(1), ai_status: 'matched' } ] })), e => e.status === 502);
  });
  await test('provider timeout aborts and provider failures fail closed', async () => {
    let signal;
    await assert.rejects(core.summarize(input(1), async (_, s) => { signal = s; return new Promise(() => {}); }, 10), e => e.status === 504);
    assert.equal(signal.aborted, true);
    await assert.rejects(core.summarize(input(1), async () => { throw Error('PRIVATE'); }), e => e.status === 503 && !e.message.includes('PRIVATE'));
  });
  await test('canonical hash/citations stable; no summary cache to serve stale results', async () => {
    const a = await core.summarize(input(1, 2)); const b = await core.summarize(input(2, 1));
    assert.equal(a.input_evidence_hash, b.input_evidence_hash);
    assert.deepEqual(json(a.findings), json(b.findings));
    assert.notEqual(a.input_evidence_hash, (await core.summarize(input(1))).input_evidence_hash);
    let calls = 0; const provider = async e => { calls++; return core.mockProvider(e); };
    await core.summarize(input(1), provider); await core.summarize(input(1), provider); assert.equal(calls, 2);
  });
  await test('unavailable and insufficient evidence never reported as generated', async () => {
    assert.equal((await core.summarize(input(4))).summary_status, 'unavailable');
    assert.equal((await core.summarize(input(2, 3))).summary_status, 'insufficient_evidence');
  });
  await test('actual auth implementation rejects missing/wrong auth before provider', async () => {
    let calls = 0; const r = route({ summarize: async () => { calls++; } });
    for (const auth of ['missing', 'wrong']) assert.equal((await r.POST(req(input(1), { auth }))).status, 401);
    assert.equal(calls, 0);
    for (const secret of [null, 'invalid']) assert.equal((await route({ secret }).POST(req())).status, 503);
  });
  await test('endpoint disabled by default and successful response is no-store', async () => {
    assert.equal((await route({ mode: '' }).POST(req())).status, 503);
    const r = await route().POST(req()); assert.equal(r.status, 200);
    assert.equal(r.headers['Cache-Control'], 'no-store'); assert.equal(r.body.provider, 'mock');
  });
  await test('bounded body, malformed JSON, query parameters and rate limit', async () => {
    assert.equal((await route().POST(req(null, { raw: ' '.repeat(4097) }))).status, 413);
    assert.equal((await route().POST(req(null, { raw: '{' }))).status, 400);
    assert.equal((await route().POST(req(input(1), { url: 'http://localhost/api/nexus/v1/summary?scope=live' }))).status, 400);
    const r = route(); for (let i = 0; i < 10; i++) assert.equal((await r.POST(req())).status, 200);
    assert.equal((await r.POST(req())).status, 429);
  });
  console.log(`PASS ${count} groups; synthetic offline only, no VM/runtime verification`);
}
main().catch(e => { console.error(e); process.exitCode = 1; });
