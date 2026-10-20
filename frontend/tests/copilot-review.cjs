const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const root = path.resolve(__dirname, '..');
function load(file, imports, extra = {}) {
  const scope = { exports: {}, Buffer, URL, process: { env: { NEXUS_COPILOT_REVIEW: 'saved-eight' } },
    require: n => Object.hasOwn(imports, n) ? imports[n] : require(n), ...extra };
  vm.runInNewContext(ts.transpileModule(fs.readFileSync(file, 'utf8'), { compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022,
  } }).outputText, scope); return scope.exports;
}
const core = load(path.join(root, 'src/lib/copilot-review.ts'), {});
function fixture() {
  return { provider: 'local-vllm', model: 'nexus-gpt-oss-20b', model_revision: '6cee5e81ee83917806bbde320786a8fb61efebee',
    prompt_version: 'soc-local-th-v1', production_ready: false, automated_response_allowed: false,
    external_transfer_allowed: false, human_review_required: true,
    finished_at: '2026-10-20T10:00:00+07:00', input_evidence_hash: 'a'.repeat(64), input_file_sha256: 'b'.repeat(64),
    private_debug: 'PRIVATE_SECRET', results: core.REVIEW_UIDS.map(uid => {
      const claim = { text: 'ข้อความสังเคราะห์ <script>untrusted</script>', evidence_uids: [uid] };
      return { event_uid: uid, status: 'generated_unreviewed', automated_response_allowed: false,
        draft: { summary_th: claim, facts: [claim], hypotheses: [], unknowns: [], suggested_checks: [] },
        trusted_evidence: { event_uid: uid, evidence_status: 'matched', source_ref: { index: 'wazuh-alerts-4.x-2026.10.20', id: 'synthetic' },
          fact: { event_uid: uid, ai_status: 'matched', ai_score: 0, ai_label: 'low_severity',
            wazuh_level: 0, rule_id: '5501', timestamp_utc: null, description: 'Synthetic rule', raw_json: 'PRIVATE_LOG' } } };
    }) };
}
function route({ auth = null, enabled = true, value = fixture(), symlink = false, oversized = false } = {}) {
  let reads = 0, closed = false, position = 0;
  const report = '/mnt/nexus-copilot-mQTssj/results/summary-eight-vone0xsh/result.json';
  const bytes = Buffer.from(JSON.stringify(value));
  const file = { stat: async () => ({ isFile: () => true, size: oversized ? 256 * 1024 + 1 : bytes.length }),
    read: async (target, offset, length) => {
      const count = Math.min(37, length, bytes.length - position);
      bytes.copy(target, offset, position, position + count); position += count; return { bytesRead: count };
    }, close: async () => { closed = true; } };
  const module = load(path.join(root, 'src/app/api/nexus/v1/copilot/review/route.ts'), {
    'next/server': { NextResponse: { json: (data, options) => ({ data, ...options }) } },
    '@/lib/history-auth': { requireHistoryAuth: async () => auth }, '@/lib/copilot-review': core,
    'node:fs/promises': { realpath: async () => { reads++; return symlink ? '/other' : report; },
      open: async () => { reads++; return file; } },
  }, { process: { env: { NEXUS_COPILOT_REVIEW: enabled ? 'saved-eight' : '' } } });
  return { module, reads: () => reads, closed: () => closed };
}
let count = 0;
async function test(name, fn) { await fn(); count++; console.log('PASS ' + name); }
async function main() {
  await test('eight saved UIDs, original zero score, plain text and allowlist projection', () => {
    const r = core.parseCopilotReview(fixture()); assert.equal(r.results.length, 8);
    assert.equal(r.results[0].evidence.ai_score, 0);
    assert.equal(JSON.stringify(r).includes('PRIVATE_'), false);
    assert.equal(r.automated_response_allowed, false); assert.equal(r.human_review_required, true);
  });
  await test('foreign/duplicate UID, citation, score and safety flags fail closed', () => {
    for (const change of [x => x.results[0].event_uid = 'f'.repeat(64),
      x => x.results[1] = x.results[0], x => x.results[0].draft.facts[0].evidence_uids = ['f'.repeat(64)],
      x => x.results[0].trusted_evidence.fact.ai_score = -1, x => x.production_ready = true,
      x => x.model_revision = 'wrong', x => x.results[0].status = 'approved']) {
      const value = fixture(); change(value); assert.throws(() => core.parseCopilotReview(value));
    }
  });
  await test('auth denial and default-disabled route read no report', async () => {
    const denied = route({ auth: { status: 401 } }); assert.equal((await denied.module.GET({ url: 'http://local/api' })).status, 401);
    assert.equal(denied.reads(), 0);
    const disabled = route({ enabled: false }); assert.equal((await disabled.module.GET({ url: 'http://local/api' })).status, 503);
    assert.equal(disabled.reads(), 0);
  });
  await test('bounded chunked read, no-store response and file handle closed', async () => {
    const r = route(); const result = await r.module.GET({ url: 'http://local/api' });
    assert.equal(result.status, 200); assert.equal(result.data.results.length, 8);
    assert.equal(result.headers['Cache-Control'], 'no-store'); assert.equal(r.closed(), true);
  });
  await test('client paths, symlink, oversized and malformed report rejected', async () => {
    const query = route(); assert.equal((await query.module.GET({ url: 'http://local/api?path=/etc/passwd' })).status, 400);
    assert.equal(query.reads(), 0);
    for (const options of [{ symlink: true }, { oversized: true }, { value: {} }]) {
      const r = route(options); assert.equal((await r.module.GET({ url: 'http://local/api' })).status, 503);
    }
  });
  await test('browser renders untrusted text without HTML sinks or credentials storage', async () => {
    class Node {
      constructor(tag) { this.tag = tag; this.children = []; this.style = {}; this.events = {}; this.text = ''; }
      append(...nodes) { this.children.push(...nodes); }
      replaceChildren(...nodes) { this.children = nodes; this.text = ''; }
      addEventListener(name, fn) { this.events[name] = fn; }
      get firstChild() { return this.children[0]; }
      set value(v) { this.selectedValue = v; }
      get value() { return this.selectedValue ?? this.children[0]?.value ?? ''; }
      set textContent(value) { this.text = String(value); this.children = []; }
      get textContent() { return this.text + this.children.map(n => n.textContent).join(''); }
      set innerHTML(_) { throw Error('Unsafe HTML sink'); }
    }
    const elements = Object.fromEntries(['status','list','filter','auth','reload'].map(id => [id, new Node('div')]));
    const report = core.parseCopilotReview(fixture());
    vm.runInNewContext(fs.readFileSync(path.join(root, 'public/nexus/copilot-review.js'), 'utf8'), {
      document: { getElementById: id => elements[id], createElement: tag => new Node(tag) }, AbortSignal,
      fetch: async () => ({ ok: true, status: 200, json: async () => report }),
    });
    await new Promise(setImmediate);
    assert.equal(elements.list.children.length, 8);
    assert(elements.list.textContent.includes('<script>untrusted</script>'));
    elements.filter.value = core.REVIEW_UIDS[0]; elements.filter.events.change();
    assert.equal(elements.list.children.length, 1);
  });
  console.log(`PASS ${count} saved-review API/UI groups; synthetic offline only`);
}
main().catch(e => { console.error(e); process.exitCode = 1; });
