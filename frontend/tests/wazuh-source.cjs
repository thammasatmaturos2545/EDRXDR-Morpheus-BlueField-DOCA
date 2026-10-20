const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const source = fs.readFileSync(path.join(__dirname, '../src/lib/wazuh-source.ts'), 'utf8');
const ctx = { exports: {}, require, process };
vm.runInNewContext(ts.transpileModule(source, { compilerOptions: {
  module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022,
} }).outputText, ctx);
const resolve = ctx.exports.resolveWazuhSource;
const id = 'a'.repeat(64), other = 'b'.repeat(64);
const row = { id, name: '/our-manager', project: 'ours', service: 'wazuh.manager', running: true, status: 'running' };
let count = 0;
async function test(name, fn) { await fn(); count++; console.log('PASS', name); }
function reader(rows, state = row) {
  return async args => {
    if (args[0] === 'ps') {
      assert(args.includes('label=com.docker.compose.project=ours'));
      assert(args.includes('label=com.docker.compose.service=wazuh.manager'));
      return rows.filter(x => x.project === 'ours').map(x => x.id).join('\n');
    }
    assert.equal(args[0], 'inspect'); assert.equal(args.at(-1), id);
    assert(!args[2].includes('.Config.Env'));
    return JSON.stringify(state);
  };
}
(async () => {
  for (const rows of [[row,{id:other,project:'theirs'}],[{id:other,project:'theirs'},row]]) {
    await test('two projects/order isolation', async () => assert.equal((await resolve('wazuh.manager', reader(rows), 'ours')).id,id));
  }
  await test('missing configuration never calls Docker', async () => {
    await assert.rejects(resolve('wazuh.manager', async()=>{throw Error('must not run');}, ''), /WAZUH_COMPOSE_PROJECT/);
  });
  for (const rows of [[],[{id:other,project:'theirs'}],[row,row]]) {
    await test('missing/ambiguous source rejects', async()=>assert.rejects(resolve('wazuh.manager',reader(rows),'ours'), /exactly one/));
  }
  for (const override of [{id:other},{project:'theirs'},{service:'other'},{running:'true'}]) {
    await test('inspect mismatch rejects', async()=>assert.rejects(resolve('wazuh.manager',reader([row],{...row,...override}),'ours'), /validation/));
  }
  await test('stopped own container does not fall back', async()=>{
    assert.equal((await resolve('wazuh.manager',reader([row,{id:other,project:'theirs'}],{...row,running:false,status:'exited'}),'ours')).running,false);
  });
  await test('Docker outage propagates', async()=>assert.rejects(resolve('wazuh.manager',async()=>{throw Error('timeout');},'ours'),/timeout/));
  await test('malformed inspection rejects', async()=>assert.rejects(resolve('wazuh.manager',async a=>a[0]==='ps'?id:'not-json','ours')));
  console.log(`PASS ${count} resolver scenarios`);
})().catch(e=>{console.error(e);process.exitCode=1;});
