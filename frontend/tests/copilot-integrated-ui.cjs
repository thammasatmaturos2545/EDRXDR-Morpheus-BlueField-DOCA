const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
class Node {
  constructor(tag) { this.tag = tag; this.children = []; this.dataset = {}; this.events = {}; this.attributes = {}; this.text = ''; }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = nodes; this.text = ''; }
  setAttribute(name, value) { this.attributes[name] = value; }
  addEventListener(name, fn) { this.events[name] = fn; }
  set textContent(value) { this.text = String(value); this.children = []; }
  get textContent() { return this.text + this.children.map(n => n.textContent).join(''); }
  set innerHTML(_) { throw Error('Untrusted HTML sink'); }
}
function report() {
  return { saved_review_only: true, human_review_required: true, automated_response_allowed: false,
    generated_at: '2026-10-20T10:05:00+07:00', input_evidence_hash: 'a'.repeat(64),
    results: Array.from({ length: 8 }, (_, i) => {
      const uid = String(i + 1).padStart(64, '0');
      const claim = { text: 'Synthetic <script>not executable</script> (event_uid: '+uid+')', evidence_uids: [uid] };
      return { event_uid: uid, draft: { summary_th: claim, facts: [claim], hypotheses: [], unknowns: [], suggested_checks: [] },
        evidence: { ai_status: 'matched', ai_score: 0, wazuh_level: 7, rule_id: String(i + 1) } };
    }) };
}
async function mount({ statusCode = 200 } = {}) {
  const nodes = Object.fromEntries(['copilot-status','copilot-queue','copilot-detail','copilot-reload'].map(id => [id, new Node('div')]));
  const root = new Node('div'); root.querySelector = selector => nodes[selector.slice(1)];
  const state = { page: 'copilot' }, data = report(); const original = JSON.stringify(data);
  const scope = { state, AbortSignal, queueMicrotask,
    document: { getElementById: id => id === 'copilot-root' ? root : null, createElement: tag => new Node(tag) },
    fetch: async (url, options) => {
      assert.equal(url, '/api/nexus/v1/copilot/review'); assert.equal(options.cache, 'no-store');
      assert.equal(options.credentials, 'same-origin');
      return { status: statusCode, ok: statusCode === 200, json: async () => data };
    } };
  const app = fs.readFileSync(path.join(__dirname, '../public/nexus/app.js'), 'utf8');
  const start = app.indexOf('  /* COPILOT_INTEGRATED_PANEL_V1 */');
  const end = app.indexOf('  function render(preserve=false){', start);
  assert(start >= 0 && end > start);
  vm.runInNewContext(app.slice(start, end), scope);
  const shell = scope.copilotPage();
  assert(shell.includes('class="page-heading"')); assert(shell.includes('class="copilot-layout"'));
  assert(!shell.includes('<iframe')); assert(!shell.includes('copilot-review.html'));
  await new Promise(setImmediate);
  assert.equal(JSON.stringify(data), original); // Display formatting cannot modify saved evidence/drafts.
  return { ...nodes, state, root, scope };
}
function find(node, className) {
  if ((node.className || '').split(' ').includes(className)) return node;
  for (const child of node.children) { const result = find(child, className); if (result) return result; }
}
async function main() {
  const ui = await mount();
  assert.equal(ui['copilot-queue'].children.length, 8);
  assert(ui['copilot-detail'].textContent.includes('0.0 / 100'));
  const summary = find(ui['copilot-detail'], 'copilot-summary');
  assert(!summary.textContent.includes('event_uid:'));
  assert(summary.textContent.includes('<script>not executable</script>'));
  assert(ui['copilot-detail'].textContent.includes('โมเดลไม่ได้ระบุ'));
  console.log('PASS native NEXUS panels, 8-event queue, zero score and safe text rendering');
  ui['copilot-queue'].children[1].events.click({ stopPropagation() {} });
  assert(ui['copilot-detail'].textContent.includes('เหตุการณ์ 2'));
  assert.equal(ui['copilot-queue'].children[1].attributes['aria-pressed'], 'true');
  console.log('PASS selection changes only embedded detail panel');
  const denied = await mount({ statusCode: 401 });
  assert.equal(denied['copilot-queue'].children.length, 0);
  assert.equal(denied['copilot-status'].children[0].href, '/api/nexus/v1/copilot/review');
  console.log('PASS auth denial clears evidence and exposes only native sign-in link');
  const unavailable = await mount({ statusCode: 503 });
  assert.equal(unavailable['copilot-detail'].children.length, 0);
  assert(unavailable['copilot-status'].textContent.includes('ไม่พร้อมใช้งาน'));
  console.log('PASS unavailable response never shows prior summary');
  console.log('PASS 4 embedded UI groups; synthetic offline only, real browser check pending');
}
main().catch(e => { console.error(e); process.exitCode = 1; });
