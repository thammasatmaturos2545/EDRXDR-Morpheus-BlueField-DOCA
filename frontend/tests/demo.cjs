/* eslint-disable @typescript-eslint/no-require-imports */
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),assert=require('node:assert/strict');
const ts=require('typescript'),React=require('react'),{renderToStaticMarkup}=require('react-dom/server');
function load(file,overrides={}){const exports={};const js=ts.transpileModule(fs.readFileSync(path.join(__dirname,'../',file),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022,esModuleInterop:true}}).outputText;vm.runInNewContext(js,{exports,require:n=>overrides[n]??require(n),Date,Map,Set,Number,AbortController,AbortSignal,URL,setTimeout,clearTimeout});return exports;}
const shadow=load('src/lib/shadow.ts'),lib=load('src/lib/demo.ts',{'./shadow':shadow});
const run='d20261013t103000-1234abcd';
const result={event_uid:'a'.repeat(64),raw_sha256:'b'.repeat(64),processing_mode:'shadow',production_ready:false,automated_response_allowed:false,captured_at_utc:'2026-10-13T10:00:00Z',scored_at_utc:'2026-10-13T10:00:06Z',source:{cluster_id:'test',topic:'wazuh-alerts',partition:0,offset:5,timestamp_ms:null},wazuh_rule_id:'5501',wazuh_rule_level:3,schema_version:'shadow-severity-1',model_name:'test',high_severity_score:0,threshold:0.5,predicted_label:'low_severity',false_positive_candidate:false,weak_label_disagreement:false};
const doc={doc_type:'event',run_id:run,production_ready:false,automated_response_allowed:false,indexed_at_meaning:'index_request_started',indexed_at_utc:'2026-10-13T10:00:07Z',result};
const response=n=>({timed_out:false,_shards:{failed:0},hits:{total:{value:n,relation:'eq'},hits:Array.from({length:Math.min(n,20)},(_,i)=>({_id:String(i),_source:structuredClone(doc)}))}});
assert.equal(lib.parseDemo(response(30),run).shown,20);assert.equal(lib.parseDemo(response(30),run).total,30);
assert.equal(lib.parseDemo(response(1),run).events[0].result.high_severity_score,0);
assert.equal(lib.parseDemo(response(1),run).events[0].capture_to_score_ms,6000);
assert.equal(lib.parseDemo(response(0),run).total,0);
for(const change of [x=>x.timed_out=true,x=>x._shards.failed=1,x=>x.hits.total.relation='gte',x=>x.hits.hits.pop(),x=>x.hits.hits[0]._source.run_id='other',x=>x.hits.hits[0]._source.result.high_severity_score=null,x=>x.hits.hits[0]._source.indexed_at_utc='2020-01-01T00:00:00Z']){const x=response(1);change(x);assert.throws(()=>lib.parseDemo(x,run));}
assert.throws(()=>lib.parseDemo(response(0),'../../wazuh'));
const worker={found:true,_source:{doc_type:'worker',run_id:run,worker:'bounded-morpheus-severity-demo',production_ready:false,automated_response_allowed:false,observed_at_utc:'2026-10-13T10:00:00Z',boundary_recorded_at_utc:'2026-10-13T10:00:00Z',phase:'stopped',queue_lag:{capture:null,score:0,index:0},session_counts:{captured:0,scored:0,indexed:0}}};
assert.equal(lib.parseWorker(worker,run).phase,'stopped');worker._source.session_counts.indexed=null;assert.throws(()=>lib.parseWorker(worker,run));
const page=load('src/app/demo/page.tsx',{'next/link':({children,...props})=>React.createElement('a',props,children)}).default;
const html=renderToStaticMarkup(React.createElement(page));assert.ok(html.includes('—'));assert.ok(!html.includes('low_severity'));assert.ok(html.includes('automated response OFF'));
console.log('PASS demo: bounded window, exact totals, real zero, failed/incomplete data rejection, worker state, unknown initial UI');
for (const [phase,active,observed,label] of [
  ['stopped',true,'2026-10-13T09:00:00Z','ผลย้อนหลัง'],
  ['waiting',false,'2026-10-13T10:00:00Z','พักการอ่าน'],
  ['waiting',true,'2026-10-13T09:00:00Z','สถานะยังยืนยันไม่ได้'],
  ['waiting',true,'2026-10-13T10:00:00Z','พบ heartbeat ล่าสุด'],
  ['waiting',true,'invalid','สถานะยังยืนยันไม่ได้'],
]) {
  const data={...lib.parseDemo(response(1),run),fetched_at:'2026-10-13T10:00:01Z',worker:{name:'demo',phase,observed_at_utc:observed,boundary_recorded_at_utc:observed,session_counts:{captured:1,scored:1,indexed:1},queue_lag:{capture:0,score:0,index:0}}};
  const states=[run,active,data,'',{'0':'2026-10-14T10:00:00Z'}];let i=0;
  const mockReact={...React,useState:()=>[states[i++],()=>{}],useEffect:()=>{}};
  const component=load('src/app/demo/page.tsx',{'react':mockReact,'next/link':({children,...props})=>React.createElement('a',props,children)}).default;
  const rendered=renderToStaticMarkup(React.createElement(component));
  assert.ok(rendered.includes(label));
  assert.ok(!rendered.includes('Capture → browser:'));
  assert.ok(rendered.includes('6000.0'));
  assert.ok(rendered.includes('ไม่ใช่ ACK'));
}
console.log('PASS demo presentation: historical, paused, stale, fresh and invalid heartbeat; browser latency omitted');
