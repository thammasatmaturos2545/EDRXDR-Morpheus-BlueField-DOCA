(function () {
  'use strict';
  const C=window.SIEM, E=C.escape, N=C.num;
  const paths={
    overview:'<rect x="3" y="3" width="7" height="7" rx="1.4"/><rect x="14" y="3" width="7" height="7" rx="1.4"/><rect x="3" y="14" width="7" height="7" rx="1.4"/><rect x="14" y="14" width="7" height="7" rx="1.4"/>',
    shield:'<path d="m12 3 8 3v6c0 4-3.5 7.3-8 9-4.5-1.7-8-5-8-9V6Z"/><path d="m9 12 2 2 4-4"/>',
    alerts:'<path d="m12 3 10 18H2Z"/><path d="M12 9v5m0 3h.01"/>',
    endpoints:'<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 21h8m-4-5v5"/>',
    cases:'<path d="M3 7a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/><path d="M8 12h8m-8 4h5"/>',
    logs:'<path d="m4 6 4 4-4 4m8 1h8M3 21h18V3H3Z"/>',
    coverage:'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><path d="M12 1v4m0 14v4M1 12h4m14 0h4"/>',
    flask:'<path d="M9 3h6m-5 0v7l-5.5 8a2 2 0 0 0 1.7 3h11.6a2 2 0 0 0 1.7-3L14 10V3"/><path d="M8 15h8"/>',
    integrations:'<rect x="9" y="2" width="6" height="6" rx="1"/><rect x="2" y="16" width="6" height="6" rx="1"/><rect x="16" y="16" width="6" height="6" rx="1"/><path d="M12 8v4H5v4m7-4h7v4"/>',
    settings:'<path d="m9 3-1 3-3 1-1 4 2 2v3l3 2 1 3h4l1-3 3-2v-3l2-2-1-4-3-1-1-3Z"/><circle cx="12" cy="12" r="3"/>',
    search:'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
    bell:'<path d="M5 17h14l-2-3V9a5 5 0 0 0-10 0v5Zm5 3h4"/>',
    help:'<circle cx="12" cy="12" r="9"/><path d="M9 9a3 3 0 0 1 6 0c0 2-3 2-3 4m0 4h.01"/>',
    right:'<path d="m9 5 7 7-7 7"/>',
    arrow:'<path d="M4 12h16m-6-6 6 6-6 6"/>',
    refresh:'<path d="M20 6v5h-5M4 18v-5h5"/><path d="M6 7a7 7 0 0 1 11-2l3 6M4 13l3 6a7 7 0 0 0 11-2"/>',
    export:'<path d="M12 3v12m-4-4 4 4 4-4M4 15v5h16v-5"/>',
    clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    activity:'<path d="M2 12h4l3-8 6 16 3-8h4"/>',
    info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10h.01"/>',
    close:'<path d="m6 6 12 12M6 18 18 6"/>',
    check:'<path d="m5 12 4 4L19 6"/>',
    plus:'<path d="M12 4v16M4 12h16"/>',
    copy:'<rect x="8" y="8" width="12" height="13" rx="2"/><path d="M16 8V3H3v13h5"/>',
    menu:'<path d="M3 6h18M3 12h18M3 18h18"/>',
    network:'<circle cx="12" cy="5" r="2"/><circle cx="5" cy="19" r="2"/><circle cx="19" cy="19" r="2"/><path d="M12 7v6H5v4m7-4h7v4"/>',
    cloud:'<path d="M7 18a5 5 0 1 1 0-10 6 6 0 0 1 11-1 5 5 0 0 1 0 11Z"/>',
    windows:'<path d="M3 4h8v7H3Zm10 0h8v7h-8ZM3 13h8v7H3Zm10 0h8v7h-8Z"/>',
    identity:'<circle cx="9" cy="7" r="3"/><path d="M3 20v-3a6 6 0 0 1 12 0v3m2-9 2 2 3-3"/>',
    upload:'<path d="M12 15V3m-4 4 4-4 4 4M4 15v5h16v-5"/>',
    link:'<path d="m10 13 4-4m-6 7-2 2a4 4 0 0 1-6-6l4-4a4 4 0 0 1 6 0m2 0 2-2a4 4 0 0 1 6 6l-4 4a4 4 0 0 1-6 0"/>',
    external:'<path d="M14 3h7v7m0-7-10 10M10 3H3v18h18v-7"/>',
    filter:'<path d="M3 4h18l-7 8v7l-4 2v-9Z"/>',
    code:'<path d="m8 6-6 6 6 6m8-12 6 6-6 6m-3-15-2 18"/>'
  };
  const icon=(name,extra='')=>`<svg class="icon ${extra}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name]||paths.shield}</svg>`;
  const pages={copilot:'SOC Copilot',allevents:'All Events',overview:'Security overview',alerts:'Threat detection',endpoints:'Endpoint inventory',cases:'Investigations',logs:'Log explorer',coverage:'ATT&CK activity',research:'Research & Experiments',modeldetails:'Model Quality Details',researchevidence:'Research Evidence',shadowdetails:'Shadow Details',bluefielddetails:'BlueField Details',integrations:'Data sources',settings:'Settings'};
  function readLocal(key,fallback){try{return JSON.parse(localStorage.getItem(key))||fallback;}catch{return fallback;}}
  const prefs=readLocal('nexus.preferences.v1',{});
  const state={page:pages[location.hash.slice(1)]?location.hash.slice(1):'overview',range:prefs.range||'24h',mode:'demo',data:C.seed(),apiBase:prefs.apiBase||'/api/v1',token:'',refreshSeconds:prefs.refreshSeconds||0,connected:false,connectionError:'',lastFetch:null,busy:false,alertFilter:{query:'',severity:'all',status:'active',sort:'newest',source:'',host:'',technique:''},logFilter:{query:'',severity:'all',source:''},endpointFilter:{query:'',status:'all'},alertPage:1,eventPage:1,endpointPage:1,selected:new Set(),detail:null,tab:'summary',focused:null};
  const $=id=>document.getElementById(id);
  let timer=null,returnFocus=null;
  const safeStorage=(key,value)=>{try{localStorage.setItem(key,JSON.stringify(value));return true;}catch{toast('Browser storage is unavailable. Changes remain in this session.',true);return false;}};
  function savePreferences(){safeStorage('nexus.preferences.v1',{apiBase:state.apiBase,range:state.range,refreshSeconds:state.refreshSeconds});}
  function applyDemoState(){const d=readLocal('nexus.demo.v1',{});if(d.alerts)for(const a of state.data.alerts){if(C.STATUSES.includes(d.alerts[a.id]?.status)){a.status=d.alerts[a.id].status;const t=d.alerts[a.id].timeline;if(Array.isArray(t))a.timeline=t;}}if(Array.isArray(d.cases))try{state.data.cases=C.validateSnapshot({...state.data,cases:d.cases}).cases;}catch{} }
  function saveDemoState(){if(state.mode!=='demo')return;safeStorage('nexus.demo.v1',{alerts:Object.fromEntries(state.data.alerts.map(a=>[a.id,{status:a.status,timeline:a.timeline}])),cases:state.data.cases});}
  applyDemoState();
  function toast(message,error=false){const el=document.createElement('div');el.className='toast'+(error?' error':'');el.innerHTML=icon(error?'alerts':'check')+`<span>${E(message)}</span>`;$('toasts').appendChild(el);setTimeout(()=>el.remove(),5500);}
  function setModeInfo(){
    const real=state.mode==='api'&&!state.data.meta?.demo,stale=state.mode==='api'&&!!state.connectionError;
    $('sidebar-state').textContent=stale?'Connection interrupted':real?'API connected':state.mode==='import'?'Snapshot loaded':'Sample telemetry';
    $('sidebar-mode').textContent=stale?'STALE':real?'API':state.mode==='import'?'IMPORT':'DEMO';
    $('sidebar-state').previousElementSibling.className='status-dot '+(stale?'red':real?'green':'amber');
    $('footer-data').textContent=stale?'Showing the last successful snapshot':real?'Connected API · '+C.date(state.data.generated_at):state.mode==='import'?'Imported snapshot · '+C.date(state.data.generated_at):'Demo telemetry · for evaluation';
  }
  function nav(){const stats=C.stats(state.data,state.range,referenceTime());const items=[['overview','Overview','overview'],['alerts','Threat detection','alerts'],['allevents','All Events','logs'],['copilot','SOC Copilot','code'],['endpoints','Endpoints','endpoints'],['cases','Investigations','cases'],['logs','Log explorer','logs'],['coverage','ATT&CK activity','coverage']];const navItem=([id,name,i])=>`<a class="nav-link ${state.page===id?'active':''}" href="#${id}" ${state.page===id?'aria-current="page"':''}>${icon(i)}<span>${name}</span>${id==='alerts'&&stats.critical?`<span class="nav-count">${stats.critical}</span>`:''}</a>`;$('main-nav').innerHTML=items.map(navItem).join('');$('breadcrumb-current').textContent=pages[state.page];setModeInfo();}
  function modeBadge(){const stale=state.mode==='api'&&state.connectionError,real=state.mode==='api'&&!state.data.meta?.demo;return `<span class="mode-pill ${stale?'error':real?'live':''}"><span class="status-dot ${stale?'red':real?'green':'amber'}"></span>${stale?'CONNECTION LOST':real?'API CONNECTED':state.mode==='import'?'IMPORTED SNAPSHOT':state.mode==='api'?'API DEMO':'DEMO MODE'}</span>`;}
  function pageHeading(title,subtitle,actions=''){return `<div class="page-heading"><div><div class="eyebrow">SECURITY OPERATIONS <span>/</span> ${state.page==='overview'?'MONITORING':E(state.page.toUpperCase())}</div><h1>${title}</h1><p class="page-subtitle">${subtitle}</p></div><div class="page-actions">${modeBadge()}${['overview','alerts','logs','coverage'].includes(state.page)?`<select class="select" id="time-range" aria-label="Time range">${[['1h','Last 1 hour'],['24h','Last 24 hours'],['7d','Last 7 days']].map(([k,n])=>`<option value="${k}" ${state.range===k?'selected':''}>${n}</option>`).join('')}</select>`:''}${actions||`<button class="button" data-action="refresh" ${state.busy?'disabled':''}>${icon('refresh',state.busy?'spinning':'')}Refresh</button>`}</div></div>${state.connectionError?`<div class="notice warn section-gap">${icon('alerts')}<div>API connection interrupted. Displaying the last successful snapshot.<br><span class="form-help">${E(state.connectionError)}</span></div><button class="link-button" data-action="refresh">Retry</button></div>`:''}${state.mode==='demo'||state.data.meta?.demo?`<div class="demo-banner">${icon('info')}<span>Demo workspace · All telemetry is synthetic. Explore the investigation workflow.</span><button data-action="navigate" data-page="integrations">Connect your data ${icon('arrow')}</button></div>`:state.mode==='import'?`<div class="demo-banner">${icon('info')}<span>Imported snapshot · Captured ${E(C.date(state.data.generated_at))}. Changes stay in this browser session.</span><button data-action="navigate" data-page="integrations">Connect an API ${icon('arrow')}</button></div>`:''}`;}
  function referenceTime(){return state.mode==='import'?C.timestamp(state.data.generated_at):Date.now();}
  function spark(color='blue',values=[]){if(values.length<2)return '';const max=Math.max(1,...values),path=values.map((n,i)=>`${i?'L':'M'}${(1+i/(values.length-1)*74).toFixed(1)},${(25-n/max*23).toFixed(1)}`).join(' ');return `<svg class="metric-spark" viewBox="0 0 76 26" aria-hidden="true"><path class="spark-area" d="${path}L75,26H1Z"/><path class="spark-line" style="stroke:${color==='red'?'var(--red)':'var(--blue)'}" d="${path}"/></svg>`;}
  function metrics(){const s=C.stats(state.data,state.range,referenceTime());return `<div class="metric-grid"><div class="metric-card"><div class="metric-label">Events ingested<span class="metric-icon">${icon('activity')}</span></div><div class="metric-value">${N(s.events)}</div><div class="metric-bottom"><strong>${N(state.data.sources.filter(s=>s.status==='healthy').length)} sources active</strong><span>in selected window</span></div>${spark('blue',s.series.map(p=>p.events))}</div><div class="metric-card"><div class="metric-label">Active alerts<span class="metric-icon red">${icon('alerts')}</span></div><div class="metric-value">${N(s.alerts)}</div><div class="metric-bottom"><strong class="urgent">${s.critical} critical</strong><span>require review</span></div>${spark('red',s.series.map(p=>p.alerts))}</div><div class="metric-card"><div class="metric-label">Monitored endpoints<span class="metric-icon green">${icon('endpoints')}</span></div><div class="metric-value">${N(s.endpoints)}</div><div class="metric-bottom"><strong>${s.online} online</strong><span>of ${s.endpoints} enrolled</span></div></div><div class="metric-card"><div class="metric-label">Mean time to triage<span class="metric-icon purple">${icon('clock')}</span></div><div class="metric-value">${s.triage==null?'—':N(s.triage)} ${s.triage==null?'':'<small>min</small>'}</div><div class="metric-bottom"><strong>${s.cases} open cases</strong><span>under investigation</span></div></div></div>`;}
  function trend(){const s=C.stats(state.data,state.range,referenceTime());let points=s.series;if(!points.length){const count=24,step=C.hours(state.range)*3600000/count,now=referenceTime();points=Array.from({length:count},(_,i)=>({timestamp:C.iso(now-(count-1-i)*step),events:0,alerts:0}));for(const ev of C.filterEvents(state.data,{range:state.range},referenceTime())){const index=Math.max(0,Math.min(count-1,Math.floor((C.timestamp(ev.timestamp)-(now-count*step))/step)));points[index].events++;}for(const a of s.alertRows){const index=Math.max(0,Math.min(count-1,Math.floor((C.timestamp(a.last_seen)-(now-count*step))/step)));points[index].alerts++;}}
    const max=Math.max(1,...points.map(p=>p.events)),amax=Math.max(1,...points.map(p=>p.alerts)),w=700,h=145,left=40,right=30,bottom=24,plotW=w-left-right,plotH=h-bottom-9;
    const xy=(p,i,type)=>[left+(points.length===1?plotW/2:i/(points.length-1)*plotW),9+plotH-(p[type]/(type==='events'?max:amax))*plotH];
    const line=type=>points.map((p,i)=>`${i?'L':'M'}${xy(p,i,type).map(n=>n.toFixed(1)).join(',')}`).join(' '),area=line('events')+` L${xy(points.at(-1),points.length-1,'events')[0]},${h-bottom} L${left},${h-bottom} Z`;
    const grids=[0,.5,1].map(v=>{const y=9+plotH-v*plotH;return `<line x1="${left}" x2="${w-right}" y1="${y}" y2="${y}" stroke="#27354a" stroke-dasharray="3 4"/><text x="${left-9}" y="${y+3}" text-anchor="end">${v===0?'0':N(Math.round(max*v))}</text><text x="${w-right+8}" y="${y+3}" fill="#aa8bef">${Math.round(amax*v)}</text>`;}).join('');
    const xlabels=points.filter((_,i)=>i===0||i===points.length-1||i%Math.max(1,Math.floor(points.length/5))===0).map(p=>{const i=points.indexOf(p),x=xy(p,i,'events')[0],label=new Date(p.timestamp).toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit',timeZone:'Asia/Bangkok'});return `<text x="${x}" y="${h-4}" text-anchor="middle">${label}</text>`;}).join('');
    return `<div class="panel chart-panel"><div class="panel-header"><div><h2>Event activity</h2><p class="panel-subtitle">Telemetry volume and detection activity</p></div><div class="chart-legend"><span class="legend-item"><i class="legend-dot"></i>Events · left</span><span class="legend-item"><i class="legend-dot purple"></i>Alerts · right</span></div></div><div class="chart-area"><svg class="trend-svg" viewBox="0 0 ${w} ${h}" role="img" aria-label="Event and alert volume over the selected time window"><defs><linearGradient id="event-gradient" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#3979f3" stop-opacity=".28"/><stop offset="100%" stop-color="#3979f3" stop-opacity=".01"/></linearGradient></defs>${grids}<path d="${area}" fill="url(#event-gradient)"/><path d="${line('events')}" fill="none" stroke="#538dff" stroke-width="2.2" stroke-linejoin="round"/><path d="${line('alerts')}" fill="none" stroke="#ad8afb" stroke-width="1.5" opacity=".7" stroke-linejoin="round"/>${xlabels}${points.map((p,i)=>{const [x,y]=xy(p,i,'events');return `<circle cx="${x}" cy="${y}" r="7" fill="transparent"><title>${E(C.date(p.timestamp))}: ${N(p.events)} events · ${p.alerts} alerts</title></circle>`;}).join('')}</svg></div><div class="chart-bottom"><span>${icon('clock').replace('class="icon ','style="display:inline;width:10px;height:10px;vertical-align:-2px;margin-right:4px" class="icon ')}Time shown in Asia/Bangkok (UTC+7)</span><span>Peak volume <strong>${N(max)} / bucket</strong></span></div></div>`;
  }
  function donut(){const s=C.stats(state.data,state.range,referenceTime()),r=59,c=2*Math.PI*r;let offset=0;const segments=s.severity.filter(i=>i.count).map(i=>{const len=s.alerts?i.count/s.alerts*c:0,html=`<circle cx="75" cy="75" r="${r}" fill="none" stroke="${i.color}" stroke-width="11" stroke-dasharray="${Math.max(0,len-4)} ${c-Math.max(0,len-4)}" stroke-dashoffset="${-offset}" stroke-linecap="round"/>`;offset+=len;return html;}).join('');return `<div class="panel chart-panel"><div class="panel-header"><div><h2>Alert severity</h2><p class="panel-subtitle">Unresolved detections in this window</p></div>${icon('shield')}</div><div class="donut-content"><div class="donut"><svg viewBox="0 0 150 150" role="img" aria-label="${s.severity.map(i=>i.name+': '+i.count).join(', ')}"><circle cx="75" cy="75" r="59" fill="none" stroke="#1c293d" stroke-width="11"/>${segments}</svg><div class="donut-center"><strong>${s.alerts}</strong><span>ACTIVE ALERTS</span></div></div><div class="severity-legend">${s.severity.filter(i=>i.name!=='info'||i.count).map(i=>`<button data-action="severity" data-severity="${i.name}"><span class="legend-dot" style="background:${i.color}"></span>${E(i.name[0].toUpperCase()+i.name.slice(1))}<strong>${i.count}</strong></button>`).join('')}</div></div><div class="chart-bottom"><span>${s.critical?`${s.critical} critical detections require review`:'No critical detections in this window'}</span><button class="link-button" data-action="navigate" data-page="alerts">View queue ${icon('arrow')}</button></div></div>`;}
  function alertRows(overview=false){return C.filterAlerts(state.data,{...state.alertFilter,range:state.range},referenceTime());}
  function alertToolbar(){return `<div class="table-toolbar"><div class="table-search">${icon('search')}<input id="alert-search" value="${E(state.alertFilter.query)}" placeholder="Search detections…" aria-label="Search detections"></div><select class="select" id="severity-filter" aria-label="Filter alerts by severity"><option value="all">All severities</option>${C.SEVERITIES.map(s=>`<option value="${s}" ${state.alertFilter.severity===s?'selected':''}>${s[0].toUpperCase()+s.slice(1)}</option>`).join('')}</select><select class="select" id="status-filter" aria-label="Filter alerts by status">${[['active','Unresolved'],['all','All statuses'],['new','New'],['acknowledged','Acknowledged'],['resolved','Resolved']].map(([v,t])=>`<option value="${v}" ${state.alertFilter.status===v?'selected':''}>${t}</option>`).join('')}</select>${state.page==='alerts'?`<select class="select" id="alert-sort" aria-label="Sort alerts"><option value="newest" ${state.alertFilter.sort==='newest'?'selected':''}>Newest first</option><option value="severity" ${state.alertFilter.sort==='severity'?'selected':''}>Severity first</option></select>`:''}</div>${['source','host','technique'].filter(k=>state.alertFilter[k]).length?`<div class="bulk-bar"><span>${['source','host','technique'].filter(k=>state.alertFilter[k]).map(k=>`${E(k)}: <strong>${E(state.alertFilter[k])}</strong>`).join(' · ')}</span><button class="link-button" data-action="clear-filters">Clear filters</button></div>`:''}`;}
  function tag(text,type=text){return `<span class="tag ${E(type)}">${E(text)}</span>`;}
  function pagination(page,total,size,type){const max=Math.max(1,Math.ceil(total/size));return `<div class="pagination"><button class="button quiet" data-action="paginate" data-type="${type}" data-page-number="${page-1}" ${page<=1?'disabled':''}>Previous</button><span><span class="page-count">${page}</span>/ ${max}</span><button class="button quiet" data-action="paginate" data-type="${type}" data-page-number="${page+1}" ${page>=max?'disabled':''}>Next</button></div>`;}
  function alertTable(overview=false){const all=alertRows(),size=overview?5:12,page=overview?1:Math.min(state.alertPage,Math.max(1,Math.ceil(all.length/size))),rows=all.slice((page-1)*size,page*size);state.alertPage=page;return `${alertToolbar()}${state.selected.size&&!overview?`<div class="bulk-bar"><span>${state.selected.size} alert${state.selected.size===1?'':'s'} selected</span><button class="button quiet" data-action="bulk-status" data-status="acknowledged">Acknowledge</button><button class="button quiet" data-action="bulk-status" data-status="resolved">Resolve</button><button class="link-button" data-action="clear-selection">Clear</button></div>`:''}<div class="table-wrapper"><table class="${overview?'overview-table':''}"><thead><tr>${!overview?`<th class="checkbox-cell"><input type="checkbox" id="select-page" aria-label="Select alerts on this page" ${rows.length&&rows.every(a=>state.selected.has(a.id))?'checked':''}></th>`:''}<th>SEVERITY</th><th>DETECTION</th><th class="entity-heading">ENDPOINT</th><th class="source-heading">SOURCE</th><th>STATUS</th><th>LAST SEEN</th><th><span class="sr-only">Details</span></th></tr></thead><tbody>${rows.map(a=>`<tr class="clickable" data-action="alert-detail" data-id="${E(a.id)}">${!overview?`<td class="checkbox-cell"><input type="checkbox" data-select-alert="${E(a.id)}" aria-label="Select ${E(a.id)}" ${state.selected.has(a.id)?'checked':''}></td>`:''}<td>${tag(a.severity)}</td><td><div class="alert-title">${E(a.title)}</div><span class="cell-secondary mono">${E(a.id)} ${a.technique?'· '+E(a.technique):''}</span></td><td class="entity-cell"><span class="mono">${E(a.host)}</span><span class="cell-secondary mono">${E(a.ip)}</span></td><td class="source-cell">${tag(a.source,'source')}</td><td><span class="status-text ${E(a.status)}"><span class="status-dot"></span>${a.status==='acknowledged'?'In review':E(a.status[0].toUpperCase()+a.status.slice(1))}</span></td><td><span class="small-label" title="${E(C.date(a.last_seen))}">${E(C.relative(a.last_seen))}</span></td><td><button class="icon-button" data-action="alert-detail" data-id="${E(a.id)}" aria-label="Investigate ${E(a.id)}">${icon('right','row-arrow')}</button></td></tr>`).join('')||`<tr><td colspan="8">${empty('No matching alerts','Adjust the filters or select a wider time window.','clear-filters','Reset filters')}</td></tr>`}</tbody></table></div><div class="table-footer"><span>${all.length?`Showing ${(page-1)*size+1}–${Math.min(page*size,all.length)} of ${N(all.length)} detections`:'0 detections match these filters'}</span>${overview?`<button class="link-button" data-action="navigate" data-page="alerts">Open detection queue ${icon('arrow')}</button>`:pagination(page,all.length,size,'alert')}</div>`;}
  function empty(title,subtitle,action,label){return `<div class="empty-state">${icon('search')}<h3>${E(title)}</h3><p>${E(subtitle)}</p>${action?`<button class="button quiet" data-action="${action}">${E(label)}</button>`:''}</div>`;}
  function coveragePanel(){const rows=C.coverage(C.stats(state.data,state.range,referenceTime()).activeRows),max=Math.max(1,...rows.map(r=>r.count));return `<div class="panel"><div class="panel-header"><div><h2>Top ATT&CK techniques</h2><p class="panel-subtitle">Observed in active detections</p></div>${icon('coverage')}</div><div class="coverage-list">${rows.slice(0,5).map(t=>`<div class="technique"><div class="technique-top"><button data-action="technique" data-technique="${E(t.id)}"><span class="technique-code">${E(t.id)}</span>${E(t.name)}</button><span class="technique-count">${t.count}</span></div><div class="bar-track"><div class="bar-fill" style="width:${t.count/max*100}%"></div></div></div>`).join('')||empty('No mapped techniques','Mapped detections will appear here.')}</div><div class="coverage-footer"><span>${rows.length} techniques observed</span><button class="link-button" data-action="navigate" data-page="coverage">Explore ${icon('arrow')}</button></div></div>`;}
  const sourceIcon=s=>({endpoint:'shield',windows:'windows',identity:'identity',network:'network',cloud:'cloud'}[s.kind]||'shield');
  function sourceStrip(){return `<div class="panel sources-panel"><div class="panel-header"><div class="panel-title-line"><h2>Data source health</h2><span class="count-badge">${state.data.sources.length}</span></div><button class="link-button" data-action="navigate" data-page="integrations">Manage sources ${icon('arrow')}</button></div><div class="sources-row">${state.data.sources.map(s=>`<a class="source-mini" href="#integrations"><span class="source-symbol">${icon(sourceIcon(s))}</span><div><strong>${E(s.name)}</strong><small><i class="status-dot ${s.status==='healthy'?'green':s.status==='offline'?'red':'amber'}"></i>${s.status==='healthy'?C.relative(s.last_seen):s.status==='offline'?'No recent events':'Degraded'}</small></div></a>`).join('')||'<div class="panel-body notes-text">No source health data received.</div>'}</div></div>`;}
  function overview(){return pageHeading('Security overview',`A unified view of your environment.<span class="update-divider">|</span>Updated ${E(C.relative(state.data.generated_at))}`)+metrics()+`<div class="chart-grid">${trend()}${donut()}</div><div class="alert-grid"><div class="panel"><div class="panel-header"><div class="panel-title-line"><h2>Detection queue</h2><span class="count-badge">${alertRows().length}</span></div><button class="link-button" data-action="navigate" data-page="alerts">View all ${icon('arrow')}</button></div><div id="alert-table">${alertTable(true)}</div></div>${coveragePanel()}</div>`+sourceStrip();}
  function alertsPage(){return pageHeading('Threat detection','Prioritize, investigate, and track every detection.',`<button class="button" data-action="export-alerts">${icon('export')}Export CSV</button><button class="button" data-action="refresh" ${state.busy?'disabled':''}>${icon('refresh')}Refresh</button>`)+`<div class="panel"><div class="panel-header"><div><h2>Detection queue</h2><p class="panel-subtitle">Select an alert to review evidence and start an investigation.</p></div><span class="result-count">${N(alertRows().length)} RESULTS</span></div><div id="alert-table">${alertTable()}</div></div>`;}
  function endpointRows(){return state.data.endpoints.filter(e=>(state.endpointFilter.status==='all'||e.status===state.endpointFilter.status)&&C.matchesQuery(e,state.endpointFilter.query)).sort((a,b)=>b.risk-a.risk);}
  function endpointsPage(){const all=endpointRows(),size=12,page=Math.min(state.endpointPage,Math.max(1,Math.ceil(all.length/size)));state.endpointPage=page;const rows=all.slice((page-1)*size,page*size),online=state.data.endpoints.filter(e=>e.status==='online').length;return pageHeading('Endpoint inventory','Host visibility, agent health, and risk across your environment.',`<button class="button" data-action="export-endpoints">${icon('export')}Export CSV</button>`)+`<div class="panel"><div class="panel-header"><div><h2>Observed endpoints</h2><p class="panel-subtitle">${online} online · ${state.data.endpoints.filter(e=>e.status==='offline').length} offline · ${state.data.endpoints.filter(e=>e.status==='unknown').length} unknown · sampled Wazuh alerts</p></div><span class="result-count">${all.length} HOSTS</span></div><div class="table-toolbar"><div class="table-search">${icon('search')}<input id="endpoint-search" value="${E(state.endpointFilter.query)}" placeholder="Search hostname, IP, or user…" aria-label="Search endpoints"></div><select class="select" id="endpoint-status" aria-label="Endpoint status">${['all','online','offline','unknown'].map(s=>`<option value="${s}" ${state.endpointFilter.status===s?'selected':''}>${s==='all'?'All statuses':s[0].toUpperCase()+s.slice(1)}</option>`).join('')}</select></div><div class="table-wrapper"><table><thead><tr><th>ENDPOINT</th><th>IP ADDRESS</th><th>OPERATING SYSTEM</th><th>STATUS</th><th>RISK SCORE</th><th>LAST SEEN</th><th></th></tr></thead><tbody>${rows.map(e=>`<tr class="clickable" data-action="endpoint-detail" data-id="${E(e.id)}"><td><div class="endpoint-summary"><span class="os-icon">${icon((e.os||'').includes('Windows')?'windows':'logs')}</span><div><strong class="mono">${E(e.host)}</strong><span class="cell-secondary">${E(e.department)} · ${E(e.user)}</span></div></div></td><td class="mono">${E(e.ip)}</td><td>${E(e.os)}</td><td>${tag(e.status)}</td><td>${Number.isFinite(e.risk)?`<div class="risk-score"><strong style="color:${e.risk>=70?'var(--red)':e.risk>=40?'var(--orange)':'var(--green)'}">${e.risk}</strong><div class="bar-track"><div class="bar-fill" style="width:${e.risk}%;background:${e.risk>=70?'var(--red)':e.risk>=40?'var(--orange)':'var(--green)'}"></div></div></div>`:'N/A'}</td><td class="small-label">${e.last_seen?E(C.relative(e.last_seen)):'Unknown'}</td><td>${icon('right','row-arrow')}</td></tr>`).join('')||`<tr><td colspan="7">${empty('No endpoints found','Adjust your search or status filter.')}</td></tr>`}</tbody></table></div><div class="table-footer"><span>Showing ${all.length?(page-1)*size+1:0}–${Math.min(page*size,all.length)} of ${all.length} endpoints</span>${pagination(page,all.length,size,'endpoint')}</div></div>`;}
  function casesPage(){return pageHeading('Investigations','Organize evidence and follow each case through to resolution.',`<button class="button primary" data-action="new-case">${icon('plus')}New case</button>`)+`<div class="grid-three case-board">${[['open','Open'],['investigating','In progress'],['closed','Closed']].map(([status,name])=>{const rows=state.data.cases.filter(c=>c.status===status).sort((a,b)=>C.timestamp(b.created_at)-C.timestamp(a.created_at));return `<section class="case-column"><div class="case-column-heading"><span>${name}</span><span class="count-badge">${rows.length}</span></div><div class="case-list">${rows.map(c=>`<article class="panel case-card" data-action="case-detail" data-id="${E(c.id)}" tabindex="0" role="button" aria-label="Open ${E(c.title)}"><div class="case-meta"><span class="case-id">${E(c.id)}</span>${tag(c.severity)}</div><h3>${E(c.title)}</h3><p>${c.alert_ids.length} linked detection${c.alert_ids.length===1?'':'s'} · ${E(C.relative(c.created_at))}</p><div class="case-card-footer"><span class="assignee"><span class="avatar mini">${E(c.owner.split(' ').map(w=>w[0]).join('').slice(0,2))}</span>${E(c.owner)}</span><span>${c.comments.length} notes</span></div></article>`).join('')||`<div class="panel">${empty('No '+name.toLowerCase()+' cases','Cases will appear here as you investigate alerts.')}</div>`}</div></section>`;}).join('')}</div>`;}
  function logRows(){return C.filterEvents(state.data,{...state.logFilter,range:state.range},referenceTime());}
  function logsPage(){const all=logRows(),size=15,page=Math.min(state.eventPage,Math.max(1,Math.ceil(all.length/size)));state.eventPage=page;const rows=all.slice((page-1)*size,page*size);return pageHeading('Log explorer','Search recent telemetry and inspect the original event payload.',`<button class="button" data-action="export-events">${icon('export')}Export CSV</button>`)+`<div class="panel"><div class="panel-header"><div><h2>Event search</h2><p class="panel-subtitle">${N(state.data.events.length)} events loaded${state.data.meta?.events_sampled?' · recent sample of the indexed event stream':''}</p></div><span class="result-count">${N(all.length)} MATCHES</span></div><div class="table-toolbar"><div class="log-query">${icon('logs')}<input id="log-query" value="${E(state.logFilter.query)}" placeholder="host:WIN-FIN severity:high" aria-label="Event search query"></div><select id="log-source" class="select" aria-label="Filter events by source"><option value="">All sources</option>${[...new Set(state.data.events.map(e=>e.source))].sort().map(s=>`<option value="${E(s)}" ${state.logFilter.source===s?'selected':''}>${E(s)}</option>`).join('')}</select><button class="button primary" data-action="run-query">${icon('search')}Search</button></div><p class="log-hint">Try <code>host:WIN-FIN</code> <code>source:Sysmon</code> <code>event:process_start</code> or <code>-severity:info</code>. Terms are combined with AND.</p><div class="table-wrapper"><table><thead><tr><th>TIME (ICT)</th><th>SOURCE</th><th>HOST</th><th>EVENT TYPE</th><th>MESSAGE</th><th></th></tr></thead><tbody>${rows.map(e=>`<tr class="clickable" data-action="event-detail" data-id="${E(e.id)}"><td class="mono" style="white-space:nowrap">${E(new Date(e.timestamp).toLocaleTimeString('en-GB',{timeZone:'Asia/Bangkok'}))}<span class="cell-secondary">${E(C.relative(e.timestamp))}</span></td><td>${tag(e.source,'source')}</td><td class="mono">${E(e.host)}</td><td><span class="mono">${E(e.event_type)}</span><span class="cell-secondary">${E(e.severity)}</span></td><td><span class="alert-title">${E(e.message.slice(0,100))}</span></td><td>${icon('right','row-arrow')}</td></tr>`).join('')||`<tr><td colspan="6">${empty('No events match this query','Adjust the query, source, or time window.','clear-log-query','Clear query')}</td></tr>`}</tbody></table></div><div class="table-footer"><span>Showing ${all.length?(page-1)*size+1:0}–${Math.min(page*size,all.length)} of ${N(all.length)} matching events</span>${pagination(page,all.length,size,'event')}</div></div>`;}
  function coveragePage(){const rows=C.coverage(C.stats(state.data,state.range,referenceTime()).alertRows),tactics=[...new Set(rows.map(t=>t.tactic))];return pageHeading('ATT&CK activity','Techniques observed in your detections, grouped by tactic.')+`<div class="notice section-gap">${icon('info')}<span>This view shows observed detection activity. It does not measure prevention effectiveness or full ATT&CK coverage.</span></div>${tactics.map(t=>`<section class="panel section-gap"><div class="panel-header"><div><h2>${E(t)}</h2><p class="panel-subtitle">${rows.filter(r=>r.tactic===t).reduce((n,r)=>n+r.count,0)} detections mapped to this tactic</p></div>${icon('coverage')}</div><div class="panel-body coverage-tiles">${rows.filter(r=>r.tactic===t).map(r=>`<button class="coverage-tile" data-action="technique" data-technique="${E(r.id)}"><small>${E(r.id)}</small><strong>${E(r.name)}</strong><span>${r.count} detections ${icon('arrow').replace('class="icon ','style="display:inline;width:12px;height:12px;vertical-align:-2px;margin-left:4px" class="icon ')}</span></button>`).join('')}</div></section>`).join('')||empty('No mapped activity','Detections with MITRE technique IDs will appear here.')}`;}
  function integrationForm(){return `<form id="api-form"><div class="form-field"><label for="api-base">Dashboard API base URL</label><input id="api-base" name="api-base" value="${E(state.apiBase)}" placeholder="https://your-api.example.com/api/v1" required><p class="form-help">Use an HTTPS API for this hosted dashboard, or run the included Docker package locally.</p></div><div class="form-field"><label for="api-token">Bearer token <span class="small-label">· optional</span></label><input type="password" id="api-token" autocomplete="off" placeholder="Kept in memory for this session only" value="${E(state.token)}"><p class="form-help">Point to your dashboard adapter. Configure OpenSearch credentials on the server.</p></div><div class="form-actions"><button type="submit" class="button primary" ${state.busy?'disabled':''}>${icon('link')}Test & connect</button><button type="button" class="button quiet" data-action="demo-mode">Use demo data</button></div></form><p class="connection-status">${state.mode==='api'&&state.connected?`<span class="status-signal">${state.data.meta?.demo?'Connected to a demo API':'API connected'}</span> · ${E(C.date(state.lastFetch))}`:'Connect to load a real snapshot from your EDR/XDR pipeline.'}</p>`;}
  function integrationsPage(){return pageHeading('Data sources','Connect your telemetry pipeline and monitor ingestion health.',`<button class="button" data-action="import">${icon('upload')}Import JSON</button>`)+`<div class="grid-three section-gap">${state.data.sources.map(s=>`<article class="panel connection-card"><div class="connection-card-top"><span class="source-symbol">${icon(sourceIcon(s))}</span>${tag(s.status)}</div><div><h3>${E(s.name)}</h3><p>${E(s.description)}</p></div><div class="connection-detail"><span>Events in snapshot window</span><strong>${N(s.events)}</strong></div><div class="connection-detail"><span>Last event</span><strong>${E(C.relative(s.last_seen))}</strong></div><button class="button quiet" data-action="source-events" data-source="${E(s.name)}">${icon('logs')}Explore events</button></article>`).join('')||`<div class="panel">${empty('No source health data','Connect an API or import a snapshot with sources.')}</div>`}</div><div class="grid-two"><section class="panel"><div class="panel-header"><div><h2>Connect your EDR / XDR backend</h2><p class="panel-subtitle">One normalized API for alerts, hosts, and telemetry.</p></div>${icon('integrations')}</div><div class="panel-body">${integrationForm()}</div></section><section class="panel"><div class="panel-header"><div><h2>Bring your own pipeline</h2><p class="panel-subtitle">An integration package is included with the source code.</p></div>${icon('code')}</div><div class="panel-body"><div class="health-list"><div class="health-row"><span class="source-symbol">${icon('activity')}</span><div><strong>OpenSearch / Elasticsearch</strong><small>Server adapter maps indexed events to the dashboard schema.</small></div></div><div class="health-row"><span class="source-symbol">${icon('shield')}</span><div><strong>Custom EDR / XDR API</strong><small>Implement GET /snapshot using the documented JSON contract.</small></div></div><div class="health-row"><span class="source-symbol">${icon('upload')}</span><div><strong>Offline JSON snapshot</strong><small>Import telemetry for reviews, lab demos, and presentations.</small></div></div></div><div class="api-schema"><p class="form-help">API contract</p><pre class="code-block">GET /api/v1/snapshot?hours=24
{
  "schema_version": 1,
  "generated_at": "2026-10-14T13:00:00Z",
  "alerts": [], "endpoints": [], "events": [],
  "cases": [], "sources": [],
  "summary": {"events_total": 0, "series": []}
}</pre></div><div class="form-actions" style="margin-top:15px"><button class="button quiet" data-action="download-snapshot">${icon('export')}Export snapshot</button><button class="button quiet" data-action="guide">${icon('help')}Setup guide</button></div></div></section></div>`;}
  function settingsPage(){return pageHeading('Workspace settings','Configure the data connection and dashboard preferences.',`<button class="button quiet" data-action="guide">${icon('help')}Setup guide</button>`)+`<div class="grid-two"><section class="panel"><div class="panel-header"><h2>Data connection</h2>${icon('integrations')}</div><div class="panel-body">${integrationForm()}</div></section><section class="panel"><div class="panel-header"><h2>Preferences</h2>${icon('settings')}</div><div class="panel-body settings-section"><div class="form-field"><label for="auto-refresh">API refresh interval</label><select id="auto-refresh">${[[0,'Manual refresh'],[30,'Every 30 seconds'],[60,'Every 60 seconds'],[120,'Every 2 minutes']].map(([v,t])=>`<option value="${v}" ${state.refreshSeconds===v?'selected':''}>${t}</option>`).join('')}</select><div class="form-help">Auto refresh runs while this tab is visible and connected to an API.</div></div><div class="key-value"><span>Display timezone</span><strong>Asia/Bangkok · UTC+7</strong></div><div class="key-value"><span>Dashboard mode</span><strong>${state.mode==='api'?'API connection':state.mode==='import'?'Imported snapshot':'Synthetic demo'}</strong></div><div class="key-value"><span>Snapshot window</span><strong>${state.data.window_hours} hours</strong></div><div class="key-value"><span>Workflow changes</span><strong>${state.mode==='api'?'Stored by the API':state.mode==='demo'?'Stored in this browser':'This session only'}</strong></div><div class="danger-zone"><h3>Demo workspace</h3><p>Reset sample alerts and cases to their initial state.</p><button class="button quiet" data-action="reset-demo">${icon('refresh')}Reset demo</button></div></div></section><section class="panel"><div class="panel-header"><h2>Export & import</h2>${icon('export')}</div><div class="panel-body settings-section"><p>Move a normalized telemetry snapshot between environments. Exports include the current alerts, endpoints, events, and case notes.</p><div class="form-actions"><button class="button" data-action="download-snapshot">${icon('export')}Export JSON snapshot</button><button class="button" data-action="import">${icon('upload')}Import snapshot</button></div></div></section><section class="panel"><div class="panel-header"><h2>Keyboard shortcuts</h2>${icon('code')}</div><div class="panel-body"><div class="key-value"><span>Global alert search</span><strong><kbd>Ctrl / ⌘ K</kbd></strong></div><div class="key-value"><span>Close details</span><strong><kbd>Esc</kbd></strong></div><div class="key-value"><span>Setup guide</span><strong><kbd>?</kbd></strong></div></div></section></div>`;}


  async function loadResearchQuality(){
    const status=$('research-quality-status');
    const body=$('research-quality-data');
    if(!status||!body)return;

    const pct=v=>typeof v==='number'&&Number.isFinite(v)&&v>=0&&v<=1
      ?(v*100).toFixed(2)+'%':'—';
    const num=v=>Number.isSafeInteger(v)&&v>=0?String(v):'—';
    const flag=v=>v===true?'YES':v===false?'NO':'UNKNOWN';
    const row=(name,value)=>`<div class="key-value">
      <span>${E(name)}</span><strong>${E(String(value))}</strong>
    </div>`;

    try{
      const response=await fetch('/api/model-quality',{
        cache:'no-store',
        signal:AbortSignal.timeout(15000)
      });
      if(!response.ok)throw new Error('HTTP '+response.status);

      const data=await response.json();
      const q=data?.quality;
      const p=data?.parity;
      const m=q?.overall;

      if(!m||!p||typeof q.production_ready!=='boolean')
        throw new Error('Invalid report');

      if(!status.isConnected)return;

      status.textContent='Historical offline report · Run: '+
        String(data.run_id||'Unknown');

      body.innerHTML=[
        row('Evaluated samples',num(m.n)),
        row('Precision',pct(m.precision)),
        row('Recall',pct(m.recall)),
        row('F1 Score',pct(m.f1)),
        row('False Positive Rate',pct(m.false_positive_rate)),
        row('Development numeric gate',flag(q.development_numeric_gate_pass)),
        row('Shadow authorized',flag(q.shadow_authorized)),
        row('Parity status',p.status||'Unknown'),
        row('Raw-event verification',p.raw_event_check?.status||'Unknown'),
        row('Production ready',flag(q.production_ready))
      ].join('');

    }catch(e){
      if(!status.isConnected)return;
      status.textContent='Model Quality unavailable';
      body.textContent='Cannot load or validate offline report.';
    }
  }


  async function loadResearchSources(){
    const shadow=$('research-shadow-status');
    const blue=$('research-bluefield-status');
    if(!shadow||!blue)return;

    async function read(path){
      try{
        const response=await fetch(path,{
          cache:'no-store',
          signal:AbortSignal.timeout(12000)
        });

        return {
          http:response.status,
          data:response.ok ? await response.json() : null
        };
      }catch{
        return {http:0,data:null};
      }
    }

    const [s,b,h]=await Promise.all([
      read('/api/shadow/events'),
      read('/api/shadow/bluefield'),
      read('/api/bluefield/history')
    ]);

    if(!shadow.isConnected||!blue.isConnected)return;

    const http=r=>r.http?`HTTP ${r.http}`:'Request unavailable';
    const validCount=v=>Number.isSafeInteger(v)&&v>=0;

    const c=s.data?.counts;

    if(s.http===200 && s.data?.mode==='shadow'
        && c && validCount(c.severity)
        && validCount(c.behavioral)
        && validCount(c.matched)){
      shadow.textContent=
        `Historical Severity: ${c.severity} | `+
        `Behavioral: ${c.behavioral} | `+
        `Shadow matched: ${c.matched}`;
    }else{
      shadow.textContent=
        s.http===200
          ? 'Shadow schema needs verification'
          : `Shadow unavailable (${http(s)})`;
    }

    const bc=b.data?.counts;

    const blueShadow=
      b.http===200 &&
      b.data?.mode==='shadow_bluefield' &&
      b.data?.historical===true &&
      b.data?.live===false &&
      b.data?.production_ready===false &&
      b.data?.automated_response_allowed===false &&
      validCount(bc?.records)
        ? `Historical records: ${bc.records}`
        : b.http===200
          ? 'Schema needs verification'
          : `Unavailable (${http(b)})`;

    const hc=h.data?.counts;

    const historicalValid=
      h.http===200 &&
      h.data?.mode==='historical_review' &&
      h.data?.live===false &&
      h.data?.production_ready===false &&
      h.data?.source_index==='review-bluefield-20261012t141653z-6396a0d3' &&
      hc &&
      validCount(hc.records) &&
      validCount(hc.interfaces) &&
      validCount(hc.carrier_unknown) &&
      validCount(hc.first_sample) &&
      validCount(hc.computed) &&
      Array.isArray(h.data.records) &&
      h.data.records.length===hc.records &&
      hc.first_sample+hc.computed===hc.records;

    const blueArchive=historicalValid
      ? `Historical records: ${hc.records} | Interfaces: ${hc.interfaces} | `+
        `Carrier unknown: ${hc.carrier_unknown} | `+
        `First sample: ${hc.first_sample} | Computed: ${hc.computed}`
      : h.http===200
        ? 'Schema or consistency verification failed'
        : `Unavailable (${http(h)})`;

    blue.textContent=
      `BlueField Shadow: ${blueShadow} | `+
      `Historical Archive: ${blueArchive}`;
  }

  function researchPage(){setTimeout(loadResearchQuality,0);setTimeout(loadResearchSources,0);
    return pageHeading(
      'Research & Experiments',
      'Historical research evidence, kept separate from live SOC monitoring.'
    ) + `
      <div class="notice warn section-gap">
        ${icon('info')}
        <div>
          Research and archived evidence only.
          Not live detection. Production automation remains disabled.
        </div>
      </div>
      <div class="grid-two">
        <section class="panel">
          <div class="panel-header"><h2>AI Model Experiments</h2></div>
          <div class="panel-body">
            <p>Review recorded model experiments and bounded demo runs.</p>
            <div class="notice warn section-gap">
              Offline evaluation only. Not live inference.
              No automated response is enabled here.
            </div>
            <p id="research-quality-status" aria-live="polite">
              Loading verified report...
            </p>
            <div id="research-quality-data" class="settings-section"></div>

            <a class="link-button" href="#modeldetails">View Model Quality details →</a>
          </div>
        </section>
        <section class="panel">
          <div class="panel-header"><h2>Shadow Analysis</h2></div>
          <div class="panel-body">
            <p>Review historical severity and behavioral evidence.</p><p id="research-shadow-status" class="form-help" aria-live="polite">Checking Shadow API...</p>
            <a class="link-button" href="#shadowdetails">View Shadow details →</a>
          </div>
        </section>
        <section class="panel">
          <div class="panel-header"><h2>BlueField Historical Review</h2></div>
          <div class="panel-body">
            <p>Archived telemetry only. BlueField live service remains disabled.</p><p id="research-bluefield-status" class="form-help" aria-live="polite">Checking historical APIs...</p>
            <a class="link-button" href="#bluefielddetails">View BlueField details →</a>
          </div>
        </section>
        <section class="panel">
          <div class="panel-header"><h2>Research Evidence</h2></div>
          <div class="panel-body">
            <p>Review previously recorded and verified research results.</p>
            <a class="link-button" href="#researchevidence">View Research evidence →</a>
          </div>
        </section>
      </div>
    `;
  }


  function shadowDetailsPage(){
    setTimeout(loadShadowDetails,0);

    return pageHeading(
      'Shadow Details',
      'Historical severity and behavioral analysis. Not live monitoring.',
      '<a class="button quiet" href="#research">Back to Research</a>'
    ) + `
      <div class="notice warn section-gap">
        ${icon('info')}
        <div>
          Offline research evidence only.
          False-positive candidates are not confirmed false positives.
          Automated response remains disabled.
        </div>
      </div>

      <section class="panel">
        <div class="panel-header">
          <h2>Historical Shadow Events</h2>
        </div>
        <div class="panel-body">
          <p id="shadow-detail-status" aria-live="polite">
            Loading historical data...
          </p>
          <div id="shadow-detail-table"></div>
        </div>
      </section>
    `;
  }

  async function loadShadowDetails(){
    const status=$('shadow-detail-status');
    const target=$('shadow-detail-table');

    if(!status||!target)return;

    const safe=v=>E(
      v===null||v===undefined?'—':String(v)
    );

    try{
      const response=await fetch('/api/shadow/events',{
        cache:'no-store',
        signal:AbortSignal.timeout(15000)
      });

      if(!response.ok)
        throw new Error('Shadow API unavailable');

      const data=await response.json();

      if(
        data?.mode!=='shadow' ||
        !Array.isArray(data.events) ||
        data.events.length>200 ||
        !data.counts ||
        !Number.isSafeInteger(data.counts.matched)
      ){
        throw new Error('Invalid Shadow schema');
      }

      const flagsValid=data.events.every(r=>
        r && typeof r==='object' &&
        (!r.severity || (
          r.severity.production_ready===false &&
          r.severity.automated_response_allowed===false
        )) &&
        (!r.behavioral || (
          r.behavioral.production_ready===false &&
          r.behavioral.automated_response_allowed===false
        ))
      );

      if(!flagsValid)
        throw new Error('Historical safety validation failed');

      if(!status.isConnected||!target.isConnected)return;
      if(state.page!=='shadowdetails')return;

      const c=data.counts;

      status.textContent=
        `${data.events.length} historical rows | `+
        `Matched: ${c.matched} | `+
        `Conflicts: ${c.conflicts} | `+
        `Unmatched: ${c.unmatched}`;

      const cellStyle=
        'padding:10px 12px;'+
        'border-bottom:1px solid #29364a;'+
        'text-align:left;white-space:nowrap';

      const headers=[
        'UID prefix',
        'Rule ID',
        'Wazuh Level',
        'Severity Score',
        'Status',
        'FP Candidate',
        'AE Scored',
        'Novelty'
      ];

      const headerHtml=headers.map(h=>
        `<th style="${cellStyle}">${safe(h)}</th>`
      ).join('');

      const rows=data.events.map((r,i)=>{
        const sev=r.severity||{};
        const beh=r.behavioral||{};

        const uid=typeof sev.event_uid==='string' &&
          /^[a-f0-9]{64}$/i.test(sev.event_uid)
          ? sev.event_uid : '';

        const uidPrefix=uid?uid.slice(0,12)+'…':'—';

        const score=
          typeof sev.high_severity_score==='number' &&
          Number.isFinite(sev.high_severity_score)
            ? sev.high_severity_score.toFixed(4)
            : '—';

        const candidate=
          sev.false_positive_candidate===true
          ? 'Candidate (unverified)'
          : sev.false_positive_candidate===false
            ? 'No'
            : '—';

        const ae=
          beh.ae_scored===true?'Yes':
          beh.ae_scored===false?'No':'—';

        const novelty=
          beh.semantic_novelty===true?'Yes':
          beh.semantic_novelty===false?'No':'—';

        const values=[
          uidPrefix,
          sev.wazuh_rule_id,
          sev.wazuh_rule_level,
          score,
          r.status,
          candidate,
          ae,
          novelty
        ];

        return `<tr>${values.map(v=>
          `<td style="${cellStyle}">${safe(v)}</td>`
        ).join('')}</tr>`;
      }).join('');

      target.innerHTML=`
        <div style="overflow:auto;max-height:600px">
          <table style="width:100%;border-collapse:collapse;font-size:12px">
            <thead><tr>${headerHtml}</tr></thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
      `;

    }catch{
      if(!status.isConnected||!target.isConnected)return;
      if(state.page!=='shadowdetails')return;

      status.textContent=
        'Shadow data unavailable or failed validation.';
      target.textContent=
        'No unverified historical data has been displayed.';
    }
  }


  function bluefieldDetailsPage(){
    setTimeout(loadBluefieldDetails,0);

    return pageHeading(
      'BlueField Details',
      'Archived network telemetry. Not live monitoring.',
      '<a class="button quiet" href="#research">Back to Research</a>'
    ) + `
      <div class="notice warn section-gap">
        ${icon('info')}
        <div>
          Historical evidence only. BlueField Live and
          automated response remain disabled.
          Different indexes must not be summed as new events.
        </div>
      </div>

      <div class="grid-two">
        <section class="panel">
          <div class="panel-header"><h2>BlueField Shadow</h2></div>
          <div class="panel-body">
            <p id="bf-shadow-status" aria-live="polite">Loading...</p>
            <div id="bf-shadow-table"></div>
          </div>
        </section>
        <section class="panel">
          <div class="panel-header"><h2>BlueField Historical Archive</h2></div>
          <div class="panel-body">
            <p id="bf-history-status" aria-live="polite">Loading...</p>
            <div id="bf-history-table"></div>
          </div>
        </section>
      </div>
    `;
  }

  async function loadBluefieldDetails(){
    if(state.page!=='bluefielddetails')return;

    const validCount=v=>
      Number.isSafeInteger(v)&&v>=0&&v<=200;

    const safe=v=>{
      if(v===null||v===undefined)return '—';
      if(!['string','number','boolean'].includes(typeof v))
        return '—';
      return E(String(v));
    };

    const columns=[
      ['Interface','interface'],
      ['Timestamp','timestamp'],
      ['Operating State','operstate'],
      ['Carrier','carrier'],
      ['RX Bytes','rx_bytes'],
      ['TX Bytes','tx_bytes'],
      ['Delta RX','delta_rx_bytes'],
      ['Delta TX','delta_tx_bytes']
    ];

    async function read(path){
      const r=await fetch(path,{
        cache:'no-store',
        signal:AbortSignal.timeout(15000)
      });
      if(!r.ok)throw new Error('HTTP '+r.status);
      return r.json();
    }

    function display(result,statusId,tableId,kind){
      const status=$(statusId);
      const table=$(tableId);

      if(!status||!table||state.page!=='bluefielddetails')
        return;

      if(result.status!=='fulfilled'){
        status.textContent='Historical API unavailable';
        table.textContent='';
        return;
      }

      const d=result.value;
      const c=d?.counts;

      const common=
        d &&
        d.live===false &&
        d.production_ready===false &&
        c &&
        validCount(c.records) &&
        validCount(c.interfaces) &&
        Array.isArray(d.records) &&
        d.records.length===c.records &&
        d.records.every(r=>r&&typeof r==='object');

      const valid=kind==='shadow'
        ? common &&
          d.mode==='shadow_bluefield' &&
          d.historical===true &&
          d.automated_response_allowed===false &&
          d.source_index==='shadow-bluefield-v1' &&
          d.records.every(r=>
            r.historical===true &&
            r.production_ready===false &&
            r.automated_response_allowed===false
          )
        : common &&
          d.mode==='historical_review' &&
          d.source_index===
            'review-bluefield-20261012t141653z-6396a0d3' &&
          validCount(c.first_sample) &&
          validCount(c.computed) &&
          c.first_sample+c.computed===c.records;

      if(!valid){
        status.textContent='Historical schema validation failed';
        table.textContent='';
        return;
      }

      status.textContent=
        `${c.records} historical records | `+
        `${c.interfaces} interfaces | `+
        `Live: OFF | Production: NO`;

      const th=columns.map(([label])=>
        `<th style="padding:10px;text-align:left;white-space:nowrap">`+
        `${safe(label)}</th>`
      ).join('');

      const rows=d.records.map(r=>
        '<tr>'+columns.map(([,key])=>
          `<td style="padding:10px;border-top:1px solid #29364a;`+
          `white-space:nowrap">${safe(r[key])}</td>`
        ).join('')+'</tr>'
      ).join('');

      table.innerHTML=`
        <div style="overflow:auto;max-height:520px">
          <table style="width:100%;border-collapse:collapse;font-size:12px">
            <thead><tr>${th}</tr></thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
      `;
    }

    const [shadow,history]=await Promise.allSettled([
      read('/api/shadow/bluefield'),
      read('/api/bluefield/history')
    ]);

    display(shadow,'bf-shadow-status','bf-shadow-table','shadow');
    display(history,'bf-history-status','bf-history-table','history');
  }


  function researchExtrasPage(){
    const model=state.page==='modeldetails';
    const page=model?'modeldetails':'researchevidence';

    setTimeout(()=>loadResearchExtras(page),0);

    return pageHeading(
      model?'Model Quality Details':'Research Evidence',
      model
        ?'Historical offline evaluation and per-rule results.'
        :'Traceable historical evidence from independent research sources.',
      '<a class="button quiet" href="#research">Back to Research</a>'
    )+`
      <div class="notice warn section-gap">
        ${icon('info')}
        <div>
          Historical research only. Not live inference.
          Production readiness is not established.
          Automated response remains disabled.
        </div>
      </div>
      <section class="panel">
        <div class="panel-header">
          <h2>${model?'Model Evaluation':'Evidence Sources'}</h2>
        </div>
        <div class="panel-body">
          <p id="research-extra-status" aria-live="polite">Loading...</p>
          <div id="research-extra-body" class="settings-section"></div>
        </div>
      </section>
    `;
  }

  async function loadResearchExtras(page){
    const status=$('research-extra-status');
    const body=$('research-extra-body');
    if(!status||!body)return;

    const current=()=>
      state.page===page&&status.isConnected&&body.isConnected;

    const esc=v=>E(
      String(v===null||v===undefined?'—':v).slice(0,240)
    );

    const count=v=>
      Number.isSafeInteger(v)&&v>=0?v:'—';

    const percent=v=>
      typeof v==='number'&&Number.isFinite(v)&&v>=0&&v<=1
      ?(v*100).toFixed(2)+'%':'—';

    const flag=v=>v===true?'PASS':v===false?'FAIL':'UNKNOWN';

    const row=(label,value)=>
      `<div class="key-value">
        <span>${esc(label)}</span>
        <strong>${esc(value)}</strong>
      </div>`;

    const panel=(title,content)=>
      `<section class="panel">
        <div class="panel-header"><h2>${esc(title)}</h2></div>
        <div class="panel-body settings-section">${content}</div>
      </section>`;

    async function read(path){
      const response=await fetch(path,{
        cache:'no-store',
        signal:AbortSignal.timeout(15000)
      });
      if(!response.ok)throw Error('HTTP '+response.status);
      return response.json();
    }

    try{
      if(page==='modeldetails'){
        const d=await read('/api/model-quality');
        const q=d?.quality;
        const p=d?.parity;
        const m=q?.overall;

        if(
          !q||!p||!m||
          typeof d.run_id!=='string'||
          q.production_ready!==false||
          !Number.isSafeInteger(m.n)||
          m.n<0
        )throw Error('Model schema or safety validation failed');

        if(!current())return;

        const overall=[
          row('Evaluated samples',count(m.n)),
          row('Precision',percent(m.precision)),
          row('Recall',percent(m.recall)),
          row('F1 Score',percent(m.f1)),
          row('False Positive Rate',percent(m.false_positive_rate)),
          row('TP / FP',`${count(m.tp)} / ${count(m.fp)}`),
          row('TN / FN',`${count(m.tn)} / ${count(m.fn)}`)
        ].join('');

        const gates=Object.entries(q.proposed_gate_results||{})
          .filter(([key,value])=>
            typeof key==='string'&&typeof value==='boolean'
          )
          .slice(0,30)
          .map(([key,value])=>row(key,flag(value)))
          .join('');

        const rules=Object.entries(q.per_rule||{})
          .filter(([key,value])=>
            /^\d{1,8}$/.test(key)&&
            value&&typeof value==='object'&&!Array.isArray(value)
          )
          .slice(0,50);

        const ruleRows=rules.map(([id,r])=>`
          <tr>
            ${[
              id,
              count(r.n),
              percent(r.precision),
              percent(r.recall),
              percent(r.f1),
              percent(r.false_positive_rate)
            ].map(v=>`
              <td style="padding:10px;border-bottom:1px solid #29364a">
                ${esc(v)}
              </td>
            `).join('')}
          </tr>
        `).join('');

        const ruleTable=`
          <div style="overflow:auto">
            <table style="width:100%;border-collapse:collapse;font-size:12px">
              <thead>
                <tr>
                  ${['Rule ID','Samples','Precision','Recall','F1','FPR']
                    .map(v=>`<th style="padding:10px;text-align:left">
                      ${esc(v)}</th>`).join('')}
                </tr>
              </thead>
              <tbody>${ruleRows}</tbody>
            </table>
          </div>
          <p class="form-help">
            — means the metric is unavailable in this report.
            Per-rule metrics must not be inferred from overall metrics.
          </p>`;

        const limitations=Array.isArray(q.limitations)
          ?q.limitations.filter(v=>typeof v==='string').slice(0,20)
          :[];

        status.textContent=
          'Offline report | Run: '+d.run_id;

        body.innerHTML=
          `<div class="grid-two">
            ${panel('Overall Evaluation',overall)}
            ${panel('Development Gates',
              row('Numeric gate',flag(q.development_numeric_gate_pass))+
              row('Shadow authorized',flag(q.shadow_authorized))+
              row('Production ready',flag(q.production_ready))+
              gates
            )}
            ${panel('Per-rule Evaluation',
              ruleRows?ruleTable:'No per-rule metrics available')}
            ${panel('Parity & Limitations',
              row('Parity status',p.status)+
              row('Compared rows',count(p.compared_rows))+
              row('Raw-event check',p.raw_event_check?.status)+
              limitations.map(v=>`<p class="form-help">${esc(v)}</p>`).join('')
            )}
          </div>`;

      }else{
        const sources=[
          ['Model Quality','/api/model-quality'],
          ['Shadow Severity / Behavioral','/api/shadow/events'],
          ['BlueField Shadow','/api/shadow/bluefield'],
          ['BlueField Historical','/api/bluefield/history']
        ];

        const results=await Promise.allSettled(
          sources.map(([,url])=>read(url))
        );

        if(!current())return;

        let available=0;

        const cards=results.map((result,i)=>{
          const [name]=sources[i];

          if(result.status!=='fulfilled')
            return panel(name,row('Status','Unavailable'));

          const d=result.value;
          const c=d?.counts;
          let details='';

          if(i===0){
            if(
              d?.quality?.production_ready!==false||
              !Number.isSafeInteger(d?.quality?.overall?.n)
            )return panel(name,row('Status','Validation failed'));

            details=
              row('Run ID',d.run_id)+
              row('Samples',count(d.quality.overall.n))+
              row('Checked at',d.checked_at)+
              row('Production ready','NO');

            const hashes=d.source||{};
            for(const key of ['quality_sha256','parity_sha256']){
              const h=hashes[key];
              if(typeof h==='string'&&/^[a-f0-9]{64}$/i.test(h)){
                details+=row(key+' prefix',h.slice(0,16)+'…');
              }
            }

          }else if(i===1){
            const valid=
              d?.mode==='shadow'&&
              c&&
              Number.isSafeInteger(c.matched)&&c.matched>=0&&
              Array.isArray(d.events)&&d.events.length<=200&&
              d.events.every(r=>
                r&&typeof r==='object'&&
                (!r.severity||(
                  r.severity.production_ready===false&&
                  r.severity.automated_response_allowed===false
                ))&&
                (!r.behavioral||(
                  r.behavioral.production_ready===false&&
                  r.behavioral.automated_response_allowed===false
                ))
              );

            if(!valid)
              return panel(name,row('Status','Validation failed'));

            details=
              row('Severity documents',count(c.severity))+
              row('Behavioral documents',count(c.behavioral))+
              row('Shadow matched',count(c.matched))+
              row('Conflicts',count(c.conflicts))+
              row('Fetched at',d.fetched_at);

          }else if(i===2){
            const valid=
              d?.mode==='shadow_bluefield'&&
              d.historical===true&&
              d.live===false&&
              d.production_ready===false&&
              d.automated_response_allowed===false&&
              d.source_index==='shadow-bluefield-v1'&&
              Number.isSafeInteger(c?.records)&&c.records>=0&&
              Array.isArray(d.records)&&d.records.length===c.records;

            if(!valid)
              return panel(name,row('Status','Validation failed'));

            details=
              row('Index',d.source_index)+
              row('Historical records',count(c.records))+
              row('Interfaces',count(c.interfaces))+
              row('Live','OFF')+
              row('Fetched at',d.fetched_at);

          }else{
            const valid=
              d?.mode==='historical_review'&&
              d.live===false&&
              d.production_ready===false&&
              d.source_index===
                'review-bluefield-20261012t141653z-6396a0d3'&&
              Number.isSafeInteger(c?.records)&&c.records>=0&&
              Array.isArray(d.records)&&d.records.length===c.records;

            if(!valid)
              return panel(name,row('Status','Validation failed'));

            details=
              row('Index',d.source_index)+
              row('Historical records',count(c.records))+
              row('Interfaces',count(c.interfaces))+
              row('Live','OFF')+
              row('Fetched at',d.fetched_at);
          }

          available++;
          return panel(name,row('Status','Historical evidence available')+
            details);
        });

        status.textContent=
          `${available} of 4 historical evidence sources available. `+
          'Counts across different indexes must not be summed.';

        body.innerHTML=
          `<div class="grid-two">${cards.join('')}</div>`;
      }

    }catch{
      if(!current())return;
      status.textContent='Research report unavailable or invalid';
      body.textContent='No unverified results have been displayed.';
    }
  }



  function allEventsPage(){
    return pageHeading(
      'All Events',
      'Browse retained Wazuh events across the full history snapshot.'
    ) + `
      <div class="panel" id="history-view">
        <div class="panel-header">
          <div>
            <h2>Wazuh Event History</h2>
            <p class="panel-subtitle">
              Historical snapshot · Read-only · Not real-time
            </p>
          </div>
        </div>

        <div class="table-toolbar" style="display:flex;gap:12px;flex-wrap:wrap;padding:16px">
          <input
            id="history-search"
            aria-label="Search all historical events"
            placeholder="Search Rule ID, Agent, Description, event_uid"
            maxlength="128"
            style="flex:1;min-width:220px"
          >

          <select id="history-hours" aria-label="History time range">
            <option value="all">All Time</option>
            <option value="24">Last 24 Hours</option>
            <option value="168">Last 7 Days</option>
            <option value="720">Last 30 Days</option>
          </select>

          <button class="button" id="history-go">Search</button>
        </div>

        <div style="padding:12px 16px">
          <p id="history-summary" role="status">Loading history...</p>
          <p id="history-error" role="alert" style="color:#ff9999"></p>
        </div>

        <div class="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>TIME (ICT)</th>
                <th>RULE</th>
                <th>ENDPOINT</th>
                <th>DESCRIPTION</th>
                <th>AI SEVERITY</th>
                <th>EVENT UID</th>
              </tr>
            </thead>
            <tbody id="history-rows"></tbody>
          </table>
        </div>

        <div style="display:flex;justify-content:space-between;align-items:center;padding:18px;gap:12px">
          <button class="button" id="history-prev" disabled>Previous</button>
          <strong id="history-page">Page —</strong>
          <button class="button" id="history-next" disabled>Next</button>
        </div>
      </div>
    `;
  }

  /* COPILOT_INTEGRATED_PANEL_V1 */
  let copilotSelectedUid='';
  function copilotPage(){
    if(typeof window!=='undefined'&&window.NexusCopilotEvidence?.selected()){
      queueMicrotask(()=>{if(state.page==='copilot')window.NexusCopilotEvidence.mount();});
      return '<section class="panel" id="copilot-live-root" style="padding:24px;overflow-wrap:anywhere" aria-live="polite"></section>';
    }
    queueMicrotask(()=>{if(state.page==='copilot')mountCopilotPage();});
    return `<style>
      .copilot-page .copilot-layout{display:grid;grid-template-columns:minmax(240px,.8fr) minmax(0,2fr);gap:20px;align-items:start}
      .copilot-page .copilot-queue{display:grid;gap:8px;padding:12px}
      .copilot-page .copilot-pick{display:block;width:100%;text-align:left;white-space:normal;padding:14px;border-radius:8px}
      .copilot-page .copilot-pick[aria-pressed="true"]{outline:1px solid var(--blue,#4b8bff);background:rgba(64,132,255,.10)}
      .copilot-page .copilot-pick strong,.copilot-page .copilot-pick small{display:block}
      .copilot-page .copilot-body{padding:22px}.copilot-page .copilot-summary{font-size:17px;line-height:1.9;margin:18px 0}
      .copilot-page .copilot-uid{overflow-wrap:anywhere;font-size:12px;line-height:1.7}
      .copilot-page .copilot-scores{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:20px 0}
      .copilot-page .copilot-scores .metric-card{padding:16px}.copilot-page .copilot-score{font-size:26px;font-weight:650;margin:6px 0}
      .copilot-page .copilot-findings{display:grid;grid-template-columns:1fr 1fr;gap:20px}
      .copilot-page .copilot-findings h3{font-size:13px;margin:0 0 10px}.copilot-page .copilot-findings ul{padding-left:18px;line-height:1.9}
      .copilot-page .copilot-findings li{margin:0 0 12px}.copilot-page .copilot-citation{display:inline-block;font-size:11px;margin-top:5px;padding:2px 7px;border:1px solid var(--border,#2b3950);border-radius:5px}
      .copilot-page details{margin-top:20px}.copilot-page summary{cursor:pointer;font-size:13px}.copilot-page pre{white-space:pre-wrap;overflow-wrap:anywhere}
      @media(max-width:1000px){.copilot-page .copilot-layout{grid-template-columns:1fr}.copilot-page .copilot-queue{grid-template-columns:repeat(2,minmax(0,1fr))}}
      @media(max-width:600px){.copilot-page .copilot-findings,.copilot-page .copilot-queue{grid-template-columns:1fr}.copilot-page .copilot-body{padding:16px}}
    </style><div class="copilot-page" id="copilot-root">
      <div class="page-heading"><div><div class="eyebrow">SECURITY OPERATIONS <span>/</span> ANALYST ASSISTANCE</div>
        <h1>SOC Copilot</h1><p class="page-subtitle">สรุปเหตุการณ์จากหลักฐาน Exact UID · Local gpt-oss-20b</p></div>
        <div class="page-actions"><span class="mode-pill">SAVED REVIEW</span><button type="button" class="button" id="copilot-reload">โหลดผลสรุป</button></div></div>
      <div class="notice warn section-gap"><div><strong>ต้องให้ Analyst ตรวจ · Automated response OFF</strong>
        <p class="form-help">ผลสรุปที่บันทึกไว้ ไม่ใช่ข้อมูล realtime หน้านี้ไม่เรียก LLM/GPU และคะแนน AI ไม่ใช่เปอร์เซ็นต์โอกาสถูกโจมตี</p></div></div>
      <p id="copilot-status" class="form-help" role="status" aria-live="polite">กำลังตรวจสิทธิ์และโหลดผลสรุป…</p>
      <div class="copilot-layout"><aside class="panel"><div class="panel-header"><h2>เหตุการณ์ที่สรุปแล้ว</h2><span class="count-badge">8</span></div>
        <div id="copilot-queue" class="copilot-queue"></div></aside>
        <section class="panel" id="copilot-detail" aria-label="รายละเอียด Copilot"></section></div>
    </div>`;
  }
  function mountCopilotPage(){
    const root=document.getElementById('copilot-root');
    if(!root||root.dataset.bound)return;
    root.dataset.bound='1';
    const status=root.querySelector('#copilot-status'),queue=root.querySelector('#copilot-queue'),detail=root.querySelector('#copilot-detail'),reload=root.querySelector('#copilot-reload');
    let report=null,busy=false;
    const live=()=>state.page==='copilot'&&document.getElementById('copilot-root')===root;
    function node(tag,text,className){const n=document.createElement(tag);if(text!==undefined)n.textContent=String(text);if(className)n.className=className;return n;}
    function readable(text,uid){return String(text).replace(new RegExp('\\(\\s*event_uid\\s*:\\s*'+uid+'\\s*\\)','gi'),'').replaceAll(uid,'[หลักฐาน 1]').replace(/ +/g,' ').trim();}
    function show(){
      if(!live()||!report)return;
      queue.replaceChildren();detail.replaceChildren();
      const rows=report.results;
      if(!rows.some(r=>r.event_uid===copilotSelectedUid))copilotSelectedUid=rows[0].event_uid;
      rows.forEach((row,index)=>{
        const pick=node('button',undefined,'button quiet copilot-pick');pick.type='button';
        pick.setAttribute('aria-pressed',String(row.event_uid===copilotSelectedUid));
        pick.append(node('strong','เหตุการณ์ '+(index+1)+' · Rule '+row.evidence.rule_id),node('small',row.event_uid.slice(0,16)+'…','mono'),node('small','รอ Analyst ตรวจ','form-help'));
        pick.addEventListener('click',event=>{event.stopPropagation();copilotSelectedUid=row.event_uid;show();});queue.append(pick);
      });
      const row=rows.find(r=>r.event_uid===copilotSelectedUid),uid=row.event_uid,ev=row.evidence;
      const header=node('div',undefined,'panel-header');header.append(node('h2','เหตุการณ์ '+(rows.indexOf(row)+1)),node('span','รอตรวจ','tag'));detail.append(header);
      const body=node('div',undefined,'copilot-body');
      body.append(node('div',uid,'mono copilot-uid'),node('p',readable(row.draft.summary_th.text,uid),'copilot-summary'));
      const scores=node('div',undefined,'copilot-scores');
      for(const [label,value,foot] of [['Wazuh level',ev.wazuh_level+' / 15','ค่าจากเหตุการณ์ต้นทาง'],['Morpheus AI · '+ev.ai_status,typeof ev.ai_score==='number'?(ev.ai_score*100).toFixed(1)+' / 100':'—','ค่าดิบเดิม ไม่ใช่ความน่าจะเป็น']]){
        const card=node('div',undefined,'metric-card');card.append(node('div',label,'metric-label'),node('div',value,'copilot-score'),node('small',foot,'form-help'));scores.append(card);
      }body.append(scores);
      const findings=node('div',undefined,'copilot-findings');
      for(const [key,title] of [['facts','ข้อเท็จจริง'],['hypotheses','ข้อสันนิษฐาน'],['unknowns','สิ่งที่ยังไม่ทราบ'],['suggested_checks','ตรวจเพิ่มเติมโดย Analyst']]){
        const section=node('section');section.append(node('h3',title));
        if(!row.draft[key].length)section.append(node('p','โมเดลไม่ได้ระบุ — ต้องตรวจความครบถ้วนของหลักฐาน','form-help'));
        else{const ul=node('ul');row.draft[key].forEach(claim=>{const li=node('li');li.append(node('div',readable(claim.text,uid)));const cite=node('span','หลักฐาน 1 · '+uid.slice(0,12)+'…','mono copilot-citation');cite.title=uid;li.append(cite);ul.append(li);});section.append(ul);}
        findings.append(section);
      }body.append(findings);
      for(const [title,value] of [['หลักฐานต้นทางและ Exact UID',ev],['ข้อความต้นฉบับของโมเดล',row.draft]]){
        const disclosure=node('details');disclosure.append(node('summary',title),node('pre',JSON.stringify(value,null,2),'code-block'));body.append(disclosure);
      }detail.append(body);
    }
    async function load(){
      if(busy||!live())return;busy=true;reload.disabled=true;report=null;
      queue.replaceChildren();detail.replaceChildren();status.textContent='กำลังตรวจสิทธิ์และโหลดผลสรุป…';
      try{
        const response=await fetch('/api/nexus/v1/copilot/review',{credentials:'same-origin',cache:'no-store',redirect:'error',signal:AbortSignal.timeout(15000)});
        if(!live())return;
        if(response.status===401){status.textContent='ต้องยืนยันตัวตนก่อนดูหลักฐาน ';const link=node('a','ยืนยันตัวตนในหน้าต่างใหม่','link-button');link.href='/api/nexus/v1/copilot/review';link.target='_blank';link.rel='noopener';status.append(link);return;}
        if(!response.ok)throw Error();
        const data=await response.json();if(!live())return;
        if(data.saved_review_only!==true||data.human_review_required!==true||data.automated_response_allowed!==false||!Array.isArray(data.results)||data.results.length!==8)throw Error();
        report=data;status.textContent='8 สรุปที่รอตรวจ · สร้างเมื่อ '+data.generated_at+' · evidence hash '+data.input_evidence_hash.slice(0,16)+'…';show();
      }catch{if(live())status.textContent='ผลสรุปไม่พร้อมใช้งานหรือไม่ผ่านการตรวจ กรุณาลองโหลดใหม่';}
      finally{busy=false;if(live())reload.disabled=false;}
    }
    reload.addEventListener('click',event=>{event.stopPropagation();load();});load();
  }

  function render(preserve=false){const active=document.activeElement,id=active?.id,selection=active?.selectionStart;nav();$('main').innerHTML=({overview,alerts:alertsPage,allevents:allEventsPage,copilot:copilotPage,endpoints:endpointsPage,cases:casesPage,logs:logsPage,coverage:coveragePage,research:researchPage,modeldetails:researchExtrasPage,researchevidence:researchExtrasPage,shadowdetails:shadowDetailsPage,bluefielddetails:bluefieldDetailsPage,integrations:integrationsPage,settings:settingsPage}[state.page]||overview)();document.title=`${pages[state.page]} · NEXUS SIEM`;if(preserve&&id&&$(id)){const el=$(id);el.focus({preventScroll:true});if(typeof selection==='number'&&typeof el.setSelectionRange==='function')try{el.setSelectionRange(selection,selection);}catch{}}}
  function navigate(page){if(!pages[page])return;state.page=page;state.selected.clear();location.hash=page;closeDrawer();$('sidebar').classList.remove('open');render();window.scrollTo({top:0,behavior:'instant'});}
  function canWrite(){return state.mode!=='api'||state.data.meta.write_enabled!==false;}
  function detailField(label,value){return `<div class="detail-field"><span>${E(label)}</span><strong>${E(value||'Unavailable')}</strong></div>`;}
  function detailSection(title,body){return `<section class="detail-section"><h3>${E(title)}</h3>${body}</section>`;}
  function drawerHeader(label,id){return `<header class="drawer-header"><span>${E(label)} <span class="mono">/ ${E(id)}</span></span><button class="icon-button" data-action="close-drawer" aria-label="Close details">${icon('close')}</button></header>`;}
  function aiSeveritySection(ev){const status=ev&&ev.ai_status;if(status==='matched'){const valid=typeof ev.ai_score==='number'&&Number.isFinite(ev.ai_score)&&ev.ai_score>=0&&ev.ai_score<=1,score=valid?(ev.ai_score*100).toFixed(1)+' / 100':'ข้อมูลไม่ถูกต้อง';return detailSection('AI severity analysis',`<div class="detail-grid">${detailField('AI status',valid?'Scored':'Invalid AI score')}${detailField('คะแนนความรุนแรงจาก AI',score)}${detailField('Raw AI score (0–1)',valid?String(ev.ai_score):'—')}${detailField('AI label',ev.ai_label||ev.ai_class||'—')}${detailField('Model',ev.ai_model||ev.ai_engine||'—')}${detailField('Correlation','Exact event_uid')}</div><p class="form-help">คะแนน 0–100 แสดงแนวโน้มความรุนแรงจากโมเดลที่เรียนรู้ Wazuh severity ไม่ใช่เปอร์เซ็นต์โอกาสถูกโจมตี และไม่ใช้สั่งตอบสนองอัตโนมัติ</p>`);}const title=status==='unavailable'?'AI service unavailable':'ยังไม่มีผล AI';return detailSection('AI severity analysis',`<div class="notice">${icon('info')}<div><strong>${E(title)}</strong><p class="form-help">No exact event_uid AI result is available for this Wazuh alert.</p></div></div>`);}
  function alertDrawer(a){const ev=a.evidence||{},mitre=C.techniqueUrl(a.technique);const body=state.tab==='raw'?`<div class="form-actions" style="margin-bottom:15px"><button class="button quiet" data-action="copy-detail">${icon('copy')}Copy JSON</button></div><pre class="code-block">${E(JSON.stringify(a,null,2))}</pre>`:state.tab==='evidence'?detailSection('Observed process',`<div class="detail-grid">${detailField('Process',ev.process)}${detailField('Parent process',ev.parent_process)}${detailField('Process ID',ev.pid)}${detailField('Execution path',ev.process_path)}</div>`)+detailSection('Command line',`<div class="evidence-command">${E(ev.command_line||'No command-line evidence supplied.')}</div>`)+(ev.destination_ip?detailSection('Network evidence',`<div class="detail-grid">${detailField('Destination IP',ev.destination_ip)}${detailField('Destination port',ev.destination_port)}</div>`):'')+detailSection('Detection timeline',a.timeline.map(t=>`<div class="timeline-item"><small>${E(C.date(t.at))}</small><span>${E(t.action)}</span><span class="small-label">${E(t.actor)}</span></div>`).join('')||'<p class="notes-text">No timeline supplied.</p>'):detailSection('Detection context',`<div class="detail-grid">${detailField('Endpoint',a.host)}${detailField('Source IP',a.ip)}${detailField('User',a.user)}${detailField('Data source',a.source)}${detailField('Rule ID',a.rule_id)}${detailField('Last seen',C.date(a.last_seen))}</div>`)+aiSeveritySection(ev)+detailSection('MITRE ATT&CK',`<div class="notice">${icon('coverage')}<div><strong>${E(a.technique||'Unmapped')} · ${E(a.technique_name||'No technique mapping')}</strong><p class="form-help">${E(a.tactic)}</p>${mitre?`<a class="link-button" href="${E(mitre)}" target="_blank" rel="noopener noreferrer" style="margin-top:7px">Technique reference ${icon('external')}</a>`:''}</div></div>`)+detailSection('Evidence preview',`<div class="evidence-command">${E(ev.command_line||'No command-line evidence supplied.')}</div>`)+detailSection('Linked investigations',state.data.cases.filter(c=>c.alert_ids.includes(a.id)).map(c=>`<button class="button quiet full-width" style="margin-bottom:7px;justify-content:flex-start;white-space:normal;text-align:left" data-action="case-detail" data-id="${E(c.id)}">${icon('cases')}${E(c.title)}</button>`).join('')||'<p class="notes-text">No case linked. Create a case to track this investigation.</p>');return drawerHeader('DETECTION DETAILS',a.id)+`<div class="drawer-body"><div class="drawer-eyebrow">${tag(a.severity)}${tag(a.status)}</div><h2>${E(a.title)}</h2><p class="drawer-subtitle">${E(a.description)}</p><div class="detail-tabs">${[['summary','Overview'],['evidence','Evidence'],['raw','Raw event']].map(([v,t])=>`<button data-action="detail-tab" data-tab="${v}" class="${state.tab===v?'active':''}">${t}</button>`).join('')}</div>${body}</div><footer class="drawer-footer"><span class="drawer-note">${state.mode==='api'?'Changes are saved through the connected API.':state.mode==='demo'?'Demo workflow · changes saved in this browser.':'Imported snapshot · changes stay in this session.'}</span>${a.status!=='acknowledged'?`<button class="button quiet" data-action="alert-status" data-status="acknowledged" ${!canWrite()?'disabled':''}>Acknowledge</button>`:''}${a.status!=='resolved'?`<button class="button quiet" data-action="alert-status" data-status="resolved" ${!canWrite()?'disabled':''}>${icon('check')}Resolve</button>`:`<button class="button quiet" data-action="alert-status" data-status="new" ${!canWrite()?'disabled':''}>Reopen</button>`}<button class="button primary" data-action="new-case" data-alert-id="${E(a.id)}" ${!canWrite()?'disabled':''}>${icon('plus')}Create case</button></footer>`;}
  function endpointDrawer(e){const rows=state.data.alerts.filter(a=>a.host===e.host&&a.status!=='resolved');return drawerHeader('ENDPOINT DETAILS',e.id)+`<div class="drawer-body"><div class="drawer-eyebrow">${tag(e.status)}<span class="small-label">Risk score: ${Number.isFinite(e.risk)?e.risk+' / 100':'N/A'}</span></div><h2>${E(e.host)}</h2><p class="drawer-subtitle">Endpoint telemetry and agent health.</p>${detailSection('Host inventory',`<div class="detail-grid">${detailField('IP address',e.ip)}${detailField('Operating system',e.os)}${detailField('Logged-in user',e.user)}${detailField('Department',e.department)}${detailField('Agent version',e.agent_version)}${detailField('Last seen',e.last_seen?C.date(e.last_seen):'Unknown')}</div>`)}${detailSection('Unresolved detections',rows.map(a=>`<button class="button quiet full-width" style="justify-content:flex-start;margin-bottom:8px;text-align:left;white-space:normal" data-action="alert-detail" data-id="${E(a.id)}">${tag(a.severity)}${E(a.title)}</button>`).join('')||'<p class="notes-text">No unresolved detections for this endpoint.</p>')}<div class="notice">${icon('info')}<p>Endpoint response actions are managed by your EDR control plane. This dashboard provides investigation and triage.</p></div></div><footer class="drawer-footer"><button class="button" data-action="host-alerts" data-host="${E(e.host)}">${icon('alerts')}All host detections</button><button class="button primary" data-action="host-events" data-host="${E(e.host)}">${icon('logs')}Explore events</button></footer>`;}
  function eventDrawer(e){return drawerHeader('EVENT INSPECTOR',e.id)+`<div class="drawer-body"><div class="drawer-eyebrow">${tag(e.source,'source')}${tag(e.severity)}</div><h2>${E(e.event_type)}</h2><p class="drawer-subtitle">${E(e.message)}</p>${detailSection('Event context',`<div class="detail-grid">${detailField('Timestamp',C.date(e.timestamp))}${detailField('Endpoint',e.host)}${detailField('IP address',e.ip)}${detailField('Event ID',e.event_id)}${detailField('Process',e.process)}${detailField('User',e.user)}</div>`)}${detailSection('Original payload',`<pre class="code-block">${E(JSON.stringify(e.raw,null,2))}</pre>`)}</div><footer class="drawer-footer"><button class="button" data-action="copy-detail">${icon('copy')}Copy event JSON</button><button class="button primary" data-action="host-alerts" data-host="${E(e.host)}">${icon('alerts')}Host detections</button></footer>`;}
  function caseDrawer(c){return drawerHeader('INVESTIGATION',c.id)+`<div class="drawer-body"><div class="drawer-eyebrow">${tag(c.severity)}${tag(c.status)}</div><h2>${E(c.title)}</h2><p class="drawer-subtitle">${E(c.description)}</p>${detailSection('Case context',`<div class="detail-grid">${detailField('Owner',c.owner)}${detailField('Created',C.date(c.created_at))}</div>`)}${detailSection('Linked detections',c.alert_ids.map(id=>{const a=state.data.alerts.find(a=>a.id===id);return a?`<button class="button quiet full-width" style="justify-content:flex-start;text-align:left;white-space:normal;margin-bottom:7px" data-action="alert-detail" data-id="${E(a.id)}">${tag(a.severity)}${E(a.title)}</button>`:`<p class="notes-text">${E(id)} · outside the loaded snapshot</p>`;}).join('')||'<p class="notes-text">No detections linked.</p>')}${detailSection('Analyst notes',c.comments.map(n=>`<div class="comment-box"><strong>${E(n.author)}</strong> <small>${E(C.date(n.at))}</small><p>${E(n.text)}</p></div>`).join('')||'<p class="notes-text">No notes yet.</p>')}<form id="note-form"><div class="form-field"><label for="case-note">Add investigation note</label><textarea id="case-note" placeholder="Record your findings…" maxlength="5000" required ${!canWrite()?'disabled':''}></textarea></div><button class="button" type="submit" ${!canWrite()?'disabled':''}>${icon('plus')}Add note</button></form></div><footer class="drawer-footer"><select class="select" id="case-status" aria-label="Case status" ${!canWrite()?'disabled':''}>${['open','investigating','closed'].map(s=>`<option value="${s}" ${s===c.status?'selected':''}>${s[0].toUpperCase()+s.slice(1)}</option>`).join('')}</select><button class="button primary" data-action="save-case-status" ${!canWrite()?'disabled':''}>${icon('check')}Update status</button></footer>`;}
  function showDrawer(type,id){returnFocus=document.activeElement;state.detail={type,id};state.tab='summary';renderDrawer();}
  function renderDrawer(){if(!state.detail)return;const {type,id}=state.detail,key={alert:'alerts',endpoint:'endpoints',event:'events',case:'cases'}[type],record=state.data[key].find(r=>r.id===id);if(!record){closeDrawer();toast('This record is outside the current snapshot.',true);return;}$('drawer').innerHTML=({alert:alertDrawer,endpoint:endpointDrawer,event:eventDrawer,case:caseDrawer}[type])(record);$('drawer').setAttribute('aria-label',record.title||record.host||record.event_type||'Details');$('drawer').hidden=false;$('overlay').hidden=false;document.body.style.overflow='hidden';$('drawer').querySelector('[data-action="close-drawer"]')?.focus({preventScroll:true});}
  function closeDrawer(){state.detail=null;$('drawer').hidden=true;$('overlay').hidden=true;document.body.style.overflow='';if(returnFocus?.isConnected)returnFocus.focus({preventScroll:true});returnFocus=null;}
  function modal(title,body){const el=$('modal');el.innerHTML=`<div class="modal-heading"><h2>${E(title)}</h2><button class="icon-button" data-action="close-modal" aria-label="Close dialog">${icon('close')}</button></div><div class="modal-body">${body}</div>`;if(!el.open)el.showModal();}
  function guide(){modal('เริ่มใช้งาน NEXUS SIEM',`<div class="guide-step"><span class="step-number">1</span><div><strong>ทดลองตรวจสอบเหตุการณ์</strong><p>เปิด Threat detection แล้วเลือก Alert เพื่อดูหลักฐาน กด Acknowledge หรือ Resolve และสร้าง Case สำหรับติดตามการตรวจสอบ ข้อมูลเริ่มต้นทั้งหมดเป็น Demo</p></div></div><div class="guide-step"><span class="step-number">2</span><div><strong>เชื่อมระบบ EDR / XDR</strong><p>ไป Data sources ใส่ URL ของ API ตาม schema แล้วกด Test & connect หากใช้ OpenSearch ให้รัน Python adapter จาก ZIP และตั้งชื่อ index กับ field mapping ในไฟล์ environment</p></div></div><div class="guide-step"><span class="step-number">3</span><div><strong>ติดตั้งในโปรเจกต์</strong><p>แตก ZIP แล้วรัน <code>docker compose up --build -d</code> จากนั้นเปิด <code>http://localhost:8080</code> หรือคัดลอกโฟลเดอร์ dist ไปเสิร์ฟในโปรเจกต์เดิม</p></div></div><div class="guide-step"><span class="step-number">4</span><div><strong>ค้นหาและส่งออกรายงาน</strong><p>ค้นหา Logs ด้วย <code>host:</code>, <code>source:</code>, <code>event:</code> และส่งออก CSV หรือ JSON สำหรับรายงานงาน EDR/XDR</p></div></div><div class="notice">${icon('info')}<p>Dashboard จะระบุ Demo, Imported snapshot หรือ API connected ชัดเจน เมื่อ API ขาดการเชื่อมต่อจะแสดงข้อมูลครั้งล่าสุดพร้อมสถานะ Connection lost</p></div>`);}
  function newCase(alertId=''){if(!canWrite()){toast('The connected API is read-only.',true);return;}const a=state.data.alerts.find(a=>a.id===alertId);modal('Create investigation',`<form id="case-form" data-alert-id="${E(alertId)}"><div class="form-field"><label for="case-title">Case title</label><input id="case-title" maxlength="240" value="${E(a?'Investigate: '+a.title:'')}" placeholder="Describe the investigation" required></div><div class="grid-two"><div class="form-field"><label for="case-severity">Priority</label><select id="case-severity">${C.SEVERITIES.filter(s=>s!=='info').map(s=>`<option value="${s}" ${s===(a?.severity||'medium')?'selected':''}>${s[0].toUpperCase()+s.slice(1)}</option>`).join('')}</select></div><div class="form-field"><label for="case-owner">Owner</label><input id="case-owner" value="SOC Analyst" maxlength="120" required></div></div><div class="form-field"><label for="case-description">Investigation notes</label><textarea id="case-description" maxlength="5000" placeholder="What should be reviewed?"></textarea></div>${a?`<div class="notice section-gap">${icon('alerts')}Linked alert: ${E(a.id)}</div>`:''}<div class="form-actions"><button class="button primary" type="submit">${icon('plus')}Create case</button><button class="button quiet" type="button" data-action="close-modal">Cancel</button></div></form>`);}
  function normalBase(raw){const s=String(raw).trim().replace(/\/+$/,'');if(s.startsWith('/')&&!s.startsWith('//'))return s;const url=new URL(s);if(!['http:','https:'].includes(url.protocol)||url.username||url.password||url.search||url.hash)throw new Error('Use an HTTP(S) API URL without credentials or query parameters.');if(location.protocol==='https:'&&url.protocol==='http:')throw new Error('This hosted dashboard requires an HTTPS API. Run the Docker package locally to use a local HTTP backend.');return url.href.replace(/\/+$/,'');}
  async function request(path,method='GET',body,base=state.apiBase,token=state.token){const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),20000);try{const response=await fetch(base+path,{method,credentials:'same-origin',signal:controller.signal,cache:'no-store',headers:{Accept:'application/json',...(body?{'Content-Type':'application/json'}:{}),...(token?{Authorization:'Bearer '+token}:{})},...(body?{body:JSON.stringify(body)}:{})});if(!response.ok){let message='';try{const problem=await response.json();message=problem.error||problem.detail||'';}catch{}throw new Error(`API returned HTTP ${response.status}${message?' · '+String(message).slice(0,300):''}`);}return await response.json();}catch(e){if(e.name==='AbortError')throw new Error('The API request timed out.');if(e instanceof TypeError)throw new Error('Cannot reach the API. Check its URL, HTTPS, network access, and CORS settings.');throw e;}finally{clearTimeout(timeout);}}
  async function connect(base,token){if(state.busy)return;state.busy=true;render(true);try{base=normalBase(base);const data=C.validateSnapshot(await request('/snapshot?hours='+C.hours(state.range),'GET',undefined,base,token));state.data=data;state.apiBase=base;state.token=token;state.mode='api';state.connected=true;state.connectionError='';state.lastFetch=C.iso(Date.now());state.selected.clear();savePreferences();startTimer();render();toast(data.meta.demo?'Connected to the demo API. Telemetry is synthetic.':'Connected. API telemetry loaded.');}catch(e){toast(e.message,true);}finally{state.busy=false;render(true);}}
  async function refresh(silent=false){if(state.busy)return;if(state.mode!=='api'){if(!silent)toast(state.mode==='demo'?'Demo snapshot refreshed. Connect an API for live telemetry.':'This is a saved snapshot. Import a new file to update it.');render(true);return;}state.busy=true;if(!silent)render(true);try{const data=C.validateSnapshot(await request('/snapshot?hours='+C.hours(state.range)));state.data=data;state.connected=true;state.connectionError='';state.lastFetch=C.iso(Date.now());render(true);if(state.detail)renderDrawer();if(!silent)toast('Telemetry snapshot updated.');}catch(e){state.connectionError=e.message;state.connected=false;render(true);if(!silent)toast(e.message,true);}finally{state.busy=false;if(!silent)render(true);}}
  function startTimer(){if(timer)clearInterval(timer);if(state.mode==='api'&&state.refreshSeconds)timer=setInterval(()=>{if(!document.hidden)refresh(true);},state.refreshSeconds*1000);}
  async function updateAlert(id,status){if(!canWrite())throw new Error('The connected API is read-only.');const a=state.data.alerts.find(a=>a.id===id);if(!a)return;if(state.mode==='api'){await request('/alerts/'+encodeURIComponent(id),'PATCH',{status});a.status=status;a.timeline.push({at:C.iso(Date.now()),action:status==='resolved'?'Resolved by analyst':status==='acknowledged'?'Acknowledged by analyst':'Reopened by analyst',actor:'SOC Analyst'});}else{a.status=status;a.timeline.push({at:C.iso(Date.now()),action:status==='resolved'?'Resolved by analyst':status==='acknowledged'?'Acknowledged by analyst':'Reopened by analyst',actor:'SOC Analyst'});saveDemoState();}}
  async function patchCase(c,updates){if(!canWrite())throw new Error('The connected API is read-only.');if(state.mode==='api')await request('/cases/'+encodeURIComponent(c.id),'PATCH',updates);Object.assign(c,updates);saveDemoState();}
  function download(content,name,type){const blob=new Blob([content],{type}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),5000);toast('Export downloaded.');}
  async function importFile(file){if(!file)return;if(file.size>15*1024*1024){toast('Use a JSON snapshot smaller than 15 MB.',true);return;}try{const data=C.validateSnapshot(JSON.parse(await file.text()));state.data=data;state.mode='import';state.connected=false;state.connectionError='';state.token='';state.selected.clear();startTimer();closeDrawer();render();toast('Snapshot imported. '+N(data.alerts.length)+' detections loaded.');}catch(e){toast('Import failed: '+e.message,true);}finally{$('import-file').value='';}}
  async function copyDetail(){if(!state.detail)return;const {type,id}=state.detail,key={alert:'alerts',endpoint:'endpoints',event:'events',case:'cases'}[type],record=state.data[key].find(r=>r.id===id),json=JSON.stringify(type==='event'?record.raw:record,null,2);try{await navigator.clipboard.writeText(json);toast('JSON copied to clipboard.');}catch{modal('Copy event JSON',`<div class="form-field"><label for="copy-json">Select and copy this payload</label><textarea id="copy-json" style="min-height:300px" readonly>${E(json)}</textarea></div>`);$('copy-json').select();}}
  function resetFilters(){state.alertFilter={query:'',severity:'all',status:'active',sort:'newest',source:'',host:'',technique:''};state.alertPage=1;state.selected.clear();$('global-search').value='';}
  const actions={
    navigate:el=>navigate(el.dataset.page),guide,refresh:()=>refresh(),
    'critical-alerts':()=>{resetFilters();state.alertFilter.severity='critical';navigate('alerts');},
    severity:el=>{resetFilters();state.alertFilter.severity=el.dataset.severity;navigate('alerts');},
    technique:el=>{resetFilters();state.alertFilter.technique=el.dataset.technique;state.alertFilter.status='all';navigate('alerts');},
    'alert-detail':el=>showDrawer('alert',el.dataset.id),'endpoint-detail':el=>showDrawer('endpoint',el.dataset.id),'event-detail':el=>showDrawer('event',el.dataset.id),'case-detail':el=>showDrawer('case',el.dataset.id),
    'close-drawer':closeDrawer,'close-modal':()=>$('modal').close(),'detail-tab':el=>{state.tab=el.dataset.tab;renderDrawer();},
    'new-case':el=>newCase(el?.dataset.alertId||''),
    'alert-status':async el=>{if(el.disabled)return;el.disabled=true;try{await updateAlert(state.detail.id,el.dataset.status);render();renderDrawer();toast('Alert '+el.dataset.status+'.');}catch(e){toast(e.message,true);el.disabled=false;}},
    'bulk-status':async el=>{el.disabled=true;let n=0;try{for(const id of state.selected){await updateAlert(id,el.dataset.status);n++;}state.selected.clear();render();toast(n+' alerts '+el.dataset.status+'.');}catch(e){render();toast(`${n} alerts updated. ${e.message}`,true);}},
    'clear-selection':()=>{state.selected.clear();render();},'clear-filters':()=>{resetFilters();render();},
    paginate:el=>{const key={alert:'alertPage',event:'eventPage',endpoint:'endpointPage'}[el.dataset.type];state[key]=Number(el.dataset.pageNumber);render();},
    'export-alerts':()=>download(C.csv(alertRows(),['id','title','severity','status','host','ip','source','technique','last_seen']),'nexus-alerts.csv','text/csv;charset=utf-8'),
    'export-endpoints':()=>download(C.csv(endpointRows(),['id','host','ip','os','status','risk','agent_version','last_seen']),'nexus-endpoints.csv','text/csv;charset=utf-8'),
    'export-events':()=>download(C.csv(logRows(),['id','timestamp','source','host','ip','event_type','severity','message']),'nexus-events.csv','text/csv;charset=utf-8'),
    'download-snapshot':()=>download(JSON.stringify(state.data,null,2),'nexus-snapshot.json','application/json'),
    'host-alerts':el=>{resetFilters();state.alertFilter.host=el.dataset.host;state.alertFilter.status='all';navigate('alerts');},
    'host-events':el=>{state.logFilter={query:'host:"'+el.dataset.host+'"',severity:'all',source:''};state.eventPage=1;navigate('logs');},
    'source-events':el=>{state.logFilter={query:'',severity:'all',source:el.dataset.source};state.eventPage=1;navigate('logs');},
    'run-query':()=>{state.logFilter.query=$('log-query').value;state.eventPage=1;render();},'clear-log-query':()=>{state.logFilter={query:'',source:'',severity:'all'};state.eventPage=1;render();},
    'copy-detail':copyDetail,import:()=>$('import-file').click(),
    'demo-mode':()=>{state.mode='demo';state.data=C.seed();state.connected=false;state.connectionError='';state.token='';state.selected.clear();applyDemoState();startTimer();closeDrawer();render();toast('Demo workspace loaded.');},
    'reset-demo':()=>modal('Reset demo workspace?',`<p class="notes-text section-gap">This clears sample triage changes and sample case notes saved in this browser.</p><div class="form-actions"><button class="button primary" data-action="confirm-reset-demo">Reset demo</button><button class="button quiet" data-action="close-modal">Cancel</button></div>`),
    'confirm-reset-demo':()=>{try{localStorage.removeItem('nexus.demo.v1');}catch{}$('modal').close();state.mode='demo';state.data=C.seed();state.connected=false;state.connectionError='';state.token='';state.selected.clear();resetFilters();startTimer();render();toast('Demo workspace reset.');},
    'save-case-status':async el=>{el.disabled=true;try{const c=state.data.cases.find(c=>c.id===state.detail.id);await patchCase(c,{status:$('case-status').value});render();renderDrawer();toast('Case status updated.');}catch(e){el.disabled=false;toast(e.message,true);}}
  };
  document.addEventListener('click',event=>{if(event.target.matches('input[type="checkbox"]'))return;const target=event.target.closest('[data-action]');if(target&&actions[target.dataset.action]){event.preventDefault();Promise.resolve(actions[target.dataset.action](target)).catch(e=>toast(e.message,true));}});
  document.addEventListener('change',event=>{const el=event.target;if(el.id==='time-range'){state.range=el.value;savePreferences();state.alertPage=state.eventPage=1;state.selected.clear();if(state.mode==='api')refresh();else render();}else if(el.id==='severity-filter'){state.alertFilter.severity=el.value;state.alertPage=1;state.selected.clear();render();}else if(el.id==='status-filter'){state.alertFilter.status=el.value;state.alertPage=1;state.selected.clear();render();}else if(el.id==='alert-sort'){state.alertFilter.sort=el.value;render();}else if(el.id==='endpoint-status'){state.endpointFilter.status=el.value;state.endpointPage=1;render();}else if(el.id==='log-source'){state.logFilter.source=el.value;state.eventPage=1;render();}else if(el.id==='auto-refresh'){state.refreshSeconds=Number(el.value);savePreferences();startTimer();toast('Refresh preference saved.');}else if(el.dataset.selectAlert){el.checked?state.selected.add(el.dataset.selectAlert):state.selected.delete(el.dataset.selectAlert);render();}else if(el.id==='select-page'){const rows=alertRows().slice((state.alertPage-1)*12,state.alertPage*12);rows.forEach(a=>el.checked?state.selected.add(a.id):state.selected.delete(a.id));render();}else if(el.id==='import-file')importFile(el.files[0]);});
  document.addEventListener('input',event=>{const el=event.target;if(el.id==='alert-search'){state.alertFilter.query=el.value;state.alertPage=1;state.selected.clear();render(true);}else if(el.id==='endpoint-search'){state.endpointFilter.query=el.value;state.endpointPage=1;render(true);}else if(el.id==='global-search'){state.alertFilter.query=el.value;state.alertFilter.status='all';state.alertFilter.host=state.alertFilter.source=state.alertFilter.technique='';state.alertFilter.severity='all';state.alertPage=1;state.selected.clear();if(state.page!=='alerts'){state.page='alerts';location.hash='alerts';}render();}});
  document.addEventListener('submit',async event=>{const form=event.target;event.preventDefault();if(form.id==='api-form')return connect($('api-base').value,$('api-token').value.trim());const submit=form.querySelector('[type="submit"]');if(submit)submit.disabled=true;try{if(form.id==='case-form'){const a=state.data.alerts.find(a=>a.id===form.dataset.alertId);let c={id:'INC-'+new Date().getUTCFullYear()+'-'+Date.now().toString(36).toUpperCase(),title:$('case-title').value.trim(),severity:$('case-severity').value,status:'open',owner:$('case-owner').value.trim(),description:$('case-description').value.trim(),alert_ids:a?[a.id]:[],created_at:C.iso(Date.now()),comments:[]};if(!c.title||!c.owner)throw new Error('Enter a case title and owner.');if(state.mode==='api')c=await request('/cases','POST',c);state.data.cases.push(C.validateSnapshot({...state.data,cases:[c]}).cases[0]);saveDemoState();$('modal').close();navigate('cases');showDrawer('case',c.id);toast('Investigation created.');}else if(form.id==='note-form'){const c=state.data.cases.find(c=>c.id===state.detail.id),text=$('case-note').value.trim();if(!text)throw new Error('Enter a note before saving.');await patchCase(c,{comments:[...c.comments,{at:C.iso(Date.now()),author:'SOC Analyst',text}]});render();renderDrawer();toast('Investigation note saved.');}}catch(e){toast(e.message,true);if(submit)submit.disabled=false;}});
  document.addEventListener('keydown',event=>{const input=event.target.matches('input,textarea,select');if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'){event.preventDefault();if(getComputedStyle($('global-search').parentElement).display==='none'){resetFilters();navigate('alerts');$('alert-search')?.focus();}else $('global-search').focus();}if(event.key==='Escape'){$('sidebar').classList.remove('open');if(!$('modal').open)closeDrawer();}if(event.key==='?'&&!input){event.preventDefault();guide();}if(event.key==='Enter'&&event.target.id==='log-query'){event.preventDefault();actions['run-query']();}if((event.key==='Enter'||event.key===' ')&&event.target.matches('.case-card')){event.preventDefault();showDrawer('case',event.target.dataset.id);}if(event.key==='Tab'&&!$('drawer').hidden&&!$('modal').open){const els=[...$('drawer').querySelectorAll('button:not(:disabled),a[href],input,select,textarea')].filter(el=>el.offsetParent!==null),first=els[0],last=els.at(-1);if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus();}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus();}}});
  window.addEventListener('hashchange',()=>{const page=location.hash.slice(1);if(pages[page]&&page!==state.page){state.page=page;state.selected.clear();closeDrawer();render();}});
  $('overlay').addEventListener('click',closeDrawer);$('mobile-menu').addEventListener('click',()=>$('sidebar').classList.toggle('open'));
  $('modal').addEventListener('click',e=>{if(e.target===$('modal')){const r=$('modal').getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)$('modal').close();}});
  $('search-icon').innerHTML=icon('search');$('notification-icon').innerHTML=icon('bell');$('mobile-menu').innerHTML=icon('menu');
  render();
  connect('/api/v1','');
})();
