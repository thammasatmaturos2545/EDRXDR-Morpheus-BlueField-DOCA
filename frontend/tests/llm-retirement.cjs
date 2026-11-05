const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const root = path.resolve(__dirname, '..');
function load(relative, imports) {
  const code = ts.transpileModule(fs.readFileSync(path.join(root, relative), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const scope = { exports: {}, require: name => {
    assert(Object.hasOwn(imports, name), 'Unapproved dependency: ' + name); return imports[name];
  }, process: { env: { NEXUS_COPILOT_DRAFT: 'local-vllm', NEXUS_COPILOT_REVIEW: 'saved-eight',
    NEXUS_COPILOT_EVIDENCE: 'local-preview', NEXUS_SUMMARY_MODE: 'synthetic-mock' } } };
  vm.runInNewContext(code, scope); return scope.exports;
}
let groups = 0;
async function test(name, run) { await run(); groups++; console.log('PASS ' + name); }
async function main() {
  await test('all retired endpoints authenticate and return 410 even with legacy enable flags', async () => {
    let allowed = false, checks = 0;
    const helper = load('src/lib/retired-summary.ts', {
      'next/server': { NextResponse: { json: (body, init) => ({ body, ...init }) } },
      '@/lib/history-auth': { requireHistoryAuth: async () => { checks++; return allowed ? null : { status: 401 }; } },
    });
    for (const route of ['copilot/draft', 'copilot/review', 'copilot/evidence', 'summary']) {
      const module = load('src/app/api/nexus/v1/' + route + '/route.ts', { '@/lib/retired-summary': helper });
      for (const method of ['GET', 'POST']) {
        const request = { get body() { throw Error('Retired body must not be read'); } };
        allowed = false; assert.equal((await module[method](request)).status, 401);
        allowed = true; const response = await module[method](request);
        assert.equal(response.status, 410); assert.equal(response.body.llm_summary_enabled, false);
        assert.equal(response.body.response_execution_enabled, false);
        assert.equal(response.headers['Cache-Control'], 'no-store');
      }
    }
    assert.equal(checks, 16);
  });
  await test('active dashboard scripts and All Events contain no Copilot model requests or controls', () => {
    const html = fs.readFileSync(path.join(root, 'public/nexus/index.html'), 'utf8');
    const scripts = [...html.matchAll(/<script[^>]+src="([^"]+)"/g)].map(match => match[1]);
    assert(!scripts.some(file => /copilot|llm/i.test(file)));
    assert(html.includes('decision-review.html'));
    for (const file of ['app.js', 'all-events.js']) {
      const code = fs.readFileSync(path.join(root, 'public/nexus', file), 'utf8');
      new vm.Script(code);
      assert(!code.includes('/api/nexus/v1/copilot'));
      assert(!code.includes('NexusCopilotEvidence'));
      assert(!code.includes('gpt-oss'));
    }
    const history = fs.readFileSync(path.join(root, 'public/nexus/all-events.js'), 'utf8');
    assert(history.includes('/api/nexus/v1/history?')); assert(history.includes('addAiCell(tr, event)'));
  });
  await test('rendered navigation excludes Copilot and old bookmarks show only a retirement notice', () => {
    const code = fs.readFileSync(path.join(root, 'public/nexus/app.js'), 'utf8');
    const source = ts.createSourceFile('app.js', code, ts.ScriptTarget.Latest, true, ts.ScriptKind.JS);
    assert.equal(source.parseDiagnostics.length, 0);
    const functions = {};
    function visit(node) {
      if (ts.isFunctionDeclaration(node) && node.name) functions[node.name.text] = node.getText(source);
      ts.forEachChild(node, visit);
    }
    visit(source);
    const nodes = { 'main-nav': {}, 'breadcrumb-current': {} };
    const scope = { C: { stats: () => ({ critical: 0 }) }, state: { data: {}, range: '24h', page: 'overview' },
      referenceTime: () => 0, icon: () => '', pages: { overview: 'Overview' },
      $: id => nodes[id], setModeInfo() {} };
    vm.runInNewContext(functions.nav + ';nav();', scope);
    assert(!nodes['main-nav'].innerHTML.includes('#copilot'));
    for (const page of ['#allevents', '#modellab', '#dfpdiagnostic']) assert(nodes['main-nav'].innerHTML.includes(page));
    vm.runInNewContext(functions.retiredCopilotPage + ';result=retiredCopilotPage();', scope);
    assert(scope.result.includes('decision-review.html'));
    assert(!scope.result.includes('<script')); assert(!scope.result.includes('fetch('));
    const standalone = fs.readFileSync(path.join(root, 'public/nexus/copilot-review.html'), 'utf8');
    assert(standalone.includes('decision-review.html')); assert(!standalone.includes('<script'));
  });
  console.log(`LLM_RETIREMENT_GROUPS=${groups}; MODEL_NETWORK_GPU_CALLS=0; SYNTHETIC_ONLY=True`);
}
main().catch(error => { console.error(error); process.exitCode = 1; });
