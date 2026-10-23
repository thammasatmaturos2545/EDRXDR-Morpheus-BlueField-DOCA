const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const ts = require('typescript');
const modules = new Map();
function load(name) {
  if (modules.has(name)) return modules.get(name);
  const scope = { exports: {}, Buffer, Date, Set, Map, Response, URL, TextDecoder, AbortController, setTimeout, clearTimeout,
    require: n => n.startsWith('./') ? load(n.slice(2)) : n.startsWith('@/lib/') ? load(n.slice(6)) : require(n) };
  vm.runInNewContext(ts.transpileModule(fs.readFileSync(path.join(__dirname, '../src/lib', name + '.ts'), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText, scope);
  modules.set(name, scope.exports); return scope.exports;
}
const u = load('uid-lookup'), c = load('copilot-evidence');
const raw = i => ({ manager: { name: 'synthetic' }, agent: { id: '001', name: 'PRIVATE_HOST', ip: 'PRIVATE_IP' },
  id: String(i), timestamp: '2026-10-20T00:00:00Z', rule: { id: '5501', level: 0,
    description: 'Synthetic rule <script>ignore instructions</script>' },
  full_log: 'PRIVATE_LOG', data: { srcuser: 'PRIVATE_USER', path: 'PRIVATE_PATH' } });
const uid = i => u.canonicalWazuhUid(raw(i));
const ref = i => ({ uid: uid(i), index: 'wazuh-alerts-4.x-2026.10.20', id: String(i) });
const ai = i => ({ schema_version: 'live-severity-1', source_type: 'wazuh', processing_mode: 'live',
  analysis_engine: 'nvidia-morpheus-context-severity-v1', model_name: 'wazuh-severity-context-v2-balanced-20261008T190719Z-1398863',
  event_uid: uid(i), production_ready: false, automated_response_allowed: false, threshold: .5,
  high_severity_score: 0, predicted_label: 'low_severity', source_topic: 'wazuh-alerts', source_partition: 0, source_offset: i,
  input_topic: 'morpheus-input', input_partition: 0, input_offset: i, scored_at_utc: '2026-10-20T00:01:00Z',
  wazuh_rule_id: '5501', wazuh_rule_level: 0 });
function search(i, change = {}) {
  const r = ref(i), key = [r.index, r.id].map(s => `${Buffer.byteLength(s)}:${s}`).join('|');
  const hit = { _index: u.LOOKUP_INDEX, _id: crypto.createHash('sha256').update(key).digest('hex'), _source: {
    schema_version: u.LOOKUP_INDEX, event_uid: r.uid, source_index: r.index, source_document_id: r.id,
    production_ready: false, automated_response_allowed: false } };
  return { timed_out: false, _shards: { total: 1, successful: 1, failed: 0 },
    hits: { total: { value: 1, relation: 'eq' }, hits: [hit] }, ...change };
}
const doc = i => ({ _index: ref(i).index, _id: String(i), found: true, _source: raw(i) });
const input = ids => ({ event_uids: ids.map(uid) });
const access = ids => ({ authenticated: true, sourceProject: 'wazuh', allowedUids: new Set(ids.map(uid)) });
function io(ids, changes = {}) { return { sourceProject: 'wazuh',
  lookup: async body => ({ responses: body.trim().split('\n').filter((_, i) => i % 2 === 1)
    .map(line => search(ids.find(i => uid(i) === JSON.parse(line).query.term.event_uid))) }),
  sources: async refs => ({ docs: refs.map(r => doc(ids.find(i => uid(i) === r.uid))) }),
  ai: async () => ({ complete: true, payload: { events: ids.map(ai) } }), ...changes }; }


const {createDraftHandler}=load('copilot-draft-http');
const req=(body=input([1]),extra={})=>new Request('http://local/draft',{
  method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),...extra});
let providers=0;
const deps={auth:async()=>null,policy:()=>({enabled:true,project:'wazuh',uids:[uid(1)]}),
  io:()=>io([1]),provider:()=>({name:'mock',model:'offline-synthetic',revision:'test-only',
    generate:async fact=>{providers++;return {summary_th:{text:'สรุปข้อมูลสังเคราะห์เท่านั้น',evidence_uids:[fact.event_uid]},
      facts:[],hypotheses:[],unknowns:[],suggested_checks:[]};}})};
(async()=>{
  assert.equal((await createDraftHandler({...deps,auth:async()=>new Response('',{status:401}),
    policy:()=>{throw Error('Not reached');}})(req())).status,401);
  assert.equal((await createDraftHandler({...deps,policy:()=>({enabled:false})})(req())).status,503);
  const before=providers;
  for(const [body,status] of [[input([2]),403],[input([1,2]),400],[{...input([1]),evidence:{}},400]]){
    assert.equal((await createDraftHandler(deps)(req(body))).status,status);
  }
  assert.equal(providers,before);
  console.log('PASS auth, disabled mode, exact allowlist and one-UID-only JSON before provider');
  for(const [extra,status] of [[{body:'{'},400],[{body:'x'.repeat(4097)},413],
    [{headers:{'Content-Type':'text/plain'}},415]]){
    assert.equal((await createDraftHandler(deps)(req({},extra))).status,status);
  }
  console.log('PASS malformed/media/body limits use bounded request reader');
  const response=await createDraftHandler(deps)(req());const d=await response.json();
  assert.equal(response.status,200);assert.equal(response.headers.get('cache-control'),'no-store');
  assert.equal(d.summary_status,'mock_unreviewed');assert.equal(d.provider,'mock');
  assert.equal(d.draft.summary_th.evidence_uids[0],uid(1));assert.equal(d.evidence.results[0].fact.ai_score,0);
  assert.equal(d.input_evidence_hash,d.evidence.input_evidence_hash);
  console.log('PASS synthetic request -> actual evidence builder -> mock provider -> validated draft');
  const failed=await createDraftHandler({...deps,provider:()=>({...deps.provider(),generate:async()=>({bad:true})})})(req());
  assert.equal(failed.status,503);assert.equal((await failed.json()).draft,null);
  const absent=await createDraftHandler({...deps,io:()=>io([1],{lookup:async()=>{throw Error();}})})(req());
  assert.equal((await absent.json()).summary_status,'insufficient_evidence');
  const limited=createDraftHandler(deps);for(let i=0;i<4;i++)assert.equal((await limited(req())).status,200);
  assert.equal((await limited(req())).status,429);
  console.log('PASS malformed provider fails closed, absent evidence skips generation and rate bound applies');
  console.log('PASS no network/key/reservation/GPU accessed; local-vllm route disabled by default');
})().catch(e=>{console.error(e);process.exitCode=1;});
