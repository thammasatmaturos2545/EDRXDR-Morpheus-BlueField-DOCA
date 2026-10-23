const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),ts=require('typescript');
const code=ts.transpileModule(fs.readFileSync(path.join(__dirname,'../src/lib/copilot-provider-config.ts'),'utf8'),{
  compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
function config(change={}){
  let closed=false;
  const bytes=Buffer.from(change.text||JSON.stringify({confirmed:true,purpose:'soc-copilot-inference',
    gpuUuid:'GPU-11111111-1111-1111-1111-111111111111',startsAt:'2026-10-24T00:00:00Z',expiresAt:'2026-10-24T02:00:00Z'}));
  const io={realpath:async p=>change.symlink?'/other':p,open:async()=>({
    stat:async()=>({isFile:()=>true,uid:1001,mode:0o100600,size:bytes.length,...change.stat}),
    read:async(buffer,offset,length,position)=>{const n=bytes.copy(buffer,offset,offset,offset+length);return {bytesRead:n};},
    close:async()=>{closed=true;}})};
  const scope={exports:{},Buffer,TextDecoder,process:{getuid:()=>1001},require:name=>{
    if(name==='node:fs/promises')return io;
    if(name==='node:fs')return {constants:fs.constants};
    if(name==='./copilot-local-provider')return {createLocalProvider:deps=>deps};
    throw Error('Unexpected dependency');
  }};
  vm.runInNewContext(code,scope);
  return {deps:scope.exports.configuredLocalProvider(),closed:()=>closed};
}
(async()=>{
  const good=config();const grant=await good.deps.reservation();assert.equal(grant.confirmed,true);assert(good.closed());
  for(const change of [{symlink:true},{stat:{uid:1002}},{stat:{mode:0o100644}},
    {stat:{size:4097}},{text:'x'.repeat(4097)},{text:'{"confirmed":true,"extra":true}'},{text:'{' }]){
    await assert.rejects(config(change).deps.reservation());
  }
  console.log('PASS fixed private reservation path, owner/mode/symlink/size/schema checks; mocked FS only');
  const key=config({text:'a'.repeat(64)});assert.equal((await key.deps.key()).length,64);assert(key.closed());
  console.log('PASS bounded private key read closes file; no real file/key/reservation or GPU accessed');
})().catch(e=>{console.error(e);process.exitCode=1;});
