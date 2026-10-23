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

function findButton(root){
  for(const n of root.children){if(n.tag==='button'&&n.textContent==='สร้างสรุปจากหลักฐานล่าสุด')return n;
    const found=findButton(n);if(found)return found;}
}
const generated=()=>({provider:'local-vllm',summary_status:'generated_unreviewed',human_review_required:true,
  production_ready:false,automated_response_allowed:false,external_transfer_allowed:false,
  input_evidence_hash:'a'.repeat(64),evidence:{input_evidence_hash:'a'.repeat(64),results:[{event_uid:uid,evidence_status:'matched'}]},
  draft:{summary_th:{text:'สรุปร่างสังเคราะห์',evidence_uids:[uid]},facts:[],hypotheses:[],unknowns:[],suggested_checks:[]},
  model:'synthetic-test-double',generated_at:'2026-10-24T00:00:00Z'});
(async()=>{
  for(const mode of ['success','hash-change','foreign-citation','mock','failure','auth']){
    let posts=0;
    const item=setup(async(url,options)=>{
      if(url.endsWith('/evidence'))return {ok:true,json:async()=>payload()};
      posts++;assert.equal(url,'/api/nexus/v1/copilot/draft');
      assert.deepEqual(JSON.parse(options.body),{event_uids:[uid]});
      if(mode==='failure')return {ok:false,status:503};
      if(mode==='auth')return {ok:false,status:401};
      const out=generated();
      if(mode==='hash-change')out.input_evidence_hash='b'.repeat(64);
      if(mode==='foreign-citation')out.draft.summary_th.evidence_uids=[second];
      if(mode==='mock'){out.provider='mock';out.summary_status='mock_unreviewed';}
      return {ok:true,json:async()=>out};
    });
    item.api.select(uid);await flush();assert.equal(posts,0);
    const button=findButton(item.root);assert(button);await button.onclick();
    assert.equal(posts,1);
    assert.equal(item.root.textContent.includes('สรุปร่างสังเคราะห์'),mode==='success');
    if(mode==='auth')assert(!item.root.textContent.includes('Wazuh 7'));
  }
  console.log('PASS explicit click sends UID only; no automatic generation');
  console.log('PASS draft requires matching evidence hash, exact citations and real-provider status');
  console.log('PASS unavailable/auth clears draft and never reuses old text');
  let finish;
  const raced=setup(async(url)=>url.endsWith('/evidence')?{ok:true,json:async()=>payload()}:
    new Promise(resolve=>{finish=resolve;}));
  raced.api.select(uid);await flush();const pending=findButton(raced.root).onclick();await flush();
  raced.api.select(second);await flush();finish({ok:true,json:async()=>generated()});await pending;
  assert(!raced.root.textContent.includes('สรุปร่างสังเคราะห์'));
  console.log('PASS late generation cannot overwrite new selection; DOM doubles only, no LLM');
})().catch(e=>{console.error(e);process.exitCode=1;});
