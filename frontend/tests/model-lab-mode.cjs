const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const text=fs.readFileSync(process.argv[2],'utf8');
const match=text.match(/function setModeInfo\(\)\{([\s\S]*?)\n  \}\n  function nav/);
assert(match,'mode status function not found');
function run(page,mode,meta={},error=''){
  const nodes=Object.fromEntries(['sidebar-state','sidebar-mode','footer-data'].map(id=>[id,{textContent:'',previousElementSibling:{className:''}}]));
  const state={page,mode,data:{meta,generated_at:'fixed'},connectionError:error};
  const before=JSON.stringify(state);
  vm.runInNewContext('(function(){'+match[1]+'})()',{state,$:id=>nodes[id],C:{date:()=>'<date>'}});
  assert.equal(JSON.stringify(state),before,'status display mutated shared state');
  return nodes;
}
for(const mode of ['demo','api','import'])for(const error of ['','offline']){
  const n=run('modellab',mode,{},error);
  assert.equal(n['sidebar-state'].textContent,'Lab replay');
  assert.equal(n['sidebar-mode'].textContent,'LAB');
  assert.equal(n['sidebar-state'].previousElementSibling.className,'status-dot amber');
  assert(n['footer-data'].textContent.includes('Stored model results'));
}
for(const page of ['overview','allevents','copilot']){
  assert.equal(run(page,'demo')['sidebar-mode'].textContent,'DEMO');
  assert.equal(run(page,'api')['sidebar-mode'].textContent,'API');
  assert.equal(run(page,'api',{},'offline')['sidebar-mode'].textContent,'STALE');
  assert.equal(run(page,'import')['sidebar-mode'].textContent,'IMPORT');
  assert.equal(run(page,'api',{demo:true})['sidebar-mode'].textContent,'DEMO');
}
console.log('PASS Lab badge scoped to Model Lab; normal/demo/import/stale pages unchanged; shared state unchanged');
