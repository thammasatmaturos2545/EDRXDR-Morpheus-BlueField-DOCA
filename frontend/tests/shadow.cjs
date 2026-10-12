/* eslint-disable @typescript-eslint/no-require-imports */
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const ts = require('typescript');
function load(name, overrides = {}, globals = {}) {
  const exports = {};
  const file = path.join(__dirname, '..', name);
  const js = ts.transpileModule(fs.readFileSync(file, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true, target: ts.ScriptTarget.ES2022 } }).outputText;
  vm.runInNewContext(js, { exports, require: n => overrides[n] ?? require(n), Map, Set, Date, URL, AbortSignal, console, ...globals });
  return exports;
}
const lib = load('src/lib/shadow.ts');
const base = { event_uid:'a'.repeat(64), raw_sha256:'b'.repeat(64), processing_mode:'shadow', production_ready:false, automated_response_allowed:false, captured_at_utc:'2026-10-10T19:09:00Z', scored_at_utc:'2026-10-10T19:18:00Z', source:{cluster_id:'test',topic:'wazuh-alerts',partition:0,offset:15573,timestamp_ms:100}, wazuh_rule_id:'5501',wazuh_rule_level:3 };
const severity = {...base,schema_version:'shadow-severity-1',model_name:'test-model',high_severity_score:0.8,threshold:0.5,predicted_label:'high_severity',false_positive_candidate:true,weak_label_disagreement:true};
const behavioral = {...base,schema_version:'shadow-behavioral-1',model_version:'test-model',ae_scored:false,ae_ratio:null,semantic_novelty:false,analysis_state:'limited_history',routing_status:'limited_history'};
const response = rows => ({timed_out:false,_shards:{failed:0},hits:{total:{value:rows.length,relation:'eq'},hits:rows.map(d=>({_source:d}))}});
const docs = (rows,kind) => lib.documents(response(rows),kind);
let count=0;
function test(name, fn) { fn(); count++; console.log('PASS',name); }
test('same occurrence joins and not-scored remains uncovered',()=>{const x=lib.joinShadow(docs([severity],'severity'),docs([behavioral],'behavioral')); assert.equal(x.counts.matched,1);assert.equal(x.counts.ae_scored,0);assert.equal(x.counts.candidates,1);});
test('same UID different offset must not join',()=>assert.equal(lib.joinShadow(docs([severity],'severity'),docs([{...behavioral,source:{...base.source,offset:15574}}],'behavioral')).counts.unmatched,2));
test('hash conflict is visible, never counted matched',()=>assert.equal(lib.joinShadow(docs([severity],'severity'),docs([{...behavioral,raw_sha256:'c'.repeat(64)}],'behavioral')).counts.conflicts,1));
test('rule metadata conflict is visible',()=>assert.equal(lib.joinShadow(docs([severity],'severity'),docs([{...behavioral,wazuh_rule_id:'other'}],'behavioral')).counts.conflicts,1));
test('duplicate occurrences rejected',()=>assert.throws(()=>docs([severity,severity],'severity')));
test('unbounded/incomplete search rejected',()=>{const r=response([severity]);r.hits.total.value=501;assert.throws(()=>lib.documents(r,'severity'));});
test('partial shard failure rejected',()=>{const r=response([severity]);r._shards.failed=1;assert.throws(()=>lib.documents(r,'severity'));});
test('wrong mode and enabled response rejected',()=>{for(const patch of [{processing_mode:'replay'},{automated_response_allowed:true}])assert.throws(()=>docs([{...severity,...patch}],'severity'));});
test('bad score and false claim rejected',()=>{for(const patch of [{high_severity_score:NaN},{false_positive_candidate:false}])assert.throws(()=>docs([{...severity,...patch}],'severity'));});
test('raw fields removed including nested source',()=>{const d=[...docs([{...severity,raw_json:'PRIVATE',source:{...base.source,raw_log:'PRIVATE'}}],'severity').values()][0];assert.equal(JSON.stringify(d).includes('PRIVATE'),false);});
test('empty indices are valid empty data',()=>assert.equal(lib.joinShadow(docs([],'severity'),docs([],'behavioral')).events.length,0));
test('unknown Wazuh level stays unknown and never becomes a candidate',()=>{const d={...severity,wazuh_rule_id:2901,wazuh_rule_level:null,false_positive_candidate:null,weak_label_disagreement:null};const x=lib.joinShadow(docs([d],'severity'),docs([],'behavioral'));assert.equal(x.counts.candidates,0);assert.equal(x.events[0].severity.wazuh_rule_level,null);});
test('contradictory AE coverage and routing states rejected',()=>{for(const patch of [{analysis_state:'baseline_consistent'},{ae_scored:true,ae_ratio:0.2},{analysis_state:'unreviewed'},{routing_status:'unreviewed'},{routing_status:'local_model'},{analysis_state:'novel_cohort'}])assert.throws(()=>docs([{...behavioral,...patch}],'behavioral'));});
test('actual scored and zero-ratio states accepted without fabricating coverage',()=>{const d={...behavioral,ae_scored:true,ae_ratio:0,analysis_state:'baseline_consistent',routing_status:'local_model'};assert.equal(lib.joinShadow(docs([],'severity'),docs([d],'behavioral')).counts.ae_scored,1);});
test('nested model metadata rejected and opposite-kind fields removed',()=>{assert.throws(()=>docs([{...severity,model_name:{raw_log:'PRIVATE'}}],'severity'));const d=[...docs([{...severity,model_version:{raw_log:'PRIVATE'},analysis_state:{raw_log:'PRIVATE'}}],'severity').values()][0];assert.equal(JSON.stringify(d).includes('PRIVATE'),false);});
test('timeout, lower-bound count, and invalid safety flags fail closed',()=>{for(const change of [r=>r.timed_out=true,r=>r.hits.total.relation='gte',r=>r._shards.failed=1]){const r=response([severity]);change(r);assert.throws(()=>lib.documents(r,'severity'));}assert.throws(()=>docs([{...severity,production_ready:true}],'severity'));});
test('UI preserves not-scored and displays both sides of a conflict',()=>{
  const React=require('react');const {renderToStaticMarkup}=require('react-dom/server');
  const Link=function TestLink({children,...props}) { return React.createElement('a',props,children); };
  const result={fetched_at:'2026-10-11T12:00:00Z',...lib.joinShadow(docs([severity],'severity'),docs([{...behavioral,wazuh_rule_id:'19008'}],'behavioral'))};
  const states=[result,'',false,0,'all'];let next=0;
  const Page=load('src/app/shadow/page.tsx',{'next/link':Link,'./bluefield-shadow':{__esModule:true,default:function TestBluefieldShadow(){return null;}},react:{...React,useState:()=>[states[next++],()=>{}],useEffect:()=>{}}}).default;
  const html=renderToStaticMarkup(React.createElement(Page));
  assert.ok(html.includes('ไม่มีคะแนน AE'));assert.ok(html.includes('ข้อมูลคู่ขัดแย้ง'));assert.ok(html.includes('19008'));assert.ok(!html.includes('AE ratio:'));
});
async function routes() {
  const env={};let called=0;
  const route=load('src/app/api/shadow/events/route.ts',{'@/lib/shadow':lib,'next/server':{NextResponse:{json:(body,init)=>({body,...init})}}},{process:{env},fetch:async(url,options)=>{called++;assert.equal(options.method,'POST');assert.equal(options.redirect,'error');return {ok:true,json:async()=>response(url.includes('severity')?[severity]:[behavioral])};}});
  assert.equal((await route.GET()).status,503);assert.equal(called,0);count++;
  env.SHADOW_OPENSEARCH_URL='http://127.0.0.1:19200';
  const result=await route.GET();assert.equal(result.body.counts.matched,1);assert.equal(called,2);count++;
  env.SHADOW_OPENSEARCH_URL='http://user:secret@localhost:9200';assert.equal((await route.GET()).status,502);assert.equal(called,2);count++;
  console.log(`PASS: ${count} shadow checks (synthetic fixtures; no VM integration claim)`);
}
routes().catch(e=>{console.error(e);process.exitCode=1;});
