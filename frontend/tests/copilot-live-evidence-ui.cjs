const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
class Node {
  constructor(tag){this.tag=tag;this.children=[];this.text='';}
  append(...children){this.children.push(...children);}
  replaceChildren(...children){this.children=children;this.text='';}
  set textContent(v){this.text=String(v);this.children=[];}
  get textContent(){return this.text+this.children.map(x=>x.textContent).join('');}
  set innerHTML(v){throw Error('Unsafe HTML sink');}
}
const uid='1'.repeat(64), second='2'.repeat(64);
function payload(id=uid, ai='matched'){
  return {schema_version:'local-evidence-v1',evidence_only:true,summary_status:'not_requested',
    automated_response_allowed:false,external_transfer_allowed:false,production_ready:false,
    input_evidence_hash:'a'.repeat(64),complete:true,results:[{event_uid:id,evidence_status:'matched',
      source_ref:{index:'wazuh-alerts-4.x-2026.10.14',id:'synthetic'},
      fact:{event_uid:id,description:'<script>not executable</script>',rule_id:'533',timestamp_utc:null,
        wazuh_level:7,ai_status:ai,ai_score:ai==='matched'?0:null,ai_label:ai==='matched'?'low_severity':null}}]};
}
function setup(fetcher){
  const root=new Node('section'),location={hash:'#copilot'},window={addEventListener(){}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../public/nexus/copilot-evidence.js'),'utf8'),{
    window,location,document:{getElementById:()=>root,createElement:tag=>new Node(tag)},
    fetch:fetcher,AbortController,setTimeout,clearTimeout,Date,
  });
  return {root,api:window.NexusCopilotEvidence,location};
}
const flush=()=>new Promise(setImmediate);
(async()=>{
  const requests=[];
  const ui=setup(async(url,options)=>{requests.push({url,options});return {ok:true,status:200,json:async()=>payload()};});
  ui.api.select(uid);await flush();
  assert.deepEqual(JSON.parse(requests[0].options.body),{event_uids:[uid]});
  assert.equal(requests[0].options.credentials,'same-origin');assert.equal(requests[0].options.cache,'no-store');
  assert(ui.root.textContent.includes('0.0 / 100'));assert(ui.root.textContent.includes('<script>not executable</script>'));
  assert(ui.root.textContent.includes('ยังไม่สร้างสรุป'));
  ui.api.select('<bad>');assert.equal(ui.api.selected(),uid);
  console.log('PASS sends UID only, safe text, genuine zero and evidence-only display');
  for(const ai of ['not_scored','conflict','unavailable']){
    const item=setup(async()=>({ok:true,json:async()=>payload(uid,ai)}));item.api.select(uid);await flush();
    assert(item.root.textContent.includes('AI: '+ai));assert(!item.root.textContent.includes('0.0 / 100'));
  }
  console.log('PASS all four AI statuses remain distinct');
  for(const status of [401,403,429,503]){
    const item=setup(async()=>({ok:false,status}));item.api.select(uid);await flush();
    assert(!item.root.textContent.includes('Wazuh 7'));
    if(status===401)assert(item.root.children.at(-1).children.some(n=>n.href==='/api/nexus/v1/copilot/review'));
  }
  for(const data of [payload(second),{...payload(),summary_status:'generated'},
    {...payload(),results:[{event_uid:uid,evidence_status:'unavailable',fact:null}],complete:false}]){
    const item=setup(async()=>({ok:true,json:async()=>data}));item.api.select(uid);await flush();
    assert(!item.root.textContent.includes('Wazuh 7'));
  }
  console.log('PASS denial, disabled, malformed, foreign UID and unavailable never show facts');
  let resolveOld;
  const race=setup(async(_,opts)=>JSON.parse(opts.body).event_uids[0]===uid ?
    new Promise(resolve=>{resolveOld=resolve;}) : {ok:true,json:async()=>payload(second)});
  race.api.select(uid);await flush();race.api.select(second);await flush();
  resolveOld({ok:true,json:async()=>payload(uid)});await flush();
  assert(race.root.textContent.includes(second));assert(!race.root.textContent.includes(uid));
  console.log('PASS selection clears previous data and ignores late responses');
  const app=fs.readFileSync(path.join(__dirname,'../public/nexus/app.js'),'utf8');
  const history=fs.readFileSync(path.join(__dirname,'../public/nexus/all-events.js'),'utf8');
  const html=fs.readFileSync(path.join(__dirname,'../public/nexus/index.html'),'utf8');
  assert(app.includes('id="copilot-live-root"'));assert(history.includes('window.NexusCopilotEvidence.select(uid)'));
  assert(html.indexOf('./copilot-evidence.js')<html.indexOf('./app.js'));
  console.log('PASS History entry point and isolated Copilot panel wiring; offline only');
})().catch(e=>{console.error(e);process.exitCode=1;});
