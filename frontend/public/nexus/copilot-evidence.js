(() => {
  'use strict';
  const validUid = value => typeof value === 'string' && /^[0-9a-f]{64}$/.test(value);
  let selected = '', generation = 0, active;
  const clear = () => { generation++; if (active) active.abort(); active = null; };
  const node = (tag, text, cls) => {
    const el = document.createElement(tag);
    if (text !== undefined) el.textContent = text;
    if (cls) el.className = cls;
    return el;
  };
  function validate(data, uid) {
    if (!data || data.schema_version !== 'local-evidence-v1' || data.evidence_only !== true ||
      data.summary_status !== 'not_requested' || data.automated_response_allowed !== false ||
      data.external_transfer_allowed !== false || data.production_ready !== false ||
      !validUid(data.input_evidence_hash) || !Array.isArray(data.results) || data.results.length !== 1) throw Error();
    const row = data.results[0];
    if (!row || row.event_uid !== uid || !['matched','not_found','conflict','unavailable','source_unavailable'].includes(row.evidence_status) ||
      data.complete !== (row.evidence_status === 'matched')) throw Error();
    if (row.evidence_status !== 'matched') { if (row.fact !== null) throw Error(); return row; }
    const f = row.fact;
    if (!f || f.event_uid !== uid || typeof f.description !== 'string' || f.description.length > 512 ||
      typeof f.rule_id !== 'string' || !f.rule_id || f.rule_id.length > 128 ||
      !Number.isInteger(f.wazuh_level) || f.wazuh_level < 0 || f.wazuh_level > 15 ||
      !['matched','not_scored','conflict','unavailable'].includes(f.ai_status) ||
      !(f.timestamp_utc === null || typeof f.timestamp_utc === 'string' && Number.isFinite(Date.parse(f.timestamp_utc)))) throw Error();
    if (f.ai_status === 'matched') {
      if (!Number.isFinite(f.ai_score) || f.ai_score < 0 || f.ai_score > 1 ||
        !['high_severity','low_severity'].includes(f.ai_label)) throw Error();
    } else if (f.ai_score !== null || f.ai_label !== null) throw Error();
    if (!row.source_ref || typeof row.source_ref.index !== 'string' ||
      !/^wazuh-alerts-4\.x-\d{4}\.\d{2}\.\d{2}$/.test(row.source_ref.index) ||
      typeof row.source_ref.id !== 'string' || !row.source_ref.id || row.source_ref.id.length > 512) throw Error();
    return row;
  }
  async function mount() {
    const root = document.getElementById('copilot-live-root');
    if (!root || !validUid(selected)) return;
    clear(); const ticket = generation, uid = selected;
    active = new AbortController(); const controller = active;
    const current = () => ticket === generation && location.hash === '#copilot' &&
      document.getElementById('copilot-live-root') === root && selected === uid;
    root.replaceChildren();
    root.append(node('h1','SOC Copilot · ตรวจหลักฐาน'), node('p',uid,'mono'));
    const back = node('a','กลับ All Events','button'); back.href = '#allevents';
    root.append(back, node('p','ยังไม่สร้างสรุป · Automated response OFF','notice warn'));
    const status = node('p','กำลังตรวจสิทธิ์และอ่านหลักฐานล่าสุด…');
    const detail = node('div'); root.append(status, detail);
    const timer = setTimeout(() => controller.abort(), 45000);
    try {
      const response = await fetch('/api/nexus/v1/copilot/evidence', {
        method:'POST', credentials:'same-origin', cache:'no-store', redirect:'error',
        headers:{'Content-Type':'application/json'}, body:JSON.stringify({event_uids:[uid]}), signal:controller.signal,
      });
      if (!current()) return;
      if (!response.ok) {
        status.textContent = response.status === 401 ? 'ต้องยืนยันตัวตนก่อนอ่านหลักฐาน' :
          response.status === 403 ? 'UID นี้ไม่ได้รับอนุญาตจาก server' :
          response.status === 429 ? 'มีคำขอมากเกินไป กรุณาลองใหม่ภายหลัง' : 'ระบบตรวจหลักฐานไม่พร้อมใช้งาน';
        if (response.status === 401) {
          const link = node('a','ยืนยันตัวตน','button'); link.href='/api/nexus/v1/copilot/review';
          link.target='_blank'; link.rel='noopener'; detail.append(link);
        }
        return;
      }
      const data = await response.json();
      if (!current()) return;
      const row = validate(data, uid);
      status.textContent = 'หลักฐาน: '+row.evidence_status;
      if (row.evidence_status !== 'matched') return;
      const f = row.fact;
      detail.append(node('h2','หลักฐานที่ตรวจใหม่จาก server'),node('p',f.description),
        node('p','Rule '+f.rule_id+' · Wazuh '+f.wazuh_level+' / 15'),
        node('p','AI: '+f.ai_status+' · '+(f.ai_status === 'matched' ? (f.ai_score*100).toFixed(1)+' / 100' : 'ไม่มีคะแนนที่ยืนยันได้')),
        node('p','คะแนนเดิม ไม่ใช่ความน่าจะเป็นการโจมตี'),
        node('p','เวลาเหตุการณ์: '+(f.timestamp_utc ?? 'ไม่ทราบ')),
        node('p','Evidence hash: '+data.input_evidence_hash,'mono'));
      const evidence = node('details'), summary = node('summary','หลักฐานต้นทางและ Exact UID');
      // Explicit projection: never display arbitrary fields from a response.
      evidence.append(summary,node('pre',JSON.stringify({event_uid:uid,rule_id:f.rule_id,
        timestamp_utc:f.timestamp_utc,wazuh_level:f.wazuh_level,description:f.description,
        ai_status:f.ai_status,ai_score:f.ai_score,ai_label:f.ai_label,
        source_ref:{index:row.source_ref.index,id:row.source_ref.id}},null,2)));
      detail.append(evidence);
    } catch {
      if (current()) { detail.replaceChildren(); status.textContent='อ่านหลักฐานไม่สำเร็จหรือหมดเวลา ไม่มีผลเก่ามาแสดงแทน'; }
    } finally { clearTimeout(timer); }
  }
  window.NexusCopilotEvidence = Object.freeze({
    selected: () => selected,
    select(uid) { if (!validUid(uid)) return; clear(); selected=uid;
      if (location.hash === '#copilot') mount(); else location.hash='copilot'; },
    mount,
  });
  window.addEventListener('hashchange', () => { if (location.hash !== '#copilot') { clear(); selected=''; } });
})();
