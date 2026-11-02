const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const ts = require('typescript');
const base = path.resolve(__dirname,'..');
function compile(file, requireFn=require, globals={}) {
  const code=ts.transpileModule(fs.readFileSync(path.join(base,file),'utf8'), {compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText;
  const mod={exports:{}}; vm.runInNewContext(code,{module:mod,exports:mod.exports,require:requireFn,Buffer,URL,AbortSignal,fetch,process:{env:{}},...globals}); return mod.exports;
}
const lib=compile('src/lib/model-lab.ts');
function event(pipeline='dfp', row=1) {
  const v={schema_version:'morpheus-lab-observation-1',observation_id:'',pipeline_id:pipeline,
    model_name:pipeline==='dfp'?'EDRXDR-LAB-DUO-generic_user':'ransomw-model-short-rf',model_version:'1',
    model_sha256:pipeline==='dfp'?'75bd72e5120acdb7fc5888d94be28a3de8bcaddf49a1b74937512de3eda14cec':'9a03cab79a239da935828911bd101a2055337c768737b02b819bc13bed6a627f',
    processing_mode:'dataset_replay',source_type:'model_result_artifact',source_artifact_sha256:'a'.repeat(64),source_record_ref:pipeline==='dfp'?'csv-row:'+row:'json-object:0',adapter_sha256:'b'.repeat(64),observed_at_utc:'2026-11-03T00:00:00+00:00',
    scores:pipeline==='dfp'?{mean_abs_z:0,max_abs_z:12000}:{output_0:0,output_1:1},
    details:pipeline==='dfp'?{execution_backend:'gpu',input_scope:'duo_sample_result'}:{execution_backend:'cpu',input_scope:'nvidia_training_csv_window',class_mapping:'unverified',input_features:297,snapshots:[1,2,3],feature_order_sha256:'ff504a45944322a33a148eb34e5a0e165d14bafca4e06119078f150daf34839b'},production_ready:false,automated_response_allowed:false,quality_metrics_evaluated:false};
  const keys='schema_version pipeline_id model_name model_version model_sha256 source_type source_artifact_sha256 source_record_ref adapter_sha256'.split(' ').sort();
  v.observation_id=crypto.createHash('sha256').update(JSON.stringify(Object.fromEntries(keys.map(k=>[k,v[k]])))).digest('hex');return v;
}
function raw(events){return {timed_out:false,_shards:{failed:0,total:1,successful:1},hits:{total:{value:events.length,relation:'eq'},hits:events.map(e=>({_id:e.observation_id,_index:'edrxdr-ai-lab-v1',_source:e}))}};}
const clone=v=>JSON.parse(JSON.stringify(v));
async function run(){
  for(const e of [event(),event('ransomware')]) assert.equal(lib.validateObservation(e).observation_id,e.observation_id);
  for(const change of [e=>e.raw_event='secret',e=>e.production_ready=true,e=>e.automated_response_allowed=true,e=>e.quality_metrics_evaluated=true,e=>e.observation_id='c'.repeat(64),e=>e.model_version='2',e=>e.scores.mean_abs_z=-1,e=>e.scores.max_abs_z=Infinity,e=>e.observed_at_utc='missing',e=>e.processing_mode='live']) {const e=event();change(e);assert.throws(()=>lib.validateObservation(e));}
  for(const change of [e=>e.details.class_mapping='verified',e=>e.details.snapshots=[1,3,4],e=>e.scores.output_1=.5,e=>e.details.raw_log='x']){const e=event('ransomware');change(e);assert.throws(()=>lib.validateObservation(e));}
  console.log('PASS strict model/schema/identity validation, zero, large z-scores and unmapped outputs');
  const events=Array.from({length:66},(_,i)=>event('dfp',i+1)).concat(event('ransomware'));
  assert.equal(lib.projectLabResult(raw(events),{page:1,pipeline:'all'}).observations.length,50);
  assert.equal(lib.projectLabResult(raw(events),{page:2,pipeline:'all'}).observations.length,17);
  assert.equal(lib.projectLabResult(raw(events),{page:1,pipeline:'ransomware'}).total,1);
  assert.equal(lib.projectLabResult(raw([]),{page:1,pipeline:'all'}).total,0);
  for(const change of [d=>d.timed_out=true,d=>d._shards.failed=1,d=>d._shards.successful=0,d=>d.hits.total.relation='gte',d=>d.hits.total.value=1001,d=>d.hits.hits[0]._index='edrxdr-events-old',d=>d.hits.hits[0]._id='wrong',d=>d.hits.hits[1]=d.hits.hits[0]]){const d=raw(events);change(d);assert.throws(()=>lib.projectLabResult(d,{page:1,pipeline:'all'}));}
  for(const query of ['?page=0','?page=21','?pipeline=live','?url=http://foreign','?page=1&page=2'])assert.throws(()=>lib.parseLabQuery('http://local/'+query));
  console.log('PASS complete bounded batches, pagination/filtering, foreign index, duplicates and partial rejection');
  let calls=0;
  const transport=async(url,opts)=>{calls++;assert.equal(url,'http://127.0.0.1:9200/edrxdr-ai-lab-v1/_search?allow_partial_search_results=false');assert.equal(opts.redirect,'error');assert.equal(opts.cache,'no-store');assert.equal(opts.method,'POST');assert.equal(JSON.parse(opts.body).size,1000);return Response.json(raw([event()]));};
  assert.equal((await lib.readModelLab({page:1,pipeline:'all'},transport)).total,1);assert.equal(calls,1);
  await assert.rejects(()=>lib.readModelLab({page:1,pipeline:'all'},async()=>new Response('x'.repeat(2*1024*1024+1),{headers:{'content-type':'application/json'}})));
  console.log('PASS fixed read-only search endpoint, body limits and no external transport');
  let authorized=false,enabled=false,reads=0,hold;
  const environment={}; const reply=(data,init={})=>({status:init.status||200,data,headers:init.headers});
  const route=compile('src/app/api/nexus/v1/lab/route.ts',id=>id==='next/server'?{NextResponse:{json:reply}}:id==='@/lib/history-auth'?{requireHistoryAuth:async()=>authorized?null:{status:401}}:id==='@/lib/model-lab'?{...lib,readModelLab:async()=>{reads++;if(hold)await hold;return {complete:true};}}:require(id),{process:{env:environment}});
  const req={url:'http://local/api/nexus/v1/lab'};
  assert.equal((await route.GET(req)).status,401);assert.equal(reads,0);
  authorized=true;assert.equal((await route.GET(req)).status,503);assert.equal(reads,0);
  environment.NEXUS_MODEL_LAB_ENABLED='1';assert.equal((await route.GET({url:req.url+'?page=0'})).status,400);assert.equal(reads,0);
  let release;hold=new Promise(r=>release=r);const pending=route.GET(req);await new Promise(r=>setImmediate(r));assert.equal((await route.GET(req)).status,503);release();assert.equal((await pending).status,200);
  assert.equal(reads,1);
  console.log('PASS auth first, disabled by default, invalid query before IO and one in-flight request');
  console.log('MODEL_LAB_OFFLINE_SERVER_PASS; synthetic only; no endpoint, secret, dataset, model or GPU reads');
}
run().catch(e=>{console.error(e);process.exitCode=1});
