'use strict';
// Execute the complete dashboard bootstrap with a deliberately small DOM double.
// Fixtures are synthetic; this test never opens a network connection or a model.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(process.argv[2] || path.join(__dirname, '..'));
const core = fs.readFileSync(path.join(root, 'public/nexus/core.js'), 'utf8');
const app = fs.readFileSync(path.join(root, 'public/nexus/app.js'), 'utf8');

async function boot(page, source = app, apiFailure = false) {
  const elements = new Map(), calls = [], pending = [], mounted = [];
  function element() {
    return { innerHTML: '', textContent: '', style: {}, dataset: {}, hidden: true,
      previousElementSibling: {}, classList: { add() {}, remove() {}, toggle() {} },
      addEventListener() {}, setAttribute() {}, appendChild() {}, remove() {},
      querySelector() { return null; }, querySelectorAll() { return []; } };
  }
  function get(id) { if (!elements.has(id)) elements.set(id, element()); return elements.get(id); }
  const scope = { console, URL, AbortController,
    location: { hash: '#' + page, protocol: 'http:' },
    document: { activeElement: null, hidden: false, body: element(),
      getElementById: get, createElement: element, addEventListener() {} },
    localStorage: { getItem() { return null; }, setItem() {}, removeItem() {} },
    addEventListener() {}, scrollTo() {},
    setTimeout() { return 1; }, clearTimeout() {}, setInterval() { return 1; }, clearInterval() {},
    queueMicrotask(fn) { pending.push(fn); },
    NexusModelLab: { mount() { assert.match(get('main').innerHTML, /id="model-lab-root"/); mounted.push('model'); } },
    NexusDfpDiagnostic: { mount() { assert.match(get('main').innerHTML, /id="dfp-diagnostic-root"/); mounted.push('dfp'); } },
    async fetch(url, options) {
      calls.push({ url, method: options.method });
      assert.equal(url, '/api/v1/snapshot?hours=24');
      assert.equal(options.method, 'GET');
      if (apiFailure) return { ok: false, status: 503, json: async () => ({ error: 'SYNTHETIC_UNAVAILABLE' }) };
      const fixture = scope.SIEM.seed();
      fixture.meta.demo = false; // Synthetic test of the API-connected branch only.
      fixture.meta.write_enabled = false;
      return { ok: true, json: async () => fixture };
    } };
  scope.window = scope;
  vm.createContext(scope);
  vm.runInContext(core, scope, { filename: 'core.js', timeout: 3000 });
  vm.runInContext(source, scope, { filename: 'app.js', timeout: 3000 });
  for (let i = 0; i < 12; i++) { await Promise.resolve(); while (pending.length) pending.shift()(); }
  assert.equal(calls.length, 1, 'Bootstrap must reach its snapshot GET');
  assert(get('main').innerHTML.length > 50, 'Main content or module root must be rendered');
  assert(!get('main-nav').innerHTML.includes('#copilot'));
  return { get, mounted };
}

async function main() {
  // Reproduce the exact previous regression: syntax alone did not catch this.
  const broken = app.split('\n').filter(line => !/^  function (dfpDiagnosticPage|modelLabPage)\(/.test(line)).join('\n');
  await assert.rejects(boot('overview', broken), /dfpDiagnosticPage is not defined/);
  console.log('PASS: missing page handlers reproduce the blank Overview failure');
  for (const page of ['overview', 'alerts', 'allevents', 'endpoints', 'cases', 'logs', 'coverage', 'integrations', 'settings', 'modellab', 'dfpdiagnostic', 'copilot']) {
    const result = await boot(page);
    if (page === 'overview') assert.match(result.get('main').innerHTML, /Security overview/);
    if (page === 'modellab') assert(result.mounted.includes('model'));
    if (page === 'dfpdiagnostic') assert(result.mounted.includes('dfp'));
    if (page === 'copilot') assert.match(result.get('main').innerHTML, /decision-review\.html/);
    if (!['modellab', 'dfpdiagnostic'].includes(page)) assert.equal(result.get('sidebar-mode').textContent, 'API');
    console.log('PASS: complete bootstrap and read-only snapshot connection: ' + page);
  }
  const offline = await boot('overview', app, true);
  assert.match(offline.get('main').innerHTML, /Security overview/);
  assert.equal(offline.get('sidebar-mode').textContent, 'DEMO');
  console.log('PASS: API failure keeps visibly labelled DEMO content');
  console.log('DASHBOARD_BOOTSTRAP=PASS; SYNTHETIC_ONLY=True; NETWORK_CALLS=0');
}
main().catch(error => { console.error(error); process.exitCode = 1; });
