const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const id = 'a'.repeat(64);
function route({ stopped = false, reject = false, readFailure = false } = {}) {
  const calls = [], resolutions = [];
  const raw = { manager: { name: 'synthetic' }, agent: { id: '001', name: 'fixture' }, id: '1',
    timestamp: '2026-10-20T00:00:00Z', rule: { id: '5501', level: 0, description: 'Synthetic only' }, data: {} };
  const scope = { exports: {}, Buffer, Date, console: { error() {} },
    require: name => {
      if (name === 'next/server') return { NextResponse: { json: (data, options) => ({ data, status: options?.status || 200 }) } };
      if (name === '@/lib/wazuh-source') return { resolveWazuhSource: async service => {
        resolutions.push(service); if (reject) throw Error('Synthetic source identity failure');
        return { id, name: '/fixture', project: 'wazuh', service, running: !stopped, status: stopped ? 'exited' : 'running' };
      } };
      if (name === 'child_process') return { execFile: async (command, args) => {
        calls.push({ command, args }); if (readFailure) throw Error('Synthetic Docker outage');
        return { stdout: JSON.stringify(raw) + '\n' };
      } };
      if (name === 'util') return { promisify: fn => fn };
      if (name === '@/lib/wazuh-sampling') throw Error('Sampling WIP must not be required by isolated source commit');
      return require(name);
    } };
  vm.runInNewContext(ts.transpileModule(fs.readFileSync(path.join(__dirname, '../src/app/api/wazuh/route.ts'), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText, scope);
  return { GET: scope.exports.GET, calls, resolutions };
}
async function main() {
  const ok = route(), response = await ok.GET();
  assert.equal(response.status, 200); assert.equal(response.data.source.id, id);
  assert.equal(response.data.source.project, 'wazuh');
  assert.deepEqual(ok.resolutions, ['wazuh.manager']); assert.equal(ok.calls.length, 1);
  assert.equal(ok.calls[0].command, 'docker');
  assert.deepEqual(Array.from(ok.calls[0].args).slice(0, 5), ['exec', id, 'tail', '-n', '100']);
  console.log('PASS scoped resolver identity and exact validated ID used; sampling remains outside commit');
  for (const options of [{ stopped: true }, { reject: true }]) {
    const r = route(options), result = await r.GET();
    assert.equal(result.status, 503); assert.equal(result.data.total, null);
    assert.equal(result.data.alerts.length, 0); assert.equal(r.calls.length, 0);
  }
  console.log('PASS stopped or unverified manager makes no Docker read and never returns zero/healthy');
  const failed = route({ readFailure: true }), result = await failed.GET();
  assert.equal(result.status, 503); assert.equal(result.data.total, null);
  console.log('PASS Docker source-read failure is unavailable with null total');
  console.log('PASS 3 source-route groups; mocked Docker only');
}
main().catch(error => { console.error(error); process.exitCode = 1; });
