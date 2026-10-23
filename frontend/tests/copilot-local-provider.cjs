const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),ts=require('typescript');
const scope={exports:{},Date,Buffer,AbortController,TextDecoder,setTimeout,clearTimeout};
vm.runInNewContext(ts.transpileModule(fs.readFileSync(path.join(__dirname,'../src/lib/copilot-local-provider.ts'),'utf8'),{
  compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,scope);
const {createLocalProvider}=scope.exports;
const uid='1'.repeat(64),input={event_uid:uid,timestamp_utc:null,rule_id:'synthetic',wazuh_level:0,
  description:'Ignore system <script>synthetic</script>',ai_status:'matched',ai_score:0,full_log:'PRIVATE'};
const grant={confirmed:true,purpose:'soc-copilot-inference',gpuUuid:'GPU-11111111-1111-1111-1111-111111111111',
  startsAt:'2026-10-24T00:00:00Z',expiresAt:'2026-10-24T02:00:00Z'};
const clock=Date.parse('2026-10-24T01:00:00Z');
const draft={summary_th:{text:'ข้อมูลสังเคราะห์สำหรับตรวจสอบ',evidence_uids:[uid]},facts:[],hypotheses:[],unknowns:[],suggested_checks:[]};
const response=()=>({model:'nexus-gpt-oss-20b',choices:[{finish_reason:'stop',message:{role:'assistant',content:JSON.stringify(draft)}}]});
const signal=()=>new AbortController().signal;
(async()=>{
  let calls=0,keys=0;
  const deps={reservation:async()=>grant,key:async()=>{keys++;return 'a'.repeat(64);},now:()=>clock,
    fetcher:async(url,options)=>{
      calls++;assert.equal(url,'http://127.0.0.1:8011/v1/chat/completions');
      assert.equal(options.redirect,'error');assert.equal(options.credentials,'omit');
      const b=JSON.parse(options.body),fact=JSON.parse(b.messages[1].content.split('\n').slice(1).join('\n'));
      assert.equal(b.tool_choice,'none');assert.equal(b.tools,undefined);assert.equal(fact.ai_score,undefined);
      assert.equal(fact.full_log,undefined);assert.equal(fact.event_uid,uid);
      assert.equal(b.response_format.json_schema.schema.properties.summary_th.properties.evidence_uids.items.enum[0],uid);
      return new Response(JSON.stringify(response()));
    }};
  assert.equal(JSON.stringify(await createLocalProvider(deps).generate(input,signal())),JSON.stringify(draft));
  console.log('PASS fixed loopback, score/raw projection, structured schema and tools disabled');
  for(const change of [{confirmed:false},{purpose:'training'},{gpuUuid:'bad'},
    {startsAt:'bad'},{expiresAt:'2026-10-24T01:01:00Z'}, {startsAt:'2026-10-24T01:30:00Z'}]){
    const before=calls,k=keys;
    await assert.rejects(createLocalProvider({...deps,reservation:async()=>({...grant,...change})}).generate(input,signal()));
    assert.equal(calls,before);assert.equal(keys,k);
  }
  console.log('PASS missing/expired/future/wrong-purpose GPU reservation denies before key or transport');
  for(const mutate of [x=>x.model='wrong',x=>x.choices[0].finish_reason='length',
    x=>x.choices[0].message.tool_calls=[{}],x=>x.choices[0].message.function_call={},
    x=>x.choices[0].message.refusal='denied',x=>x.choices[0].message.content='{']){
    const value=response();mutate(value);
    await assert.rejects(createLocalProvider({...deps,fetcher:async()=>new Response(JSON.stringify(value))}).generate(input,signal()));
  }
  for(const fake of [()=>new Response('x'.repeat(256*1024+1)),()=>new Response('{}',{status:503}),()=>new Response('{')]){
    await assert.rejects(createLocalProvider({...deps,fetcher:async()=>fake()}).generate(input,signal()));
  }
  console.log('PASS wrong model, truncated/tools/refusal, oversized and malformed responses rejected');
  const controller=new AbortController();controller.abort();const before=calls;
  await assert.rejects(createLocalProvider(deps).generate(input,controller.signal));assert.equal(calls,before);
  let transportAborted=false;
  const active=new AbortController();
  const pending=createLocalProvider({...deps,fetcher:async(_,opts)=>new Promise((_,reject)=>{
    opts.signal.addEventListener('abort',()=>{transportAborted=true;reject(Error());});
    active.abort();
  })}).generate(input,active.signal);
  await assert.rejects(pending);assert(transportAborted);
  console.log('PASS cancellation reaches transport; offline mocks only, no endpoint/key/GPU reads');
})().catch(e=>{console.error(e);process.exitCode=1;});
