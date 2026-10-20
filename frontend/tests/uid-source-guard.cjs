const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const id = 'a'.repeat(64);
const other = 'b'.repeat(64);
const refs = [{ uid: '1'.padStart(64, '0'), index: 'wazuh-alerts-4.x-2026.10.20', id: 'synthetic' }];
const lib = path.resolve(__dirname, '../src/lib');
function fixture({ project = 'wazuh', ids = id + '\n', identity = {}, fail = '' } = {}) {
  const calls = [];
  async function docker(command, args) {
    assert.equal(command, 'docker'); calls.push(args);
    if (args[0] === fail) throw Error('Synthetic Docker outage');
    if (args[0] === 'ps') {
      assert(args.includes('label=com.docker.compose.project=wazuh'));
      assert(args.includes('label=com.docker.compose.service=wazuh.manager'));
      assert(args.includes('--no-trunc'));
      assert(!args.includes('{{.Names}}'));
      return { stdout: ids };
    }
    if (args[0] === 'inspect') {
      assert.equal(args.at(-1), id);
      assert(!args[2].includes('Env'));
      return { stdout: JSON.stringify({ id, name: '/synthetic-manager', project: 'wazuh',
        service: 'wazuh.manager', running: true, status: 'running', ...identity }) };
    }
    if (args[0] === 'exec') {
      assert.equal(args[1], id); // The exact validated ID, never a mutable name.
      assert.equal(args[2], 'python3');
      assert.deepEqual(JSON.parse(Buffer.from(args.at(-1), 'base64').toString()), refs);
      return { stdout: '{"docs":[]}' };
    }
    throw Error('Unexpected Docker action');
  }
  const cache = new Map();
  function load(name) {
    if (cache.has(name)) return cache.get(name);
    const scope = { exports: {}, Buffer, URL, AbortSignal,
      process: { env: { WAZUH_COMPOSE_PROJECT: project } },
      fetch: () => { throw Error('Unexpected network access'); },
      require: spec => spec.startsWith('./') ? load(spec.slice(2)) :
        spec.startsWith('@/lib/') ? load(spec.slice(6)) :
        spec === 'node:child_process' ? { execFile: docker } :
        spec === 'node:util' ? { promisify: fn => fn } : require(spec) };
    vm.runInNewContext(ts.transpileModule(fs.readFileSync(path.join(lib, name + '.ts'), 'utf8'), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
    }).outputText, scope);
    cache.set(name, scope.exports); return scope.exports;
  }
  return { module: load('uid-lookup-server'), calls };
}
let count = 0;
async function test(name, fn) { await fn(); count++; console.log('PASS ' + name); }
async function main() {
  await test('scoped discovery, inspected identity and exact container ID used', async () => {
    const f = fixture(); await f.module.readUidSources(refs);
    assert.deepEqual(f.calls.map(a => a[0]), ['ps', 'inspect', 'exec']);
  });
  await test('missing project fails before Docker access', async () => {
    const f = fixture({ project: '' }); await assert.rejects(f.module.readUidSources(refs));
    assert.equal(f.calls.length, 0);
  });
  await test('zero and multiple own containers never execute', async () => {
    for (const ids of ['', id + '\n' + other + '\n']) {
      const f = fixture({ ids }); await assert.rejects(f.module.readUidSources(refs));
      assert.equal(f.calls.some(a => a[0] === 'exec'), false);
    }
  });
  await test('other project, wrong service and replaced ID fail closed', async () => {
    for (const identity of [{ project: 'luckyfive_wazuh' }, { service: 'other' }, { id: other }]) {
      const f = fixture({ identity }); await assert.rejects(f.module.readUidSources(refs));
      assert.equal(f.calls.some(a => a[0] === 'exec'), false);
    }
  });
  await test('stopped own manager cannot fall back to another project', async () => {
    for (const identity of [{ running: false, status: 'exited' }, { running: true, status: 'paused' }]) {
      const f = fixture({ identity }); await assert.rejects(f.module.readUidSources(refs));
      assert.equal(f.calls.some(a => a[0] === 'exec'), false);
    }
  });
  await test('discovery, inspection and source-read failures propagate', async () => {
    for (const fail of ['ps', 'inspect', 'exec']) {
      const f = fixture({ fail }); await assert.rejects(f.module.readUidSources(refs));
      assert.equal(f.calls.at(-1)[0], fail);
    }
  });
  await test('empty batch uses no Docker; invalid refs fail before Docker', async () => {
    const f = fixture(); assert.equal((await f.module.readUidSources([])).docs.length, 0);
    await assert.rejects(f.module.readUidSources([{ ...refs[0], uid: 'bad' }]));
    assert.equal(f.calls.length, 0);
  });
  console.log(`PASS ${count} UID source isolation groups; mocked Docker only`);
}
main().catch(e => { console.error(e); process.exitCode = 1; });
