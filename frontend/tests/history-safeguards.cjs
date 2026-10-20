const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const compile = file => ts.transpileModule(fs.readFileSync(path.join(__dirname, '../'+file),'utf8'),
  {compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
const uid = n => n.toString(16).padStart(64,'0');
function history(ai) {
  const scope={exports:{},AbortSignal,Map,Set,fetch:()=>{throw Error('Network forbidden');},
    require:name=>{assert.equal(name,'./copilot-ai-reader');return {readCompleteAi:ai};}};
  vm.runInNewContext(compile('src/lib/history-ai.ts'),scope);return scope.exports.enrichHistoryPage;
}
function route({auth=false,body={total:0,events:[]}}={}) {
  let calls=0, enrich=0;
  const scope={exports:{},URL,require:name=>{
    if(name==='next/server')return {NextResponse:{json:(data,options)=>({data,status:options?.status||200,headers:options?.headers})}};
    if(name==='@/lib/history-auth')return {requireHistoryAuth:async()=>auth?{status:401}:null};
    if(name==='@/lib/history-ai')return {enrichHistoryPage:async events=>{enrich++;return {events,ai_lookup_status:'ok'};}};
    if(name==='node:child_process')return {execFile:async(command,args,options)=>{calls++;assert.equal(command,'python3');assert.equal(options.timeout,10000);assert.equal(options.maxBuffer,1024*1024);return {stdout:JSON.stringify(body)};}};
    if(name==='node:util')return {promisify:f=>f};throw Error(name);
  }};
  vm.runInNewContext(compile('src/app/api/nexus/v1/history/route.ts'),scope);
  return {get:scope.exports.GET,calls:()=>calls,enrich:()=>enrich};
}
(async()=>{
  let calls=0;
  const data=await history(async batch=>{calls++;return {complete:true,payload:{events:batch.flatMap(u=>
    u===uid(1)?[{event_uid:u,high_severity_score:0,predicted_label:'low_severity'}]:
    u===uid(2)?[0,1].map(()=>({event_uid:u})):[])}};})([1,2,3].map(n=>({event_uid:uid(n)})));
  assert.deepEqual(Array.from(data.events,e=>e.ai_status),['matched','conflict','not_scored']);assert.equal(data.events[0].ai_score,0);
  assert.equal((await history(async()=>{throw Error('partial');})([{event_uid:uid(1)}])).events[0].ai_status,'unavailable');
  assert.equal((await history(async()=>{throw Error('Must not call');})([{event_uid:'invalid'}])).events[0].ai_status,'unavailable');
  assert.equal((await history(async()=>{throw Error('Must not call');})([])).events.length,0);
  console.log('PASS History zero/not_scored/conflict/unavailable and no invalid-UID IO');
  let active=0,max=0,total=0;
  await history(async batch=>{assert(batch.length<=8);total+=batch.length;active++;max=Math.max(max,active);await Promise.resolve();active--;return {complete:true,payload:{events:[]}};})(Array.from({length:100},(_,n)=>({event_uid:uid(n+1)})));
  assert.equal(total,100);assert(max<=2);
  const failed=await history(async batch=>{if(batch.includes(uid(9)))throw Error('unavailable');return {complete:true,payload:{events:batch.map(event_uid=>({event_uid,high_severity_score:0,predicted_label:'low_severity'}))}};})(Array.from({length:16},(_,n)=>({event_uid:uid(n+1)})));
  assert(failed.events.every(e=>e.ai_status==='unavailable'&&e.ai_score===null));
  console.log('PASS History bounded batches/concurrency and no partial-page matches');
  const denied=route({auth:true});assert.equal((await denied.get(new Request('http://local/api'))).status,401);assert.equal(denied.calls(),0);
  for(const query of ['?page=0','?page=1&page=2','?unknown=x','?hours=1']){
    const r=route();assert.equal((await r.get(new Request('http://local/api'+query))).status,400);assert.equal(r.calls(),0);
  }
  for(const body of [{total:-1,events:[]},{total:1,events:[null]},{total:101,events:Array(101).fill({})}]){
    const r=route({body});assert.equal((await r.get(new Request('http://local/api'))).status,503);assert.equal(r.enrich(),0);
  }
  const ok=route({body:{total:0,events:[],source:'forged',snapshot_only:false}});
  const response=await ok.get(new Request('http://local/api'));assert.equal(response.status,200);assert.equal(response.data.source,'wazuh-history-sqlite');assert.equal(response.data.snapshot_only,true);assert.equal(response.headers['Cache-Control'],'no-store');
  console.log('PASS History route auth first, strict query, invalid payload, fixed metadata and no-store');
})().catch(e=>{console.error(e);process.exitCode=1;});
