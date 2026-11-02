(() => {
  'use strict';
  let active = null, generation = 0;
  const make = (tag, text, cls) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = String(text); if (cls) n.className = cls; return n; };
  function mount() {
    active?.abort(); const token = ++generation;
    const root = document.getElementById('model-lab-root'); if (!root) return;
    root.replaceChildren();
    root.append(make('h1', 'Model Lab · DFP / Ransomware'));
    root.append(make('p', 'Dataset replay · ไม่ใช่ Live alerts · ไม่ได้แทน BERT · Automated response OFF', 'notice warn'));
    root.append(make('p', 'คะแนนจากผลทดลองเดิม ไม่ได้เรียกโมเดลใหม่ และยังไม่ได้ประเมินคุณภาพการตรวจจับ'));
    const label = make('label', 'Pipeline '), filter = make('select'); filter.setAttribute('aria-label', 'Lab pipeline');
    for (const [value, text] of [['all','All pipelines'],['dfp','DFP'],['ransomware','Ransomware CPU']]) {
      const option = make('option', text); option.value = value; filter.append(option);
    }
    label.append(filter);
    const prev = make('button', 'Previous', 'button'), next = make('button', 'Next', 'button'), reload = make('button', 'Reload', 'button');
    for (const b of [prev,next,reload]) b.type = 'button';
    const status = make('p', 'กำลังอ่านผล Lab…'); status.setAttribute('role','status');
    const content = make('div'); root.append(label, reload, prev, next, status, content);
    let page = 1, requestId = 0;
    const current = id => generation === token && id === requestId && root.isConnected && document.getElementById('model-lab-root') === root && location.hash === '#modellab';
    async function load(wanted) {
      active?.abort(); const controller = new AbortController(); active = controller; const id = ++requestId;
      content.replaceChildren(); status.replaceChildren(); status.textContent = 'กำลังอ่านผล Lab…'; prev.disabled = next.disabled = true;
      const timer = setTimeout(() => controller.abort(), 15000);
      try {
        const r = await fetch('/api/nexus/v1/lab?' + new URLSearchParams({page:String(wanted),pipeline:filter.value}), {
          credentials:'same-origin', cache:'no-store', redirect:'error', signal:controller.signal
        });
        if (!current(id)) return;
        if (r.status === 401) {
          status.textContent = 'ต้องเข้าสู่ระบบเพื่ออ่านผล Lab ';
          const a = make('a', 'Sign in'); a.href = '/api/nexus/v1/lab'; status.append(a); return;
        }
        if (!r.ok) throw new Error();
        const d = await r.json(); if (!current(id)) return;
        if (!d || d.source !== 'edrxdr-ai-lab-v1' || d.schema_version !== 'morpheus-lab-observation-1' || d.processing_mode !== 'dataset_replay' || d.complete !== true ||
          d.production_ready !== false || d.automated_response_allowed !== false || d.quality_metrics_evaluated !== false || d.page !== wanted || d.page_size !== 50 || d.pipeline !== filter.value ||
          !Number.isSafeInteger(d.total) || d.total < 0 || d.total > 1000 || !Array.isArray(d.observations) || d.observations.length !== Math.min(50,Math.max(0,d.total-(wanted-1)*50))) throw new Error();
        const fragment = document.createDocumentFragment(); const ids = new Set();
        for (const e of d.observations) {
          if (!e || !/^[0-9a-f]{64}$/.test(e.observation_id) || ids.has(e.observation_id) || !['dfp','ransomware'].includes(e.pipeline_id) ||
            (filter.value !== 'all' && filter.value !== e.pipeline_id) || e.production_ready !== false || e.automated_response_allowed !== false || e.quality_metrics_evaluated !== false || e.processing_mode !== 'dataset_replay') throw new Error();
          ids.add(e.observation_id);
          const s=e.scores, t=e.details; if (!s || !t) throw new Error();
          const finite = n => typeof n === 'number' && Number.isFinite(n);
          const card = make('article', undefined, 'panel'); card.style.padding='16px'; card.style.marginTop='12px'; card.style.overflowWrap='anywhere';
          card.append(make('h2', e.pipeline_id === 'dfp' ? 'DFP · Duo sample · GPU result' : 'Ransomware · CPU · training CSV window'));
          if(e.pipeline_id==='dfp') {
            if(!finite(s.mean_abs_z)||!finite(s.max_abs_z)||s.mean_abs_z<0||s.max_abs_z<s.mean_abs_z||t.execution_backend!=='gpu') throw new Error();
            card.append(make('p', 'mean_abs_z: '+s.mean_abs_z+' · max_abs_z: '+s.max_abs_z));
            card.append(make('p', 'Z-scores ไม่ใช่ probability และไม่มี alert threshold ที่ผ่าน validation'));
          } else {
            if(!finite(s.output_0)||!finite(s.output_1)||s.output_0<0||s.output_0>1||s.output_1<0||s.output_1>1||Math.abs(s.output_0+s.output_1-1)>1e-4||t.execution_backend!=='cpu'||t.class_mapping!=='unverified') throw new Error();
            card.append(make('p', 'output_0: '+s.output_0+' · output_1: '+s.output_1));
            card.append(make('p', 'Class mapping ยังไม่ยืนยัน จึงไม่ระบุ benign/ransomware จากตำแหน่ง output'));
          }
          card.append(make('p', 'Observation ID: '+e.observation_id,'mono'));
          card.append(make('p', 'Model: '+e.model_name+' · version '+e.model_version));
          card.append(make('p', 'เวลานำเข้าผล (ไม่ใช่เวลาเหตุการณ์): '+e.observed_at_utc));
          fragment.append(card);
        }
        content.replaceChildren(fragment); page=wanted;
        status.textContent = d.total+' observations · Page '+page+' / '+Math.max(1,Math.ceil(d.total/50));
        if(!d.total) content.append(make('p','ไม่มีผล Lab ใน pipeline นี้'));
        prev.disabled=page<=1; next.disabled=page*50>=d.total;
      } catch { if(current(id)){content.replaceChildren(); status.textContent='ผล Lab ไม่พร้อมใช้งานหรือไม่ผ่านการตรวจ ไม่มีผลเก่ามาแสดงแทน';} }
      finally { clearTimeout(timer); }
    }
    filter.onchange=()=>load(1); reload.onclick=()=>load(1); prev.onclick=()=>load(page-1); next.onclick=()=>load(page+1);
    load(1);
  }
  window.addEventListener('hashchange',()=>{active?.abort();generation++;});
  window.NexusModelLab = Object.freeze({mount});
})();
