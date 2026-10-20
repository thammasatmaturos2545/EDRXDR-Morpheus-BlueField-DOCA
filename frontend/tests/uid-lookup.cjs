/* eslint-disable @typescript-eslint/no-require-imports */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const ts = require('typescript');
const cache = new Map();
function load(name) {
  if (cache.has(name)) return cache.get(name);
  const code = fs.readFileSync(path.join(__dirname, '../src/lib', name + '.ts'), 'utf8');
  const scope = { exports: {}, Buffer, Date, Set, Map, console,
    require: n => n.startsWith('@/lib/') ? load(n.slice(6)) : n.startsWith('./') ? load(n.slice(2)) : require(n) };
  vm.runInNewContext(ts.transpileModule(code, {compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText, scope);
  cache.set(name,scope.exports);return scope.exports;
}
const u = load('uid-lookup'), n = load('nexus-soc');
const clone = x => JSON.parse(JSON.stringify(x));
const raw = i => ({manager:{name:'test'},agent:{id:'004',name:'WIN'},id:String(i),
  timestamp:'2026-10-14T00:00:00Z',rule:{id:'5501',level:0,description:'test'},full_log:'PRIVATE'});
const uid = i => u.canonicalWazuhUid(raw(i));
const ref = i => ({uid:uid(i),index:'wazuh-alerts-4.x-2026.10.14',id:String(i)});
const ai = i => ({schema_version:'live-severity-1',source_type:'wazuh',processing_mode:'live',
  analysis_engine:'nvidia-morpheus-context-severity-v1',model_name:'wazuh-severity-context-v2-balanced-20261008T190719Z-1398863',
  event_uid:uid(i),production_ready:false,automated_response_allowed:false,threshold:.5,
  high_severity_score:0,predicted_label:'low_severity',source_topic:'wazuh-alerts',source_partition:0,source_offset:i,
  input_topic:'morpheus-input',input_partition:0,input_offset:i,scored_at_utc:'2026-10-14T00:01:00Z',wazuh_rule_id:'5501',wazuh_rule_level:0});
function hit(r) {
  const key=[r.index,r.id].map(s=>`${Buffer.byteLength(s)}:${s}`).join('|');
  return {_index:u.LOOKUP_INDEX,_id:crypto.createHash('sha256').update(key).digest('hex'),_source:{
    schema_version:u.LOOKUP_INDEX,event_uid:r.uid,source_index:r.index,source_document_id:r.id,production_ready:false,automated_response_allowed:false}};
}
const search = (hits,total=hits.length) => ({timed_out:false,_shards:{total:1,successful:1,failed:0},hits:{total:{value:total,relation:'eq'},hits}});
const doc = i => ({_index:ref(i).index,_id:ref(i).id,found:true,_source:raw(i)});
function route(io, wazuh, aiPayload) {
  const code=fs.readFileSync(path.join(__dirname,'../src/app/api/nexus/v1/snapshot/route.ts'),'utf8');
  const scope={exports:{},URL,AbortSignal,Date,fetch:async url=>({ok:true,json:async()=>url.endsWith('/api/events')?aiPayload:wazuh}),
    require:name=>({'next/server':{NextResponse:{json:(data,opts)=>({data,status:opts?.status??200})}},
      '@/lib/nexus-soc':n,'@/lib/uid-lookup':u,'@/lib/uid-lookup-server':{searchUidLookup:io.search,readUidSources:io.sources}})[name]};
  vm.runInNewContext(ts.transpileModule(code,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,scope);
  return scope.exports.GET({url:'http://127.0.0.1:3001/api/nexus/v1/snapshot'});
}
let tests=0;
async function test(name,fn) {await fn();tests++;console.log('PASS '+name);}
async function main() {
  await test('canonical identity safe integers and UTF-8',()=>{
    assert.equal(u.canonicalWazuhUid(raw(1)),uid(1));
    assert.equal(u.canonicalWazuhUid({...raw(1),id:1}),uid(1));
    for(const id of [1.2,Number.MAX_SAFE_INTEGER+1,true,null])assert.equal(u.canonicalWazuhUid({...raw(1),id}),null);
    assert.equal(u.canonicalWazuhUid({...raw(1),id:'\ud800'}),null);
    const x=raw(1);x.manager.name='ไทย';
    const c='wazuh-v1|9:ไทย|3:004|1:1';assert.equal(u.canonicalWazuhUid(x),crypto.createHash('sha256').update(c).digest('hex'));
  });
  await test('query exact keyword only and bounded',()=>{
    const q=u.lookupQuery([uid(1)]).trim().split('\n').map(JSON.parse);
    assert.deepEqual(clone(q[1].query),{term:{event_uid:uid(1)}});assert.equal(q[1].size,2);
    assert.throws(()=>u.lookupQuery([uid(1),uid(1)]));assert.throws(()=>u.lookupQuery(['bad']));
    assert.throws(()=>u.lookupQuery(Array(101).fill(uid(1))));
  });
  await test('not_found is not unavailable',()=>assert.equal(u.parseLookup([uid(1)],{responses:[search([])]})[0].status,'not_found'));
  await test('duplicate references conflict even when same UID',()=>{
    const r={...ref(1),id:'different'};assert.equal(u.parseLookup([uid(1)],{responses:[search([hit(ref(1)),hit(r)],3)]})[0].status,'conflict');
  });
  await test('partial shards timeout lower bound and missing index fail closed',()=>{
    for(const change of [r=>r._shards.failed=1,r=>r.timed_out=true,r=>r.hits.total.relation='gte',r=>r.error={type:'index_not_found_exception'}]) {
      const r=search([hit(ref(1))]);change(r);assert.equal(u.parseLookup([uid(1)],{responses:[r]})[0].status,'unavailable');
    }
  });
  await test('hash safety flags and wrong returned UID rejected',()=>{
    for(const change of [h=>h._id='f'.repeat(64),h=>h._source.production_ready=true,h=>h._source.event_uid=uid(2),h=>h._source.raw_event='PRIVATE']) {
      const h=hit(ref(1));change(h);assert.equal(u.parseLookup([uid(1)],{responses:[search([h])]})[0].status,'unavailable');
    }
  });
  await test('truncated and extra msearch responses rejected',()=>{
    assert.throws(()=>u.parseLookup([uid(1)],{responses:[]}));
    assert.equal(u.parseLookup([uid(1)],{responses:[search([],1)]})[0].status,'unavailable');
  });
  await test('source missing retention stays unavailable',()=>{
    assert.equal(u.parseSources([ref(1)],{docs:[{...doc(1),found:false}]},[ai(1)])[0].status,'source_unavailable');
  });
  await test('source identity recalculated not trusted from lookup',()=>{
    const d=doc(1);d._source.id='2';assert.equal(u.parseSources([ref(1)],{docs:[d]},[ai(1)])[0].status,'conflict');
  });
  await test('source index and ID must match exact request',()=>{
    const d=doc(1);d._index=ref(2).index+'x';assert.equal(u.parseSources([ref(1)],{docs:[d]},[ai(1)])[0].status,'source_unavailable');
  });
  await test('Wazuh rule mismatch conflicts instead of displaying AI score',()=>{
    const d=doc(1);d._source.rule.level=3;assert.equal(u.parseSources([ref(1)],{docs:[d]},[ai(1)])[0].status,'conflict');
  });
  await test('private raw fields excluded and real zero remains zero',()=>{
    const r=u.parseSources([ref(1)],{docs:[doc(1)]},[ai(1)])[0];assert.equal(r.alert.rule_level,0);
    assert.equal(JSON.stringify(r).includes('PRIVATE'),false);
  });
  await test('eight historical synthetic fixtures reach actual snapshot builder',async()=>{
    const ids=Array.from({length:8},(_,i)=>i+1);let calls=0;
    const result=await u.augmentWithUidLookup({alerts:[]},{events:ids.map(ai)}, {
      search:async()=>({responses:ids.map(i=>search([hit(ref(i))]))}),
      sources:async refs=>{calls++;assert.equal(refs.length,8);return {docs:ids.map(doc)};}});
    const s=n.buildNexusSnapshot(result.wazuh,{events:ids.map(ai)},{lookupStatuses:result.statuses});
    assert.equal(calls,1);assert.equal(s.alerts.length,8);
    for(const a of s.alerts){assert.equal(a.evidence.ai_status,'matched');assert.equal(a.evidence.ai_score,0);assert.equal(a.evidence.ai_match_method,'event_uid');}
    assert.equal(JSON.stringify(s).includes('PRIVATE'),false);
  });
  await test('new source absent in frozen lookup does not fall back to recent window',async()=>{
    const r=await u.augmentWithUidLookup({alerts:[{event_uid:uid(1)}]},{events:[ai(1)]}, {
      search:async()=>({responses:[search([])]}),sources:async()=>{throw Error('must not fetch');}});
    const s=n.buildNexusSnapshot(r.wazuh,{events:[ai(1)]},{lookupStatuses:r.statuses});
    assert.equal(s.alerts[0].evidence.ai_status,'not_found');assert.equal(s.alerts[0].evidence.ai_score,null);
  });
  await test('lookup outage clears matched score on subsequent request',async()=>{
    const r=await u.augmentWithUidLookup({alerts:[{event_uid:uid(1)}]},{events:[ai(1)]}, {
      search:async()=>{throw Error('offline');},sources:async()=>({docs:[doc(1)]})});
    const s=n.buildNexusSnapshot(r.wazuh,{events:[ai(1)]},{lookupStatuses:r.statuses});
    assert.equal(s.alerts[0].evidence.ai_status,'unavailable');assert.equal(s.alerts[0].evidence.ai_score,null);
  });
  await test('source outage creates no fabricated historical Wazuh row',async()=>{
    const r=await u.augmentWithUidLookup({alerts:[]},{events:[ai(1)]}, {
      search:async()=>({responses:[search([hit(ref(1))])]}),sources:async()=>{throw Error('offline');}});
    assert.equal(r.wazuh.alerts.length,0);assert.equal(r.evidence[0].status,'source_unavailable');
  });
  await test('duplicate AI or current Wazuh UID becomes conflict',async()=>{
    for(const [alerts,events] of [[[],[ai(1),ai(1)]],[[{event_uid:uid(1)},{event_uid:uid(1)}],[ai(1)]]]) {
      const r=await u.augmentWithUidLookup({alerts},{events},{search:async()=>({responses:[search([hit(ref(1))])]}),sources:async()=>({docs:[doc(1)]})});
      assert.equal(r.statuses[uid(1)],'conflict');
    }
  });
  await test('no AI means no lookup or source requests',async()=>{
    const fail=async()=>{throw Error('must not request');};
    const r=await u.augmentWithUidLookup({alerts:[]},{events:[]},{search:fail,sources:fail});assert.equal(r.evidence.length,0);
  });
  await test('missing historical timestamp is not replaced with fetch time',()=>{
    const s=n.buildNexusSnapshot({alerts:[{event_uid:uid(1),timestamp:null}]},{events:[ai(1)]},{lookupStatuses:{[uid(1)]:'matched'}});
    assert.equal(s.alerts[0].created_at,null);assert.equal(s.alerts[0].last_seen,null);
  });
  await test('actual route augments historical alert and exposes metadata',async()=>{
    const r=await route({search:async()=>({responses:[search([hit(ref(1))])]}),sources:async()=>({docs:[doc(1)]})},{alerts:[]},{events:[ai(1)]});
    assert.equal(r.status,200);assert.equal(r.data.meta.uid_lookup.matched,1);assert.equal(r.data.alerts[0].evidence.ai_match_method,'event_uid');
    assert.equal(r.data.meta.production_ready,false);assert.equal(r.data.meta.automated_response_allowed,false);
  });
  await test('actual route preserves unavailable rather than stale match',async()=>{
    const r=await route({search:async()=>{throw Error('unavailable');},sources:async()=>({docs:[]})},{alerts:[{event_uid:uid(1)}]},{events:[ai(1)]});
    assert.equal(r.status,200);assert.equal(r.data.meta.uid_lookup.matched,0);assert.equal(r.data.alerts[0].evidence.ai_status,'unavailable');
    assert.equal(r.data.alerts[0].evidence.ai_score,null);
  });
  console.log(`PASS ${tests} UID Lookup groups; synthetic fixtures, not VM eight-event verification`);
}
main().catch(e=>{console.error(e);process.exitCode=1;});
