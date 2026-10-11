/* eslint-disable @typescript-eslint/no-require-imports -- Node regression runner loads TS in isolated VM contexts. */
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const { createRequire } = require('node:module');
const { createHash } = require('node:crypto');
const ts = require('typescript');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const root = path.resolve(__dirname, '..');
const reportDir = path.resolve(root, '..', 'reports', 'morpheus-raw-offline-check-20261008T203523Z-1803526');
const qualityBytes = fs.readFileSync(path.join(reportDir, 'quality_report.json'));
const parityBytes = fs.readFileSync(path.join(reportDir, 'parity_report.json'));
const actualQuality = JSON.parse(qualityBytes);
const actualParity = JSON.parse(parityBytes);
let passed = 0;
function load(relative, overrides = {}, globals = {}) {
  const filename = path.resolve(root, relative);
  const nativeRequire = createRequire(filename);
  const sandboxModule = { exports: {} };
  const code = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022, esModuleInterop: true },
  }).outputText;
  function localRequire(name) {
    if (Object.hasOwn(overrides, name)) return overrides[name];
    if (name === 'next/link') return function TestLink({ children, ...props }) { return React.createElement('a', props, children); };
    if (name.startsWith('.')) {
      const base = path.resolve(path.dirname(filename), name);
      const target = ['.ts', '.tsx'].map(ext => base + ext).find(file => fs.existsSync(file));
      if (target) return load(target, overrides, globals);
    }
    return nativeRequire(name);
  }
  vm.runInNewContext(code, {
    exports: sandboxModule.exports, module: sandboxModule, require: localRequire, Buffer, AbortSignal, Error,
    console: { error() {} }, process: { env: {}, cwd: () => root }, ...globals,
  }, { filename });
  return sandboxModule.exports;
}
async function test(name, run) { await run(); passed++; console.log(`PASS ${name}`); }
async function readQuality(overrides = {}) {
  const route = load('src/app/api/model-quality/route.ts', overrides);
  const response = await route.GET();
  return { status: response.status, headers: response.headers, data: await response.json() };
}
(async () => {
  const evidence = await readQuality();
  await test('real report values and file hashes are returned without rounding or replacements', () => {
    assert.equal(evidence.status, 200);
    assert.equal(evidence.headers.get('cache-control'), 'no-store');
    assert.deepEqual(evidence.data.quality, actualQuality);
    assert.equal(evidence.data.parity.rows, 1367);
    assert.equal(evidence.data.parity.raw_event_check.reconstructed_rows, 6546);
    assert.equal(evidence.data.source.quality_sha256, createHash('sha256').update(qualityBytes).digest('hex'));
    assert.equal(evidence.data.source.parity_sha256, createHash('sha256').update(parityBytes).digest('hex'));
    assert.equal(evidence.data.quality.production_ready, false);
    assert.ok(!('source_sha256' in evidence.data.parity.raw_event_check));
  });
  await test('missing reports return 503 without invented metrics', async () => {
    const result = await readQuality({ 'node:fs/promises': { readFile: async () => { const e = new Error('missing'); e.code = 'ENOENT'; throw e; } } });
    assert.equal(result.status, 503); assert.ok(result.data.error); assert.ok(!result.data.quality);
  });
  await test('invalid JSON, missing fields, incorrect counts, and threshold mismatch fail closed', async () => {
    const inputs = ['{broken', JSON.stringify({}), JSON.stringify({ ...actualQuality, overall: { ...actualQuality.overall, n: 0 } }), JSON.stringify({ ...actualQuality, threshold: 0.9 })];
    for (const input of inputs) {
      const result = await readQuality({ 'node:fs/promises': { readFile: async p => p.endsWith('quality_report.json') ? Buffer.from(input) : parityBytes } });
      assert.equal(result.status, 502); assert.ok(!result.data.quality);
    }
  });
  await test('quality UI displays actual development metrics, fail state, and N/A denominators', () => {
    const Component = load('src/app/model-quality.tsx').default;
    const html = renderToStaticMarkup(React.createElement(Component, { data: evidence.data }));
    for (const value of ['67.18%', '100.00%', '80.37%', '32.82%', '2901', '258', 'N/A', 'FAIL', 'DEVELOPMENT EVALUATION', actualParity.checkpoint_weights_sha256]) assert.ok(html.includes(value), value);
    const empty = renderToStaticMarkup(React.createElement(Component, { data: null }));
    assert.ok(!empty.includes('67.18%')); assert.ok(!empty.includes('PASS'));
  });
  await test('initial dashboard and /replay remain unknown with no fabricated counts', () => {
    const Component = load('src/app/dashboard.tsx').default;
    const html = renderToStaticMarkup(React.createElement(Component));
    assert.equal((html.match(/● unknown/g) || []).length, 13);
    assert.ok(!html.includes('● offline')); assert.ok(!html.includes('<strong>0</strong>'));
    const replay = renderToStaticMarkup(React.createElement(Component, { replayOnly: true }));
    assert.ok(replay.includes('id="replay"')); assert.ok(!replay.includes('id="live"'));
  });
  await test('live and replay OpenSearch queries remain separate; real zero scores survive', async () => {
    const queries = new Map();
    const fetch = async (url, options) => {
      queries.set(url, JSON.parse(options.body));
      const behavioral = url.endsWith('/replay-behavioral-v1/_search');
      const source = behavioral
        ? { event_uid: 'test-uid', schema_version: 'replay-behavioral-1', processing_mode: 'replay', production_ready: false, automated_response_allowed: false, analysis_state: 'limited_history' }
        : { event_uid: 'test-uid', id: 'spoof', high_severity_score: 0 };
      return { ok: true, json: async () => ({ hits: { total: { value: 1 }, hits: [{ _id: 'document-id', _index: 'index', _source: source }] } }) };
    };
    const replay = load('src/app/api/replay/events/route.ts', {}, { fetch, process: { env: { REPLAY_OPENSEARCH_URL: 'http://test.invalid' } } });
    const payload = await (await replay.GET()).json();
    assert.equal(payload.events[0].id, 'document-id'); assert.equal(payload.events[0].high_severity_score, 0);
    assert.equal(queries.size, 2);
    const severityQuery = queries.get('http://test.invalid/replay-severity-v1/_search');
    const behavioralQuery = queries.get('http://test.invalid/replay-behavioral-v1/_search');
    assert.deepEqual(severityQuery.query.bool.filter, [{ term: { processing_mode: 'replay' } }, { term: { schema_version: 'replay-severity-1' } }, { term: { production_ready: false } }]);
    // Behavioral uses dynamic mappings and validates schema/mode after reading.
    assert.ok(behavioralQuery._source.includes('schema_version'));
    assert.equal(payload.behavioral_joined, 1);
    assert.equal(payload.events[0].behavioral_analysis.analysis_state, 'limited_history');
    await load('src/app/api/events/route.ts', {}, { fetch, process: { env: { OPENSEARCH_URL: 'http://live.invalid' } } }).GET();
    assert.equal(queries.size, 3);
    assert.equal(queries.get('http://live.invalid/edrxdr-events-*/_search').query.bool.filter[0].term.processing_mode, 'live');
  });
  await test('unknown probes never become offline; DOCA is independent from BlueField', async () => {
    async function status(mode) {
      const execFile = (command, args, _options, callback) => {
        if (mode === 'missing') return callback(new Error('unavailable'));
        let stdout = '';
        if (command === 'docker') stdout = args[0] === 'inspect' ? (mode === 'stopped' ? 'false' : 'true') : (mode === 'stopped' ? 'exited' : 'running');
        if (command === 'systemctl') stdout = `LoadState=loaded\nActiveState=${mode === 'stopped' ? 'inactive' : 'active'}`;
        if (command === 'nvidia-smi') stdout = '    Fabric\n        State : Completed\n        Status : Success\n    Other\n        Status : Failed';
        callback(null, { stdout });
      };
      return await (await load('src/app/api/status/route.ts', { 'node:child_process': { execFile } }).GET()).json();
    }
    const unknown = await status('missing');
    for (const [key, value] of Object.entries(unknown)) if (!['checked_at', 'evidence'].includes(key)) assert.equal(value, 'unknown', key);
    const stopped = await status('stopped'); assert.equal(stopped.kafka, 'offline'); assert.equal(stopped.wazuhAgent, 'offline');
    const online = await status('running'); assert.equal(online.bluefield, 'online'); assert.equal(online.doca, 'unknown'); assert.equal(online.gpuFabric, 'online');
  });
  console.log(`${passed} regression groups passed.`);
})().catch(error => { console.error(error); process.exitCode = 1; });
