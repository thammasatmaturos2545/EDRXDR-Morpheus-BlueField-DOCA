(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.SIEM = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const SEVERITIES = ['critical', 'high', 'medium', 'low', 'info', 'unknown'];
  const STATUSES = ['new', 'acknowledged', 'resolved'];
  const COLORS = {critical:'#f06c7e', high:'#f0ad57', medium:'#dec86b', low:'#538dff', info:'#8294b0', unknown:'#66758d'};
  const ATTACKS = [
    {title:'Suspicious PowerShell execution',category:'Execution',tactic:'Execution',technique:'T1059.001',name:'PowerShell',source:'Sysmon',process:'powershell.exe',parent:'winword.exe',command:'powershell.exe -NoProfile -EncodedCommand VwByAGkAdABlAC0ATwB1AHQAcAB1AHQAIABUAGUAbABlAG0AZQB0AHIAeQA=',description:'An Office application spawned PowerShell with an encoded argument. Validate the parent process, command content, and user activity before escalation.'},
    {title:'Credential access behavior detected',category:'Credential access',tactic:'Credential Access',technique:'T1003.001',name:'LSASS Memory',source:'EDR Agent',process:'rundll32.exe',parent:'cmd.exe',command:'rundll32.exe [redacted demo arguments]',description:'A process requested access to LSASS memory. The telemetry pattern matches a credential-access rule; confirm whether the process is an approved diagnostic tool.'},
    {title:'Unusual outbound connection',category:'Network',tactic:'Command and Control',technique:'T1071.001',name:'Web Protocols',source:'Suricata',process:'chrome.exe',parent:'explorer.exe',command:'Connection observed to 203.0.113.44:443',description:'Outbound HTTPS activity exceeded the host baseline and matched an example network detection. The destination is a documentation address in this demo.'},
    {title:'Multiple failed authentication attempts',category:'Identity',tactic:'Credential Access',technique:'T1110',name:'Brute Force',source:'Windows Events',process:'lsass.exe',parent:'wininit.exe',command:'Windows Security event 4625 × 24',description:'Repeated authentication failures were observed from a single source. Check the user, source host, and successful logons around the same time.'},
    {title:'Scheduled task created by unknown process',category:'Persistence',tactic:'Persistence',technique:'T1053.005',name:'Scheduled Task',source:'Sysmon',process:'schtasks.exe',parent:'powershell.exe',command:'schtasks.exe /Query /TN DemoHealthCheck',description:'Task telemetry matched an example persistence rule. Inspect the task definition, author, and execution path. The displayed demo command only queries a task.'},
    {title:'Unexpected service installation',category:'Persistence',tactic:'Persistence',technique:'T1543.003',name:'Windows Service',source:'Windows Events',process:'services.exe',parent:'wininit.exe',command:'Service event 7045: DemoService',description:'A new service was registered outside the approved change window. Confirm its binary signature and the account that installed it.'},
    {title:'Remote access activity across endpoints',category:'Lateral movement',tactic:'Lateral Movement',technique:'T1021.001',name:'Remote Desktop Protocol',source:'EDR Agent',process:'mstsc.exe',parent:'explorer.exe',command:'Remote desktop session observed',description:'A user connected to multiple endpoints in a short period. Review whether the activity matches an approved administration session.'},
    {title:'Archive creation on sensitive directory',category:'Collection',tactic:'Collection',technique:'T1560.001',name:'Archive via Utility',source:'EDR Agent',process:'7z.exe',parent:'cmd.exe',command:'7z.exe l C:\\Demo\\telemetry.zip',description:'Archive utility activity was observed near a sensitive directory. Validate the file list and the business reason. This demo command only lists an archive.'}
  ];
  function escape(value) { return String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
  function num(value) { return Number(value || 0).toLocaleString('en-US'); }
  function iso(ms) { return new Date(ms).toISOString(); }
  function timestamp(value) { const t = Date.parse(value); return Number.isFinite(t) ? t : 0; }
  function relative(value, now=Date.now()) {
    const minutes=Math.max(0, Math.floor((now-timestamp(value))/60000));
    return minutes < 1 ? 'Just now' : minutes < 60 ? minutes+'m ago' : minutes < 1440 ? Math.floor(minutes/60)+'h ago' : Math.floor(minutes/1440)+'d ago';
  }
  function date(value) { return timestamp(value) ? new Date(value).toLocaleString('en-GB',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit',timeZone:'Asia/Bangkok'})+' ICT' : 'Unavailable'; }
  function hours(range) { return {'1h':1,'24h':24,'7d':168}[range] || 24; }
  function seed(now=Date.now()) {
    let r=642813;
    const rand=()=>{r=(Math.imul(r,1664525)+1013904223)>>>0;return r/4294967296;};
    const endpoints=Array.from({length:128},(_,i)=>{
      const dept=['FIN','HR','IT','OPS'][i%4];
      return {id:'ep-'+(i+1),host:`WIN-${dept}-${String(i+1).padStart(3,'0')}`,ip:`10.10.${Math.floor(i/50)+1}.${i%50+20}`,os:i%9===0?'Ubuntu 24.04':'Windows 11',agent_version:'1.4.2',status:i<118?'online':'offline',risk:i<7?88-i*3:i<24?60-i:Math.floor(rand()*28),last_seen:iso(now-(i<118?Math.floor(rand()*180000):14400000+rand()*28800000)),user:['j.somchai','n.suda','it.admin','p.ananda'][i%4],department:dept};
    });
    const alerts=Array.from({length:64},(_,i)=>{
      const a=ATTACKS[i<20?0:i<31?1:i<40?2:i%8];
      const host=endpoints[i%32], minutes=i<9?i*3+2:25+(i-9)*18;
      const ts=now-minutes*60000, severity=i<7?'critical':i<24?'high':i<51?'medium':'low';
      const status=i%9===8?'resolved':i%5===3?'acknowledged':'new';
      return {id:`ALR-2026-${String(1042+i).padStart(4,'0')}`,title:a.title,severity,status,host:host.host,ip:host.ip,user:host.user,source:a.source,category:a.category,tactic:a.tactic,technique:a.technique,technique_name:a.name,created_at:iso(ts-90000),last_seen:iso(ts),description:a.description,rule_id:`NX-${a.technique.replace('.','-')}`,evidence:{process:a.process,parent_process:a.parent,command_line:a.command,pid:2024+i*17,process_path:`C:\\Windows\\System32\\${a.process}`,destination_ip:a.source==='Suricata'?'203.0.113.44':null,destination_port:a.source==='Suricata'?443:null},timeline:[{at:iso(ts-90000),action:'Detection rule matched',actor:'Correlation engine'},{at:iso(ts),action:'Alert added to investigation queue',actor:'NEXUS SIEM'},...(status==='new'?[]:[{at:iso(ts+60000),action:status==='resolved'?'Resolved after review':'Acknowledged by analyst',actor:'SOC Analyst'}])],tags:['demo',a.category.toLowerCase()]};
    });
    const events=Array.from({length:600},(_,i)=>{
      const host=endpoints[i%128], a=ATTACKS[i%8], ts=now-i*136000;
      return {id:'evt-'+(10000+i),timestamp:iso(ts),host:host.host,ip:host.ip,user:host.user,source:a.source,event_type:['process_start','network_connection','authentication','file_access','service_change'][i%5],severity:i%47===0?'high':i%13===0?'medium':'info',message:i%5===0?`${a.process} started by ${a.parent}`:i%5===1?'Outbound connection to 203.0.113.44:443':i%5===2?'User logon event observed':i%5===3?'File access: C:\\Demo\\report.csv':'Service status changed',process:a.process,event_id:[1,3,4624,11,7040][i%5],raw:{'@timestamp':iso(ts),'host.name':host.host,'source.ip':host.ip,'event.action':['process_start','network_connection','authentication','file_access','service_change'][i%5],demo:true}};
    });
    const counts=[530,480,405,390,345,310,460,840,1240,1590,1435,1870,1320,1655,1435,2130,1510,1840,1220,1035,1060,780,740,1060];
    const scale=24680/counts.reduce((a,b)=>a+b,0);
    const series=counts.map((n,i)=>{const ts=now-(23-i)*3600000;return {timestamp:iso(ts),events:Math.round(n*scale),alerts:alerts.filter(a=>timestamp(a.last_seen)<=ts && timestamp(a.last_seen)>ts-3600000).length};});
    series[23].events+=24680-series.reduce((n,p)=>n+p.events,0);
    const sources=[
      {id:'edr',name:'EDR Agent',kind:'endpoint',status:'healthy',events:9864,last_seen:iso(now-15000),description:'Process, file, and endpoint behavior telemetry.'},
      {id:'sysmon',name:'Sysmon',kind:'windows',status:'healthy',events:7490,last_seen:iso(now-27000),description:'Windows process creation, DNS, and network events.'},
      {id:'windows',name:'Windows Events',kind:'identity',status:'healthy',events:4820,last_seen:iso(now-35000),description:'Authentication, account, and security event logs.'},
      {id:'suricata',name:'Suricata',kind:'network',status:'healthy',events:2306,last_seen:iso(now-51000),description:'Network intrusion detection and connection telemetry.'},
      {id:'cloud',name:'Cloud Audit',kind:'cloud',status:'offline',events:200,last_seen:iso(now-5400000),description:'Cloud audit trail events from your configured collector.'}
    ];
    const cases=[
      {id:'INC-2026-008',title:'Investigate PowerShell activity on finance hosts',severity:'critical',status:'open',owner:'SOC Analyst',description:'Review encoded execution events and confirm the origin of the document.',alert_ids:[alerts[0].id,alerts[1].id],created_at:iso(now-2400000),comments:[]},
      {id:'INC-2026-007',title:'Credential access detection on WIN-IT-003',severity:'high',status:'investigating',owner:'SOC Analyst',description:'Validate diagnostic tool usage and process signature.',alert_ids:[alerts[21].id],created_at:iso(now-7200000),comments:[{at:iso(now-1800000),author:'SOC Analyst',text:'Endpoint owner contacted; awaiting confirmation of maintenance activity.'}]},
      {id:'INC-2026-006',title:'Repeated authentication failures',severity:'medium',status:'open',owner:'Identity Team',description:'Review the source of failed logons and recent password changes.',alert_ids:[alerts[43].id],created_at:iso(now-14400000),comments:[]},
      {id:'INC-2026-005',title:'Unusual outbound HTTPS traffic',severity:'high',status:'investigating',owner:'Network Team',description:'Inspect the connection timing and associated process.',alert_ids:[alerts[33].id],created_at:iso(now-21600000),comments:[]},
      {id:'INC-2026-004',title:'Scheduled task review',severity:'low',status:'closed',owner:'SOC Analyst',description:'Approved maintenance task, reviewed with the endpoint owner.',alert_ids:[alerts[52].id],created_at:iso(now-39600000),comments:[{at:iso(now-28800000),author:'SOC Analyst',text:'Confirmed as an approved scheduled maintenance task.'}]},
      {id:'INC-2026-003',title:'Service change validation',severity:'medium',status:'closed',owner:'SOC Analyst',description:'Service installation matched the approved change record.',alert_ids:[alerts[53].id],created_at:iso(now-64800000),comments:[]}
    ];
    return {schema_version:1,generated_at:iso(now),window_hours:24,summary:{events_total:24680,avg_triage_minutes:16,series},alerts,endpoints,events,sources,cases,meta:{demo:true,events_sampled:true,events_loaded:events.length,description:'Synthetic lab telemetry. Log Explorer shows the most recent 600 sample events; volume metrics are demo aggregate counts.'}};
  }
  function str(v, max=1000) { return typeof v==='string' ? v.slice(0,max) : v==null ? '' : String(v).slice(0,max); }
  function finite(v, fallback=0) { return Number.isFinite(Number(v)) && Number(v)>=0 ? Number(v) : fallback; }
  function validTime(v, fallback) { return timestamp(v) ? str(v,40) : fallback; }
  function enumValue(v, values, fallback) { const s=str(v,40).toLowerCase(); return values.includes(s)?s:fallback; }
  function validateSnapshot(input) {
    if (!input || typeof input!=='object' || !Array.isArray(input.alerts) || !Array.isArray(input.endpoints) || !Array.isArray(input.events)) throw new Error('Snapshot must contain alerts, endpoints, and events arrays.');
    if (input.schema_version && input.schema_version!==1) throw new Error('Unsupported schema_version. Use schema_version: 1.');
    const lists=['alerts','endpoints','events','cases','sources'];
    for (const key of lists) if(input[key] && (!Array.isArray(input[key]) || input[key].length>10000)) throw new Error(key+' must be an array with at most 10,000 records.');
    const generated=validTime(input.generated_at,iso(Date.now()));
    const seen=new Set();
    function rows(key, convert){return (input[key]||[]).map((row,i)=>{if(!row || typeof row!=='object' || Array.isArray(row))throw new Error(`Invalid ${key} record ${i+1}.`);const value=convert(row,i);const uid=key+':'+value.id;if(seen.has(uid))throw new Error(`Duplicate ${key} id: ${value.id}`);seen.add(uid);return value;});}
    const alerts=rows('alerts',(a,i)=>({id:str(a.id||'alert-'+i,120),title:str(a.title||a.message||'Untitled detection',240),severity:enumValue(a.severity,SEVERITIES,'info'),status:enumValue(a.status,STATUSES,'new'),host:str(a.host||'Unknown',160),ip:str(a.ip,60),user:str(a.user,120),source:str(a.source||'API',80),category:str(a.category||'Detection',80),tactic:str(a.tactic||'Unmapped',80),technique:str(a.technique,30),technique_name:str(a.technique_name||a.technique,160),created_at:validTime(a.created_at,null),last_seen:validTime(a.last_seen||a.created_at,null),description:str(a.description,5000),rule_id:str(a.rule_id,100),evidence: a.evidence && typeof a.evidence==='object'&&!Array.isArray(a.evidence)?JSON.parse(JSON.stringify(a.evidence)): {},timeline:Array.isArray(a.timeline)?a.timeline.slice(0,100).map(t=>({at:validTime(t.at,generated),action:str(t.action,500),actor:str(t.actor,100)})):[],tags:Array.isArray(a.tags)?a.tags.slice(0,20).map(t=>str(t,80)):[]}));
    const endpoints=rows('endpoints',(e,i)=>({id:str(e.id||'endpoint-'+i,120),host:str(e.host||'Unknown',160),ip:str(e.ip,60),os:str(e.os||'Unknown',100),agent_version:str(e.agent_version||'Unknown',80),status:enumValue(e.status,['online','offline','unknown'],'unknown'),risk:(typeof e.risk==='number'&&Number.isFinite(e.risk)&&e.risk>=0&&e.risk<=100?e.risk:null),last_seen:validTime(e.last_seen,null),user:str(e.user,120),department:str(e.department||'Unassigned',80)}));
    const events=rows('events',(e,i)=>({id:str(e.id||'event-'+i,120),timestamp:validTime(e.timestamp||e['@timestamp'],null),host:str(e.host||'Unknown',160),ip:str(e.ip,60),user:str(e.user,120),source:str(e.source||'API',80),event_type:str(e.event_type||'event',100),severity:enumValue(e.severity,SEVERITIES,'info'),message:str(e.message,6000),process:str(e.process,200),event_id:str(e.event_id,80),raw:e.raw&&typeof e.raw==='object'?JSON.parse(JSON.stringify(e.raw)):JSON.parse(JSON.stringify(e))}));
    const cases=rows('cases',(c,i)=>({id:str(c.id||'case-'+i,120),title:str(c.title||'Untitled case',240),severity:enumValue(c.severity,SEVERITIES,'medium'),status:enumValue(c.status,['open','investigating','closed'],'open'),owner:str(c.owner||'Unassigned',120),description:str(c.description,5000),alert_ids:Array.isArray(c.alert_ids)?c.alert_ids.slice(0,1000).map(a=>str(a,120)):[],created_at:validTime(c.created_at,generated),comments:Array.isArray(c.comments)?c.comments.slice(0,1000).map(c=>({at:validTime(c.at,generated),author:str(c.author,100),text:str(c.text,5000)})):[]}));
    const sources=rows('sources',(s,i)=>({id:str(s.id||'source-'+i,120),name:str(s.name||'Unnamed source',80),kind:enumValue(s.kind,['endpoint','windows','identity','network','cloud'],'endpoint'),status:enumValue(s.status,['healthy','degraded','offline','unknown'],'unknown'),events:finite(s.events),last_seen:validTime(s.last_seen,null),description:str(s.description,1000)}));
    const summary=input.summary&&typeof input.summary==='object'?input.summary:{};
    const series=Array.isArray(summary.series)?summary.series.slice(0,336).map(p=>({timestamp:validTime(p.timestamp,generated),events:finite(p.events),alerts:finite(p.alerts)})).sort((a,b)=>timestamp(a.timestamp)-timestamp(b.timestamp)):[];
    return {schema_version:1,generated_at:generated,window_hours:finite(input.window_hours,24)||24,summary:{events_total:finite(summary.events_total,events.length),avg_triage_minutes:summary.avg_triage_minutes==null?null:finite(summary.avg_triage_minutes),series},alerts,endpoints,events,sources,cases,meta:{demo:Boolean(input.meta?.demo),events_sampled:Boolean(input.meta?.events_sampled),events_loaded:events.length,description:str(input.meta?.description,2000),write_enabled:input.meta?.write_enabled!==false,backend:str(input.meta?.backend,100)}};
  }
  function matchesQuery(row,query,kind='alert') {
    const parts=(query||'').match(/(?:[^\s"]+|"[^"]*")+/g)||[];
    const fields={host:row.host,ip:row.ip,user:row.user,source:row.source,severity:row.severity,status:row.status,technique:row.technique,event:row.event_type,id:row.id,process:row.process||row.evidence?.process};
    const all=[row.title,row.id,row.message,row.host,row.ip,row.user,row.source,row.technique,row.technique_name,row.category,row.process,row.event_type].filter(Boolean).join(' ').toLowerCase();
    return parts.every(part=>{
      let negative=part.startsWith('-');if(negative)part=part.slice(1);
      const colon=part.indexOf(':');let found;
      if(colon>0 && Object.prototype.hasOwnProperty.call(fields,part.slice(0,colon).toLowerCase())){const key=part.slice(0,colon).toLowerCase(),value=part.slice(colon+1).replace(/^"|"$/g,'').toLowerCase();found=String(fields[key]||'').toLowerCase().includes(value);}
      else found=all.includes(part.replace(/^"|"$/g,'').toLowerCase());
      return negative?!found:found;
    });
  }
  function inRange(time,range,now=Date.now()){const t=timestamp(time);return t>=now-hours(range)*3600000 && t<=now+60000;}
  function filterAlerts(data,{query='',severity='all',status='all',range='24h',source='',host='',technique='',sort='newest'}={},now=Date.now()){
    const rows=data.alerts.filter(a=>inRange(a.last_seen,range,now) && (severity==='all'||a.severity===severity) && (status==='all'||a.status===status||status==='active'&&a.status!=='resolved') && (!source||a.source===source) && (!host||a.host===host) && (!technique||a.technique===technique) && matchesQuery(a,query));
    return rows.sort((a,b)=>sort==='severity'?SEVERITIES.indexOf(a.severity)-SEVERITIES.indexOf(b.severity)||timestamp(b.last_seen)-timestamp(a.last_seen):timestamp(b.last_seen)-timestamp(a.last_seen));
  }
  function filterEvents(data,{query='',severity='all',source='',range='24h'}={},now=Date.now()){return data.events.filter(e=>inRange(e.timestamp,range,now) && (severity==='all'||e.severity===severity) && (!source||e.source===source) && matchesQuery(e,query,'event')).sort((a,b)=>timestamp(b.timestamp)-timestamp(a.timestamp));}
  function coverage(alerts){const m=new Map();for(const a of alerts){if(!a.technique)continue;if(!m.has(a.technique))m.set(a.technique,{id:a.technique,name:a.technique_name||a.technique,tactic:a.tactic,count:0});m.get(a.technique).count++;}return [...m.values()].sort((a,b)=>b.count-a.count);}
  function stats(data,range='24h',now=Date.now()) {
    const alerts=filterAlerts(data,{range},now),active=alerts.filter(a=>a.status!=='resolved');
    const fullWindow=hours(range)>=data.window_hours;
    const series=fullWindow?data.summary.series:data.summary.series.filter(p=>timestamp(p.timestamp)>now-hours(range)*3600000 && timestamp(p.timestamp)<=now+60000);
    const total=fullWindow?data.summary.events_total:series.length?series.reduce((n,p)=>n+p.events,0):filterEvents(data,{range},now).length;
    return {events:total,alerts:active.length,critical:active.filter(a=>a.severity==='critical').length,endpoints:data.endpoints.length,online:data.endpoints.filter(e=>e.status==='online').length,cases:data.cases.filter(c=>c.status!=='closed').length,triage:data.summary.avg_triage_minutes,series,alertRows:alerts,activeRows:active,severity:SEVERITIES.map(s=>({name:s,count:active.filter(a=>a.severity===s).length,color:COLORS[s]}))};
  }
  function csv(records,columns){const safe=v=>{let value=String(v??'');if(/^[\s]*[=+@-]/.test(value))value="'"+value;return '"'+value.replace(/"/g,'""')+'"';};return '\ufeff'+[columns.map(safe).join(','),...records.map(r=>columns.map(c=>safe(typeof r[c]==='object'?JSON.stringify(r[c]):r[c])).join(','))].join('\r\n');}
  function techniqueUrl(id){return /^T\d{4}(\.\d{3})?$/.test(id)?'https://attack.mitre.org/techniques/'+id.replace('.','/')+'/':null;}
  return {SEVERITIES,STATUSES,COLORS,ATTACKS,escape,num,iso,timestamp,relative,date,hours,seed,validateSnapshot,matchesQuery,inRange,filterAlerts,filterEvents,coverage,stats,csv,techniqueUrl};
});
