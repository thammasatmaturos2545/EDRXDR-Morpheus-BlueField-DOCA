export type Obj = Record<string, unknown>;

const obj = (v: unknown): v is Obj => !!v && typeof v === "object" && !Array.isArray(v);
const str = (v: unknown) => typeof v === "string" && v.trim() ? v.trim() : null;
const int = (v: unknown) => typeof v === "number" && Number.isInteger(v) && v >= 0 ? v : null;
const finite = (v: unknown) => typeof v === "number" && Number.isFinite(v) ? v : null;
const date = (v: unknown) => { const s=str(v); return s && Number.isFinite(Date.parse(s)) ? s : null; };
const first = (...vs: unknown[]) => { for (const v of vs) { const s=str(v); if (s) return s; if (Array.isArray(v)) for (const x of v) { const n=str(x); if (n) return n; } } return null; };

function identity(r: Obj) {
  const s = obj(r.source) ? r.source : {};
  const topic = first(s.topic, r.source_topic, r.kafka_topic);
  const partition = int(s.partition ?? r.source_partition ?? r.kafka_partition);
  const offset = int(s.offset ?? r.source_offset ?? r.kafka_offset);
  const cluster = first(s.cluster_id, r.source_cluster_id, r.cluster_id) ?? "";
  const file = first(r.source_file, r.file);
  const line = int(r.source_line ?? r.line);
  return {
    uid: first(r.event_uid),
    hash: first(r.raw_sha256),
    source: topic && partition !== null && offset !== null ? JSON.stringify([cluster, topic, partition, offset]) : null,
    file: file && line !== null ? JSON.stringify([file, line]) : null,
  };
}

export function correlateWazuhAi(w: Obj, rows: Obj[], available=true) {
  if (!available) return {status:"unavailable", method:null, event:null};
  const wi = identity(w);
  const hits: {method:string,event:Obj}[] = [];
  for (const a of rows) {
    const ai = identity(a);
    const pairs: [keyof typeof wi,string][] = [["uid","event_uid"],["hash","raw_sha256"],["source","source_coordinates"],["file","source_file_line"]];
    const exact: string[] = [];
    let conflict=false;
    for (const [k,m] of pairs) if (wi[k] && ai[k]) { if (wi[k] !== ai[k]) { conflict=true; break; } exact.push(m); }
    if (!conflict && exact.length) {
      const method = ["event_uid","raw_sha256","source_coordinates","source_file_line"].find(x=>exact.includes(x))!;
      hits.push({method,event:a});
    }
  }
  if (!hits.length) return {status:"not_found", method:null, event:null};
  if (hits.length !== 1) return {status:"conflict", method:null, event:null};
  return {status:"matched", method:hits[0].method, event:hits[0].event};
}

const level = (r: Obj) => { const v=int(r.rule_level ?? r.wazuh_rule_level); return v !== null && v <= 15 ? v : null; };
const severity = (v:number|null) => v===null?"unknown":v>=12?"critical":v>=7?"high":v>=4?"medium":v>=1?"low":"info";
const liveAi = (p: unknown) => obj(p) && Array.isArray(p.events) ? p.events.filter((x): x is Obj => obj(x) && x.processing_mode==="live" && !!str(x.analysis_engine) && x.analysis_engine!=="morpheus-simulator") : [];
const score = (r: Obj|null) => { if (!r) return null; const v=finite(r.high_severity_score ?? r.threat_score); return v!==null && v>=0 && v<=1 ? v : null; };

export function buildNexusSnapshot(wazuhPayload: unknown, aiPayload: unknown, options:{hours?:number;generatedAt?:string;aiAvailable?:boolean}={}) {
  if (!obj(wazuhPayload) || !Array.isArray(wazuhPayload.alerts)) throw new Error("Invalid Wazuh payload");
  const generatedAt = date(options.generatedAt) ?? new Date().toISOString();
  const hours = [1,24,168].includes(options.hours ?? 24) ? (options.hours ?? 24) : 24;
  const aiAvailable = options.aiAvailable !== false;
  const ais = liveAi(aiPayload);
  const rows = wazuhPayload.alerts.filter((x): x is Obj => obj(x)).slice(0,100);

  const alerts = rows.map((r,i)=>{
    const l=level(r), c=correlateWazuhAi(r,ais,aiAvailable), a=c.event as Obj|null;
    const ts=date(r.timestamp ?? r["@timestamp"]) ?? generatedAt;
    const uid=first(r.event_uid), hash=first(r.raw_sha256);
    return {
      id:first(uid,hash,r.id) ?? `wazuh-${first(r.rule_id) ?? "unknown"}-${i}`,
      title:first(r.description,r.rule_description) ?? `Wazuh alert${first(r.rule_id)?` · Rule ${first(r.rule_id)}`:""}`,
      severity:severity(l), status:"new", host:first(r.agent_name) ?? "Unknown", ip:first(r.agent_ip,r.src_ip) ?? "", user:first(r.user,r.dst_user,r.src_user) ?? "",
      source:"Wazuh", category:first(r.category) ?? "Endpoint alert", tactic:first(r.mitre_tactic,r.tactic) ?? "Unmapped", technique:first(r.mitre_id,r.technique) ?? "", technique_name:first(r.mitre_technique,r.technique_name) ?? "",
      created_at:ts,last_seen:ts,description:first(r.description,r.rule_description) ?? "Wazuh alert loaded from the current API snapshot.",rule_id:first(r.rule_id,r.wazuh_rule_id) ?? "",
      evidence:{wazuh_level:l,event_uid:uid,raw_sha256:hash,ai_status:c.status,ai_match_method:c.method,ai_score:score(a),ai_class:a?first(a.predicted_label,a.threat_class):null,ai_engine:a?first(a.model_name,a.analysis_engine):null,ai_analysis_state:a?first(a.analysis_state):null,ai_routing_status:a?first(a.routing_status):null},
      timeline:[],tags:[]
    };
  });

  const events=alerts.map(a=>({id:`event-${a.id}`,timestamp:a.last_seen,host:a.host,ip:a.ip,user:a.user,source:"Wazuh",event_type:"wazuh_alert",severity:a.severity,message:a.description,process:"",event_id:a.id,raw:{id:a.id,rule_id:a.rule_id,wazuh_level:a.evidence.wazuh_level,event_uid:a.evidence.event_uid,raw_sha256:a.evidence.raw_sha256,ai_status:a.evidence.ai_status,ai_match_method:a.evidence.ai_match_method,ai_score:a.evidence.ai_score,ai_class:a.evidence.ai_class}}));
  const latest = rows.map(r=>date(r.timestamp ?? r["@timestamp"])).filter(Boolean).sort().at(-1) ?? null;
  return {
    schema_version:1, generated_at:generatedAt, window_hours:hours,
    summary:{events_total:events.length,avg_triage_minutes:null,series:[]},
    alerts,endpoints:[],events,cases:[],
    sources:latest?[{id:"wazuh",name:"Wazuh",kind:"endpoint",status:"healthy",events:alerts.length,last_seen:latest,description:"Current Wazuh API snapshot. Counts are loaded rows, not total historical ingestion."}]:[],
    meta:{demo:false,events_sampled:true,write_enabled:false,backend:"EDRXDR-Morpheus",description:aiAvailable?"Deterministic AI correlation only; no timestamp-nearness joins.":"Wazuh loaded; AI API unavailable. No AI result is inferred."}
  };
}
