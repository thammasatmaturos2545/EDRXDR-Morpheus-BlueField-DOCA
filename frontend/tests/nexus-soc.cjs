/* eslint-disable @typescript-eslint/no-require-imports */
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
const vm=require("node:vm");

const src=fs.readFileSync(path.join(__dirname,"../src/lib/nexus-soc.ts"),"utf8");
const out=ts.transpileModule(src,{
  compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}
}).outputText;
const scope={exports:{}};
vm.runInNewContext(out,scope);
const {correlateWazuhAi,buildNexusSnapshot}=scope.exports;

const ai={
  processing_mode:"live",
  analysis_engine:"real-engine",
  threat_score:0,
  threat_class:"low",
  event_uid:"uid-1",
  raw_sha256:"hash-1",
  source:{cluster_id:"c",topic:"wazuh-alerts",partition:0,offset:7}
};

assert.equal(
  correlateWazuhAi(
    {event_uid:"uid-1",raw_sha256:"hash-1",source:ai.source},
    [ai],true
  ).method,
  "event_uid"
);

assert.equal(
  correlateWazuhAi(
    {event_uid:"uid-1",raw_sha256:"DIFFERENT"},
    [ai],true
  ).status,
  "not_found"
);

assert.equal(
  correlateWazuhAi(
    {timestamp:"2026-10-14T00:00:00Z"},
    [{...ai,event_uid:null,raw_sha256:null,timestamp:"2026-10-14T00:00:00Z"}],
    true
  ).status,
  "not_found"
);

const snapshot=buildNexusSnapshot(
  {alerts:[
    {
      rule_level:0,
      rule_id:"100",
      description:"Real zero",
      agent_name:"WIN-01",
      event_uid:"uid-1",
      raw_sha256:"hash-1",
      source:ai.source,
      timestamp:"2026-10-14T00:00:00Z",
      full_log:"PRIVATE"
    },
    {
      rule_level:null,
      rule_id:"101",
      description:"Unknown level",
      agent_name:"WIN-02",
      timestamp:"2026-10-14T00:01:00Z"
    }
  ]},
  {events:[ai]},
  {hours:24,aiAvailable:true,generatedAt:"2026-10-14T01:00:00Z"}
);

assert.equal(snapshot.alerts[0].evidence.wazuh_level,0);
assert.equal(snapshot.alerts[0].evidence.ai_score,0);
assert.equal(snapshot.alerts[1].severity,"unknown");
assert.equal(snapshot.alerts[1].evidence.ai_status,"not_found");
assert.equal(JSON.stringify(snapshot).includes("PRIVATE"),false);

const html=fs.readFileSync(path.join(__dirname,"../public/nexus/index.html"),"utf8");
const app=fs.readFileSync(path.join(__dirname,"../public/nexus/app.js"),"utf8");
const core=fs.readFileSync(path.join(__dirname,"../public/nexus/core.js"),"utf8");

assert(html.includes("NEXUS"));
assert(html.includes("SIEM PLATFORM"));
assert(html.includes("EDR / XDR Lab"));

for (const label of [
  "Security overview",
  "Threat detection",
  "Endpoints",
  "Investigations",
  "Log explorer",
  "ATT&CK activity",
  "Data sources",
  "Settings"
]) assert(app.includes(label));

assert(app.includes("connect('/api/v1','')"));
assert(core.includes("'unknown'"));

console.log("PASS NEXUS exact uploaded ZIP UI + real EDR/XDR read adapter");
