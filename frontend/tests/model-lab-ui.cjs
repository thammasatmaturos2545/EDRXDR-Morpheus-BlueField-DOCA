const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'../public/nexus/model-lab.js'),'utf8');
class Element {
  constructor(tag){this.tag=tag;this.children=[];this.style={};this.attrs={};this.disabled=false;this.value='';this.own='';this.isConnected=true;}
  set textContent(v){this.own=String(v);this.children=[];} get textContent(){return this.own+this.children.map(c=>c.textContent).join('');}
  append(...values){for(const v of values){this.children.push(v);if(this.tag==='select'&&!this.value)this.value=v.value;}}
  replaceChildren(...v){this.children=[];this.own='';this.append(...v);} setAttribute(k,v){this.attrs[k]=v;}
}
const uid='a'.repeat(64);
function payload(pipeline='dfp') {return {source:'edrxdr-ai-lab-v1',schema_version:'morpheus-lab-observation-1',processing_mode:'dataset_replay',complete:true,production_ready:false,automated_response_allowed:false,quality_metrics_evaluated:false,page:1,page_size:50,pipeline:'all',total:1,observations:[{observation_id:uid,pipeline_id:pipeline,processing_mode:'dataset_replay',production_ready:false,automated_response_allowed:false,quality_metrics_evaluated:false,model_name:'<img src=x onerror=alert(1)>',model_version:'1',observed_at_utc:'2026-11-03T00:00:00Z',scores:pipeline==='dfp'?{mean_abs_z:0,max_abs_z:12300}:{output_0:0,output_1:1},details:pipeline==='dfp'?{execution_backend:'gpu'}:{execution_backend:'cpu',class_mapping:'unverified'}}]};}
function setup(fetcher){const root=new Element('section'),window={addEventListener(){}};const document={getElementById:id=>id==='model-lab-root'?root:null,createElement:t=>new Element(t),createDocumentFragment:()=>new Element('fragment')};vm.runInNewContext(source,{window,document,location:{hash:'#modellab'},fetch:fetcher,URLSearchParams,AbortController,setTimeout,clearTimeout});return {root,api:window.NexusModelLab};}
const flush=()=>new Promise(r=>setImmediate(r));
const response=data=>({ok:true,status:200,json:async()=>data});
async function main(){
  for(const pipeline of ['dfp','ransomware']){let calls=0;const x=setup(async(url,options)=>{calls++;assert(url.startsWith('/api/nexus/v1/lab?'));assert.equal(options.credentials,'same-origin');assert.equal(options.redirect,'error');return response(payload(pipeline));});x.api.mount();await flush();assert.equal(calls,1);assert(x.root.textContent.includes(pipeline==='dfp'?'mean_abs_z: 0':'output_0: 0'));assert(x.root.textContent.includes('<img src=x onerror=alert(1)>'));assert(x.root.textContent.includes('Automated response OFF'));assert(!x.root.textContent.includes('99.9 / 100'));}
  console.log('PASS literal safe text, zero, unscaled DFP z-scores and unmapped CPU outputs');
  for(const mode of ['denied','disabled','partial','wrong-index','bad-score','raw-mode']){const d=payload();if(mode==='partial')d.complete=false;if(mode==='wrong-index')d.source='edrxdr-events-live';if(mode==='bad-score')d.observations[0].scores.mean_abs_z=-1;if(mode==='raw-mode')d.observations[0].processing_mode='live';const x=setup(async()=>mode==='denied'?{status:401,ok:false}:mode==='disabled'?{status:503,ok:false}:response(d));x.api.mount();await flush();assert(!x.root.textContent.includes('Observation ID:'));if(mode==='denied')assert(x.root.textContent.includes('Sign in'));}
  console.log('PASS auth denial, disabled, partial/foreign and invalid results display no facts');
  let done;const raced=setup(()=>new Promise(r=>done=r));raced.api.mount();await flush();const old=done;raced.api.mount();await flush();done(response({...payload(),total:0,observations:[]}));await flush();old(response(payload()));await flush();assert(!raced.root.textContent.includes('Observation ID:'));assert(raced.root.textContent.includes('0 observations'));
  let attempt=0;const stale=setup(async()=>++attempt===1?response(payload()):{status:503,ok:false});stale.api.mount();await flush();assert(stale.root.textContent.includes('Observation ID:'));await stale.root.children.find(c=>c.tag==='button'&&c.textContent==='Reload').onclick();await flush();assert(!stale.root.textContent.includes('Observation ID:'));
  console.log('PASS selection/remount cancels stale results; reload failure clears prior evidence');
  const app=fs.readFileSync(path.join(__dirname,'../public/nexus/app.js'),'utf8'),html=fs.readFileSync(path.join(__dirname,'../public/nexus/index.html'),'utf8');
  assert(app.includes("modellab:'Model Lab'"));assert(app.includes("['modellab','Model Lab','code']"));assert(app.includes('modellab:modelLabPage'));assert(html.indexOf('src="./model-lab.js"')<html.indexOf('src="./app.js"'));
  console.log('MODEL_LAB_OFFLINE_UI_PASS; DOM doubles only; real browser check pending');
}
main().catch(e=>{console.error(e);process.exitCode=1});
