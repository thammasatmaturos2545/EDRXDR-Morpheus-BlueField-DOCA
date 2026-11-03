const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto'),ts=require('typescript');
const base=path.resolve(__dirname,'..'),fixture=JSON.parse(fs.readFileSync(path.join(__dirname,'dfp-diagnostic-fixture.json'),'utf8'));
function compile(file,requireFn=require,globals={}){
  const code=ts.transpileModule(fs.readFileSync(path.join(base,file),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText;
  const mod={exports:{}};vm.runInNewContext(code,{module:mod,exports:mod.exports,require:requireFn,Buffer,URL,process:{env:{},getuid:()=>1001},...globals});return mod.exports;
}
const lib=compile('src/lib/dfp-diagnostic.ts');const clone=x=>JSON.parse(JSON.stringify(x));
async function main(){
  let out=lib.validateDfpBundle(clone(fixture));assert.equal(out.total,12);assert.equal(out.record_total,845);assert.equal(out.observations[0].reconstruction_score,0);assert(out.observations[11].reconstruction_score>1);
  for(const change of [x=>x.processing_mode='live',x=>x.source_capture_sha256='a'.repeat(64),x=>x.model_sha256='b'.repeat(64),
    x=>x.quality_metrics_evaluated=true,x=>x.threshold_selected=true,x=>x.production_ready=true,x=>x.event_uid='fake',
    x=>x.observations.pop(),x=>x.observations[1]=x.observations[0],x=>x.observations[0].reconstruction_score=NaN,
    x=>x.observations[0].reconstruction_score=-1,x=>x.observations[0].window_complete=true,x=>x.observations[0].full_log='private',
    x=>x.observations[0].window_start_utc='2030-02-30T00:00:00+00:00',x=>x.observations[0].record_count=0]){
    const bad=clone(fixture);change(bad);assert.throws(()=>lib.validateDfpBundle(bad));
  }
  console.log('PASS exact frozen scope, Python/JS observation identities, zero/above-one scores and no raw/event/severity fields');
  const raw=Buffer.from(JSON.stringify(fixture)),hash=crypto.createHash('sha256').update(raw).digest('hex');
  let opens=0,closes=0,mode=0o100600,uid=1001,nlink=1,changed=false,oversize=false;
  const reader=compile('src/lib/dfp-diagnostic.ts',id=>id==='node:fs'?{constants:{...fs.constants,O_NOFOLLOW:0x20000}}:id==='node:fs/promises'?{open:async(file,flags)=>{
    opens++;assert.equal(file,lib.DFP_BUNDLE_PATH);assert(flags&0x20000);let stats=0;
    return {stat:async()=>({isFile:()=>true,nlink,size:oversize?lib.MAX_DFP_BYTES+1:raw.length,mode,uid,ino:stats++&&changed?2:1,dev:1,mtimeMs:1}),
      read:async(buffer)=>{raw.copy(buffer);return{bytesRead:raw.length};},close:async()=>{closes++;}};
  }}:require(id));
  assert.equal((await reader.readDfpDiagnostic(hash)).total,12);assert.equal(opens,1);assert.equal(closes,1);
  await assert.rejects(()=>reader.readDfpDiagnostic('invalid'));assert.equal(opens,1);
  await assert.rejects(()=>reader.readDfpDiagnostic('0'.repeat(64)));
  mode=0o100644;await assert.rejects(()=>reader.readDfpDiagnostic(hash));mode=0o100600;
  uid=0;await assert.rejects(()=>reader.readDfpDiagnostic(hash));uid=1001;
  nlink=2;await assert.rejects(()=>reader.readDfpDiagnostic(hash));nlink=1;
  changed=true;await assert.rejects(()=>reader.readDfpDiagnostic(hash));changed=false;
  oversize=true;await assert.rejects(()=>reader.readDfpDiagnostic(hash));assert.equal(opens,closes);
  console.log('PASS fixed bounded private-file reader, no-follow/hash/owner/mode/link/change guards and closed handles');
  let authorized=false,reads=0,hold;const env={};const response=(data,init={})=>({status:init.status||200,data});
  const route=compile('src/app/api/nexus/v1/dfp-diagnostic/route.ts',id=>id==='next/server'?{NextResponse:{json:response}}:
    id==='@/lib/history-auth'?{requireHistoryAuth:async()=>authorized?null:{status:401}}:
    id==='@/lib/dfp-diagnostic'?{readDfpDiagnostic:async()=>{reads++;if(hold)await hold;return out;}}:require(id),{process:{env}});
  const request={url:'http://local/api/nexus/v1/dfp-diagnostic'};
  assert.equal((await route.GET(request)).status,401);assert.equal(reads,0);authorized=true;
  assert.equal((await route.GET(request)).status,503);env.NEXUS_DFP_DIAGNOSTIC_ENABLED='1';
  assert.equal((await route.GET(request)).status,503);env.NEXUS_DFP_DIAGNOSTIC_SHA256=hash;
  assert.equal((await route.GET({url:request.url+'?path=/private'})).status,400);assert.equal(reads,0);
  let release;hold=new Promise(r=>release=r);const pending=route.GET(request);await new Promise(r=>setImmediate(r));
  assert.equal((await route.GET(request)).status,503);release();assert.equal((await pending).status,200);assert.equal(reads,1);
  console.log('PASS auth first, disabled/unpinned before IO, no browser paths/queries and one in-flight read');
  console.log('DFP_DIAGNOSTIC_SERVER_OFFLINE_PASS; mocks only, no private files/auth keys/network/models/GPU');
}
main().catch(e=>{console.error(e);process.exitCode=1});
