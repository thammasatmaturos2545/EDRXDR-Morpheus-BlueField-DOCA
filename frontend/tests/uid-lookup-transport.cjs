const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const code = ts.transpileModule(fs.readFileSync(path.join(__dirname, '../src/lib/uid-lookup-server.ts'), 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 }
}).outputText;
const limit = 2 * 1024 * 1024;
async function attempt(chunks, options = {}) {
  let reads = 0, cancelled = false, released = false;
  const scope = { exports: {}, Buffer, URL, AbortSignal, TextDecoder, process: { env: {} },
    require: name => {
      if (name === './wazuh-source') return { resolveWazuhSource: () => { throw Error('No Docker allowed'); } };
      if (name === './uid-lookup') return { LOOKUP_INDEX: 'edrxdr-wazuh-uid-lookup-v1' };
      return require(name);
    },
    fetch: async (url, init) => {
      assert.equal(url, 'http://localhost:9200/edrxdr-wazuh-uid-lookup-v1/_msearch');
      assert.equal(init.method, 'POST'); assert.equal(init.redirect, 'error'); assert.equal(init.cache, 'no-store');
      return { ok: options.ok !== false, text: () => { throw Error('Unbounded text read forbidden'); },
        body: options.missing ? null : { getReader: () => ({
          read: async () => {
            if (options.readFailure) throw Error('stream failed');
            const value = chunks[reads++]; return value ? { done: false, value } : { done: true };
          },
          cancel: async () => { cancelled = true; if (options.cancelFailure) throw Error('cancel failed'); },
          releaseLock: () => { released = true; }
        }) }
      };
    }
  };
  vm.runInNewContext(code, scope);
  let value, error;
  try { value = await scope.exports.searchUidLookup('{}\n'); } catch (e) { error = e; }
  return { value, error, reads, cancelled, released };
}
(async () => {
  const bytes = Buffer.from('{"text":"ไทย"}');
  const valid = await attempt([bytes.subarray(0, 10), bytes.subarray(10)]);
  assert.ifError(valid.error); assert.equal(valid.value.text, 'ไทย'); assert(valid.released);
  console.log('PASS bounded stream preserves split UTF-8 and read-only request scope');
  const exact = await attempt([Buffer.from('{}'), Buffer.alloc(limit - 2, 32)]);
  assert.ifError(exact.error);
  const over = await attempt([Buffer.alloc(limit), Buffer.alloc(1), Buffer.from('never read')]);
  assert(over.error); assert.equal(over.reads, 2); assert(over.cancelled && over.released);
  const cancelFail = await attempt([Buffer.alloc(limit + 1)], { cancelFailure: true });
  assert(cancelFail.error && cancelFail.released);
  console.log('PASS exact 2 MiB accepted; oversized body stops and cancels before remaining data');
  for (const [chunks, options] of [
    [[Buffer.from('bad JSON')], {}], [[Buffer.from([0xff])], {}],
    [[], { readFailure: true }], [[], { missing: true }], [[], { ok: false }]
  ]) {
    const result = await attempt(chunks, options); assert(result.error);
    if (!options.missing && options.ok !== false) assert(result.released);
  }
  console.log('PASS malformed JSON/UTF-8, stream failure, missing body and HTTP failure reject');
  console.log('PASS 3 UID transport groups; mocked fetch only, no Docker or OpenSearch');
})().catch(error => { console.error(error); process.exitCode = 1; });
