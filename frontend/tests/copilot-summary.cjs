const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const ts = require('typescript');
const modules = new Map();
function load(name) {
  if (modules.has(name)) return modules.get(name);
  const scope = { exports: {}, Buffer, Date, Set, Map, AbortController, setTimeout, clearTimeout,
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

const summary = load('copilot-summary');
const draft = id => ({ summary_th: { text: 'หลักฐานระบุเหตุการณ์ แต่ยังยืนยันการโจมตีไม่ได้', evidence_uids: [id] },
  facts: [], hypotheses: [], unknowns: [], suggested_checks: [] });
const provider = fn => ({ name:'mock', model:'synthetic-summary-v2', revision:'offline-only', generate:fn });
(async()=>{
  let calls=0;
  const mock=provider(async (fact,signal)=>{
    calls++;assert.equal(fact.ai_score,undefined);assert.equal(fact.ai_label,undefined);
    assert.equal(fact.full_log,undefined);assert.equal(signal.aborted,false);
    assert(Object.isFrozen(fact));return draft(fact.event_uid);
  });
  const a=await summary.generateCopilotDraft(input([1]),access([1]),io([1]),mock);
  assert.equal(a.summary_status,'mock_unreviewed');assert.equal(a.evidence.results[0].fact.ai_score,0);
  assert.equal(a.input_evidence_hash,a.evidence.input_evidence_hash);
  assert.equal(a.automated_response_allowed,false);assert.equal(a.production_ready,false);
  assert.equal(a.human_review_required,true);
  const b=await summary.generateCopilotDraft(input([1]),access([1]),io([1]),mock);
  assert.equal(b.input_evidence_hash,a.input_evidence_hash);assert.equal(calls,2);
  console.log('PASS fresh canonical evidence each call, stable hash, score sidecar and explicit mock status');
  const before=calls;
  for(const bad of [{...access([1]),authenticated:false},access([2])]){
    await assert.rejects(summary.generateCopilotDraft(input([1]),bad,io([1]),mock));
  }
  await assert.rejects(summary.generateCopilotDraft({...input([1]),evidence:{}},access([1]),io([1]),mock));
  const absent=await summary.generateCopilotDraft(input([1]),access([1]),io([1],{lookup:async()=>{throw Error();}}),mock);
  assert.equal(absent.summary_status,'insufficient_evidence');assert.equal(absent.draft,null);assert.equal(calls,before);
  console.log('PASS unauthorized, browser evidence and insufficient source never invoke provider');
  for(const mutate of [x=>x.ai_score=1,x=>x.summary_th.evidence_uids=[uid(2)],
    x=>x.summary_th.text='<script>bad</script>',x=>x.summary_th.text='คะแนน AI คือ 99',
    x=>x.summary_th.text='100%',x=>x.facts='bad',x=>x.summary_th.text='English only']){
    const bad=draft(uid(1));mutate(bad);
    const out=await summary.generateCopilotDraft(input([1]),access([1]),io([1]),provider(async()=>bad));
    assert.equal(out.summary_status,'unavailable');assert.equal(out.draft,null);
  }
  console.log('PASS malformed schema, foreign citations, markup and generated scores fail closed');
  let aborted=false;
  const stalled=provider((_,signal)=>new Promise(()=>signal.addEventListener('abort',()=>{aborted=true;})));
  const timed=await summary.generateCopilotDraft(input([1]),access([1]),io([1]),stalled,10);
  assert.equal(timed.summary_status,'unavailable');assert.equal(timed.draft,null);assert(aborted);
  const failed=await summary.generateCopilotDraft(input([1]),access([1]),io([1]),provider(async()=>{throw Error('private error');}));
  assert.equal(failed.summary_status,'unavailable');assert.equal(failed.draft,null);
  console.log('PASS timeout abort and provider failure expose no partial or previous draft');
  for(const changes of [{ai:async()=>({complete:true,payload:{events:[]}})},
    {ai:async()=>({complete:false,payload:{}})},
    {ai:async()=>({complete:true,payload:{events:[ai(1),ai(1)]}})}]){
    const out=await summary.generateCopilotDraft(input([1]),access([1]),io([1],changes),mock);
    assert(['not_scored','unavailable','conflict'].includes(out.evidence.results[0].fact.ai_status));
    assert.equal(out.evidence.results[0].fact.ai_score,null);
  }
  console.log('PASS AI statuses preserved; synthetic offline only, no transport/LLM/GPU');
})().catch(error=>{console.error(error);process.exitCode=1;});
