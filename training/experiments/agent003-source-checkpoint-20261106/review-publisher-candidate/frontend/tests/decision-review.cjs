const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const ts = require('typescript');
const root = path.resolve(__dirname, '..');
const api = 'http://lab/api/nexus/v1/decisions';
const authorization = 'Basic ' + Buffer.from('synthetic:synthetic-password-only').toString('base64');
const hash = 'a'.repeat(64);

function loadRoute(options = {}) {
  let calls = 0;
  const environment = options.environment || { NEXUS_DECISION_REVIEW_ENABLED: '1', NEXUS_DECISION_CATALOG_SHA256: hash };
  const imports = {
    'next/server': { NextResponse: { json: (body, init) => ({ body, ...init }) } },
    '@/lib/decision-review': { runDecisionReview: async (...args) => {
      calls++; return options.worker ? options.worker(...args) : { status: 200, body: { response_executed: false } };
    } },
  };
  const code = ts.transpileModule(fs.readFileSync(path.join(root, 'src/app/api/nexus/v1/decisions/route.ts'), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const scope = { exports: {}, require: id => imports[id] || require(id), process: { env: environment },
    URL, Buffer, TextDecoder, setTimeout: options.timer || setTimeout, clearTimeout };
  vm.runInNewContext(code, scope);
  return { route: scope.exports, calls: () => calls };
}
function post(body, headers = {}) {
  return new Request(api, { method: 'POST', headers: {
    authorization, origin: 'http://lab', 'content-type': 'application/json', ...headers,
  }, body: typeof body === 'string' ? body : JSON.stringify(body) });
}
let groups = 0;
async function test(name, fn) { await fn(); groups++; console.log('PASS ' + name); }

class Node {
  constructor(tag) { this.tag = tag; this.children = []; this.events = {}; this.hidden = false; this.disabled = false; this.text = ''; }
  append(...values) { this.children.push(...values); }
  replaceChildren(...values) { this.children = values; this.text = ''; }
  addEventListener(name, fn) { this.events[name] = fn; }
  setAttribute() {}
  focus() {}
  set value(value) { this.selected = value; }
  get value() { return this.selected ?? this.children[0]?.value ?? ''; }
  set textContent(value) { this.text = String(value); this.children = []; }
  get textContent() { return this.text + this.children.map(child => child.textContent).join(''); }
  set innerHTML(_) { throw Error('Unsafe HTML sink'); }
}
function fixture(role = 'reviewer') {
  return { schema_version: 'nexus-human-review-v1', automated_response_allowed: false, response_execution_enabled: false,
    principal: { actor_ref: 'synthetic-reviewer', role }, items: [{
      alert_id: hash, alert_revision: 'b'.repeat(64), endpoint_id: '003', pipeline: 'dfp',
      source_mode: 'controlled-test', validation_status: 'experimental', coverage_status: 'unknown',
      event_time: '2026-11-05T00:00:00Z', detected_at: '2026-11-05T00:01:00Z',
      detector_id: 'synthetic', detector_version: 'test', score: 0, score_semantics: 'reconstruction-error',
      findings: ['<script>untrusted</script>'], limitations: ['Synthetic only'],
      recommendation: { action: 'investigate', reason: 'Review evidence' },
      feature_contract: 'synthetic-six', evidence_refs: [], history: [], latest_seq: 0,
    }] };
}
function browser(fetch) {
  const elements = Object.fromEntries(['status', 'list', 'auth', 'filter', 'reload'].map(id => [id, new Node('div')]));
  elements.filter.value = 'all';
  const code = fs.readFileSync(path.join(root, 'public/nexus/decision-review.js'), 'utf8');
  vm.runInNewContext(code, { document: { getElementById: id => elements[id], createElement: tag => new Node(tag) },
    fetch, AbortSignal, crypto: { getRandomValues: bytes => crypto.webcrypto.getRandomValues(bytes) }, Uint8Array });
  return elements;
}
function find(node, match) {
  if (match(node)) return node;
  for (const child of node.children) { const found = find(child, match); if (found) return found; }
}
const tick = () => new Promise(setImmediate);

async function main() {
  await test('worker uses fixed executable and private root; credentials only on stdin', async () => {
    let received, args, options;
    const code = ts.transpileModule(fs.readFileSync(path.join(root, 'src/lib/decision-review.ts'), 'utf8'), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
    }).outputText;
    const scope = { exports: {}, process: { cwd: () => root }, require: id => id === 'node:child_process' ? {
      execFile: (executable, passed, config, callback) => {
        assert.equal(executable, 'python3'); args = passed; options = config;
        return { stdin: { on() {}, end(value) {
          received = JSON.parse(value);
          setImmediate(() => callback(null, JSON.stringify({ status: 200, body: { response_executed: false } })));
        } } };
      },
    } : require(id) };
    vm.runInNewContext(code, scope);
    const result = await scope.exports.runDecisionReview({ method: 'GET', authorization, body: null }, hash);
    assert.equal(received.authorization, authorization); assert.equal(result.status, 200);
    assert(args.includes('/mnt/nexus-copilot-mQTssj/nexus-human-review-v1'));
    assert.equal(args.includes(authorization), false); assert.equal(options.timeout, 8000);
    assert.equal(options.shell, undefined);
  });
  await test('disabled, unpinned, auth format and browser path gates perform no worker IO', async () => {
    for (const environment of [{}, { NEXUS_DECISION_REVIEW_ENABLED: '1' }]) {
      const r = loadRoute({ environment }); assert.equal((await r.route.GET(new Request(api))).status, 503); assert.equal(r.calls(), 0);
    }
    const r = loadRoute(); assert.equal((await r.route.GET(new Request(api))).status, 401);
    assert.equal((await r.route.GET(new Request(api + '?path=/private', { headers: { authorization } }))).status, 400);
    assert.equal(r.calls(), 0);
  });
  await test('cross-origin and missing POST origin rejected before worker', async () => {
    const r = loadRoute();
    for (const headers of [{ origin: 'http://other' }, { 'sec-fetch-site': 'cross-site' }])
      assert.equal((await r.route.POST(post({}, headers))).status, 403);
    const request = post({}); request.headers.delete('origin');
    assert.equal((await r.route.POST(request)).status, 403); assert.equal(r.calls(), 0);
  });
  await test('chunked, malformed, oversized and invalid content types rejected', async () => {
    const r = loadRoute();
    for (const request of [post('{'), post('x'.repeat(4097)), post({}, { 'content-type': 'text/plain' }),
      post({}, { 'content-length': '5000' })]) assert.equal((await r.route.POST(request)).status, 400);
    assert.equal(r.calls(), 0);
  });
  await test('stalled body times out without invoking worker', async () => {
    const r = loadRoute({ timer: (fn) => setTimeout(fn, 1) });
    const headers = new Headers({ authorization, origin: 'http://lab', 'content-type': 'application/json' });
    const request = { url: api, headers, body: new ReadableStream({ start() {} }) };
    assert.equal((await r.route.POST(request)).status, 400); assert.equal(r.calls(), 0);
  });
  await test('server gets raw credentials only through worker and returns no-store named auth errors', async () => {
    const r = loadRoute({ worker: async (input, pin) => {
      assert.equal(input.authorization, authorization); assert.equal(pin, hash);
      assert.equal(input.method, 'POST'); assert.equal(input.body.reason, 'synthetic');
      return { status: 401, body: { error: 'AUTH_REQUIRED' } };
    } });
    const response = await r.route.POST(post({ reason: 'synthetic' }));
    assert.equal(response.status, 401); assert.equal(response.headers['Cache-Control'], 'no-store');
    assert(response.headers['WWW-Authenticate'].includes('Named Reviewers'));
  });
  await test('bounded concurrency and worker failures fail closed', async () => {
    let release; const hold = new Promise(resolve => release = resolve);
    const r = loadRoute({ worker: async () => { await hold; throw Error('PRIVATE ERROR'); } });
    const request = () => new Request(api, { headers: { authorization } });
    const first = r.route.GET(request()), second = r.route.GET(request());
    await tick(); assert.equal((await r.route.GET(request())).status, 503);
    release();
    const results = await Promise.all([first, second]);
    assert(results.every(result => result.status === 503 && !JSON.stringify(result).includes('PRIVATE')));
  });
  await test('UI renders safe text, zero score, experimental mode and viewer restrictions', async () => {
    const data = fixture('viewer');
    const ui = browser(async () => ({ ok: true, status: 200, json: async () => data })); await tick();
    assert.equal(ui.list.children.length, 1); assert(ui.list.textContent.includes('<script>untrusted</script>'));
    assert(find(ui.list, node => node.tag === 'button').disabled);
    assert(ui.list.textContent.includes('ผลทดลอง')); assert(ui.list.textContent.includes('ไม่มีคะแนน') === false);
  });
  await test('UI saves only reviewer intent and retries the same request after an uncertain result', async () => {
    const bodies = []; let fail = true;
    const ui = browser(async (url, options = {}) => {
      assert.equal(url, '/api/nexus/v1/decisions');
      if (options.method === 'POST') {
        const body = JSON.parse(options.body); bodies.push(body);
        if (fail) { fail = false; throw Error('network'); }
        return { ok: true, status: 200, json: async () => ({ response_executed: false, decision: body }) };
      }
      return { ok: true, status: 200, json: async () => fixture() };
    }); await tick();
    const note = find(ui.list, node => node.tag === 'textarea'); note.value = 'Synthetic review';
    const save = find(ui.list, node => node.tag === 'button');
    await save.events.click(); assert.equal(bodies.length, 1); assert.equal(note.disabled, true);
    await save.events.click(); assert.deepEqual(bodies[0], bodies[1]);
    assert.match(bodies[0].request_id, /^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/);
    assert.equal(Object.hasOwn(bodies[0], 'actor_ref'), false); assert.equal(Object.hasOwn(bodies[0], 'execute'), false);
    assert(ui.status.textContent.includes('ไม่มีการส่งคำสั่ง'));
  });
  await test('UI clears stale observations on auth/outage and never falls back to synthetic data', async () => {
    let state = 200;
    const ui = browser(async () => ({ ok: state === 200, status: state, json: async () => fixture() })); await tick();
    assert.equal(ui.list.children.length, 1); state = 401; await ui.reload.events.click();
    assert.equal(ui.list.children.length, 0); assert.equal(ui.auth.hidden, false);
    state = 503; await ui.reload.events.click(); assert.equal(ui.list.children.length, 0);
  });
  await test('UI conflict reloads current history without automatically submitting another decision', async () => {
    let posts = 0;
    const ui = browser(async (url, options = {}) => {
      if (options.method === 'POST') { posts++; return { ok: false, status: 409 }; }
      return { ok: true, status: 200, json: async () => fixture() };
    }); await tick();
    find(ui.list, node => node.tag === 'textarea').value = 'Synthetic stale decision';
    await find(ui.list, node => node.tag === 'button').events.click();
    assert.equal(posts, 1); assert(ui.status.textContent.includes('เปลี่ยนแล้ว'));
    assert.equal(find(ui.list, node => node.tag === 'textarea').disabled, false);
  });
  await test('old decision shows original evidence and recommendation as literal text', async () => {
    const data = fixture(); const row = data.items[0];
    row.history = [{ action: 'agree_recommendation', reason: 'Prior human decision', actor_ref: 'synthetic-reviewer',
      decided_at: '2026-11-05T00:01:00Z', alert_revision: 'd'.repeat(64) }];
    row.revision_evidence = { ['d'.repeat(64)]: { detector_id: 'prior-detector', detector_version: 'prior-version',
      feature_contract: 'synthetic', findings: ['prior finding'], limitations: ['prior limitation'], evidence_refs: [],
      recommendation: { action: 'investigate', reason: 'prior recommendation <script>literal</script>' } } };
    const ui = browser(async () => ({ ok: true, status: 200, json: async () => data })); await tick();
    assert(ui.list.textContent.includes('prior recommendation <script>literal</script>'));
    assert(ui.list.textContent.includes('คำตัดสินต่อข้อมูลรุ่นก่อน'));
  });
  await test('retired alert disables new decisions for named reviewer', async () => {
    const data = fixture(); data.items[0].retired = true;
    const ui = browser(async () => ({ ok: true, status: 200, json: async () => data })); await tick();
    assert(find(ui.list, node => node.tag === 'button').disabled);
    assert(find(ui.list, node => node.tag === 'textarea').disabled);
    assert(ui.list.textContent.includes('รายการเก่า อ่านประวัติเท่านั้น'));
  });
  await test('missing prior evidence is explicit and never substituted with current recommendation', async () => {
    const data = fixture(); data.items[0].history = [{ action: 'no_action', reason: 'Prior reason', actor_ref: 'synthetic',
      decided_at: '2026-11-05T00:01:00Z', alert_revision: 'd'.repeat(64) }];
    const ui = browser(async () => ({ ok: true, status: 200, json: async () => data })); await tick();
    assert(ui.list.textContent.includes('ยังไม่มีสำเนาหลักฐานรุ่นนี้'));
  });
  await test('v2 evidence keeps identity contract and native loss explicit', async () => {
    const data = fixture(); data.schema_version = 'nexus-human-review-v2';
    data.items[0].score = 125.5;
    data.items[0].evidence_refs = [{ record_ref: 'd'.repeat(64), identity_contract: 'synthetic-journal-reference-1', sha256: 'e'.repeat(64) }];
    const ui = browser(async () => ({ ok: true, status: 200, json: async () => data })); await tick();
    assert.equal(ui.list.children.length, 1);
    assert(ui.list.textContent.includes('synthetic-journal-reference-1'));
    assert(ui.list.textContent.includes('125.5'));
  });
  await test('unsupported catalog schema displays no score facts', async () => {
    const data = fixture(); data.schema_version = 'unrecognized-schema';
    const ui = browser(async () => ({ ok: true, status: 200, json: async () => data })); await tick();
    assert.equal(ui.list.children.length, 0);
  });
  console.log(`DECISION_REVIEW_API_UI_GROUPS=${groups}; SYNTHETIC_ONLY=True`);
}
main().catch(error => { console.error(error); process.exitCode = 1; });
