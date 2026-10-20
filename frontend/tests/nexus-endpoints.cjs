const assert = require('node:assert/strict');
const fs = require('node:fs');
const ts = require('typescript');

const source = fs.readFileSync('src/lib/nexus-endpoints.ts', 'utf8');

const compiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2020
  }
}).outputText;

const mod = {};
new Function('exports', compiled)(mod);

const build = mod.buildObservedEndpoints;
assert.equal(typeof build, 'function');

const rows = [
  {
    agent_id: '005',
    agent_name: 'kali-demo-20261016',
    agent_ip: '192.168.255.130',
    timestamp: '2026-10-15T22:00:00.000+0000'
  },
  {
    agent_id: '004',
    agent_name: 'windows-agent',
    agent_ip: '100.66.12.6',
    timestamp: '2026-10-15T22:02:00.000+0000'
  },
  {
    agent_id: '005',
    agent_name: 'kali-demo-20261016',
    agent_ip: '192.168.255.131',
    timestamp: '2026-10-15T22:05:00.000+0000'
  },
  {
    agent_id: '003',
    agent_name: 'oa-hgx-h100-bu-02',
    agent_ip: '127.0.0.1',
    timestamp: '2026-10-15T22:04:00.000+0000'
  },
  {
    agent_id: '000',
    agent_name: 'wazuh.manager',
    timestamp: '2026-10-15T22:06:00.000+0000'
  },
  {
    agent_id: 'invalid',
    agent_name: 'bad-agent',
    timestamp: '2026-10-15T22:07:00.000+0000'
  }
];

const endpoints = build(rows);

assert.deepEqual(
  endpoints.map(e => e.agent_id),
  ['003', '004', '005']
);
console.log('PASS: Three unique endpoint IDs');

const kali = endpoints.find(e => e.agent_id === '005');

assert.equal(kali.ip, '192.168.255.131');
assert.equal(kali.last_seen, '2026-10-15T22:05:00.000Z');
console.log('PASS: Latest Kali observation selected');

assert.ok(endpoints.every(e => e.status === 'unknown'));
assert.ok(endpoints.every(e => e.risk === null));
console.log('PASS: No fabricated health or risk');

assert.equal(build(null).length, 0);
assert.equal(build([]).length, 0);
console.log('PASS: Empty and invalid input handled');

const badTime = build([{
  agent_id: '006',
  agent_name: 'test-host',
  timestamp: 'invalid-date'
}]);

assert.equal(badTime[0].last_seen, null);
console.log('PASS: Invalid timestamp does not become current time');

console.log('\nENDPOINT REGRESSION: PASS');
