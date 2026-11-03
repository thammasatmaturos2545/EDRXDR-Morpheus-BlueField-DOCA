const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'../public/nexus/dfp-diagnostic.js'),'utf8');
const fixture=JSON.parse(fs.readFileSync(path.join(__dirname,'dfp-diagnostic-fixture.json'),'utf8'));
class Element{
  constructor(tag){this.tag=tag;this.children=[];this.style={};this.attrs={};this.disabled=false;this.own='';this.isConnected=true;}
  set textContent(v){this.own=String(v);this.children=[];}get textContent(){return this.own+this.children.map(x=>x.textContent).join('');}
  append(...v){this.children.push(...v);}replaceChildren(...v){this.children=[];this.own='';this.append(...v);}setAttribute(k,v){this.attrs[k]=v;}
}
function payload(){return {...JSON.parse(JSON.stringify(fixture)),artifact_sha256:'c'.repeat(64),read_complete:true,total:12,record_total:845,nominal_interior_windows:10,boundary_windows:2};}
const response=data=>({ok:true,status:200,json:async()=>data}),flush=()=>new Promise(r=>setImmediate(r));
function setup(fetcher){
  const root=new Element('section'),events={};const window={addEventListener:(n,f)=>events[n]=f};
  const location={hash:'#dfpdiagnostic'};const document={getElementById:n=>n==='dfp-diagnostic-root'?root:null,
    createElement:n=>new Element(n),createDocumentFragment:()=>new Element('fragment')};
  vm.runInNewContext(source,{window,document,location,fetch:fetcher,AbortController,setTimeout,clearTimeout});
  return {root,api:window.NexusDfpDiagnostic,events,location};
}
async function main(){
  let calls=0;const good=setup(async(url,opt)=>{calls++;assert.equal(url,'/api/nexus/v1/dfp-diagnostic');assert.equal(opt.method,'GET');assert.equal(opt.credentials,'same-origin');assert.equal(opt.redirect,'error');return response(payload());});
  good.api.mount();await flush();assert.equal(calls,1);assert(good.root.textContent.includes('อ่านผลครบ 12 windows'));
  assert(good.root.textContent.includes('Reconstruction score'));assert(good.root.textContent.includes('Automated response OFF'));
  const all=[];function scan(n){all.push(n);n.children.forEach(scan);}scan(good.root);
  assert(all.some(n=>n.tag==='td'&&n.textContent==='0'));assert(all.some(n=>n.tag==='td'&&n.textContent==='22'));
  assert(!source.includes('innerHTML'));assert(!good.root.textContent.includes('99.9 / 100'));
  console.log('PASS 12-window native table, genuine zero/above-one loss, explicit unknown coverage and no model calls');
  for(const change of [d=>d.processing_mode='live',d=>d.model_sha256='b'.repeat(64),d=>d.source_capture_sha256='a'.repeat(64),
    d=>d.read_complete=false,d=>d.total=11,d=>d.production_ready=true,d=>d.observations.pop(),
    d=>d.observations[0].window_start_utc='<img src=x onerror=alert(1)>',d=>d.observations[0].reconstruction_score=-1,
    d=>d.observations[1]=d.observations[0]]){
    const d=payload();change(d);const x=setup(async()=>response(d));x.api.mount();await flush();assert(!x.root.textContent.includes('Reconstruction score'));
  }
  for(const status of [401,503]){
    const x=setup(async()=>({ok:false,status}));x.api.mount();await flush();assert(!x.root.textContent.includes('Reconstruction score'));
    if(status===401)assert(x.root.textContent.includes('Sign in'));
  }
  console.log('PASS denial/disabled/foreign/partial/malformed data render no score facts or markup');
  let attempt=0;const stale=setup(async()=>++attempt===1?response(payload()):{ok:false,status:503});stale.api.mount();await flush();
  assert(stale.root.textContent.includes('Reconstruction score'));await stale.root.children.find(x=>x.tag==='button').onclick();
  assert(!stale.root.textContent.includes('Reconstruction score'));
  let done;const raced=setup(()=>new Promise(r=>done=r));raced.api.mount();await flush();const first=done;raced.api.mount();await flush();
  done({ok:false,status:503});await flush();first(response(payload()));await flush();assert(!raced.root.textContent.includes('Reconstruction score'));
  const navigating=setup(()=>new Promise(r=>done=r));navigating.api.mount();await flush();navigating.location.hash='#overview';navigating.events.hashchange();done(response(payload()));await flush();assert(!navigating.root.textContent.includes('Reconstruction score'));
  console.log('PASS failed reload clears old facts; remount/navigation ignore late responses');
  const app=fs.readFileSync(path.join(__dirname,'../public/nexus/app.js'),'utf8'),html=fs.readFileSync(path.join(__dirname,'../public/nexus/index.html'),'utf8');
  assert(app.includes("dfpdiagnostic:'DFP Diagnostic'"));assert(app.includes("['dfpdiagnostic','DFP Diagnostic','code']"));assert(app.includes('dfpdiagnostic:dfpDiagnosticPage'));
  assert(html.indexOf('src="./dfp-diagnostic.js"')<html.indexOf('src="./app.js"'));
  const match=app.match(/function setModeInfo\(\)\{([\s\S]*?)\n  \}\n  function nav/);assert(match);
  for(const mode of ['demo','api','import']){
    const nodes=Object.fromEntries(['sidebar-state','sidebar-mode','footer-data'].map(id=>[id,{textContent:'',previousElementSibling:{className:''}}]));
    const state={page:'dfpdiagnostic',mode,data:{meta:{}},connectionError:''},before=JSON.stringify(state);
    vm.runInNewContext('(function(){'+match[1]+'})()',{state,$:id=>nodes[id]});
    assert.equal(nodes['sidebar-mode'].textContent,'DIAG');assert.equal(JSON.stringify(state),before);
  }
  console.log('DFP_DIAGNOSTIC_UI_OFFLINE_PASS; DOM doubles only, real browser pending');
}
main().catch(e=>{console.error(e);process.exitCode=1});
