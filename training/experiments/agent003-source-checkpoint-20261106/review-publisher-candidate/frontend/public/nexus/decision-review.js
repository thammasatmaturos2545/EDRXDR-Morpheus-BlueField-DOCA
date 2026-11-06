'use strict';
(() => {
  const status = document.getElementById('status'), list = document.getElementById('list');
  const auth = document.getElementById('auth'), filter = document.getElementById('filter');
  const pending = new Map();
  const labels = { investigating: 'รับเรื่องตรวจสอบ', agree_recommendation: 'เห็นด้วยกับคำแนะนำ', no_action: 'ไม่ดำเนินการ' };
  const modes = { shadow: 'เฝ้าดู / ยังไม่ตอบสนอง', replay: 'ข้อมูลเล่นซ้ำ', 'controlled-test': 'การทดสอบที่ควบคุม' };
  const scoreNames = { 'reconstruction-error': 'คะแนนความผิดปกติ (ไม่ใช่ความน่าจะเป็น)',
    'rule-count': 'จำนวนตามกฎตรวจจับ', 'classifier-score': 'คะแนนจากตัวจำแนก' };
  const coverageNames = { verified: 'ตรวจสอบความครอบคลุมแล้ว', incomplete: 'ข้อมูลไม่ครบ', unknown: 'ยังไม่ยืนยันความครอบคลุม' };
  let report = null, loading = false;
  function el(tag, text, cls) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = String(text);
    if (cls) node.className = cls;
    return node;
  }
  function lines(parent, title, values) {
    parent.append(el('h3', title));
    const ul = el('ul'); values.forEach(text => ul.append(el('li', text))); parent.append(ul);
  }
  function date(value) { return new Date(value).toLocaleString('th-TH', { timeZone: 'Asia/Bangkok' }); }
  function requestId() {
    // getRandomValues also works on the existing HTTP lab origin; randomUUID may not.
    const bytes = crypto.getRandomValues(new Uint8Array(16));
    bytes[6] = (bytes[6] & 15) | 64; bytes[8] = (bytes[8] & 63) | 128;
    const hex = Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join('');
    return [hex.slice(0, 8), hex.slice(8, 12), hex.slice(12, 16), hex.slice(16, 20), hex.slice(20)].join('-');
  }
  function render() {
    list.replaceChildren();
    if (!report) return;
    const rows = report.items.filter(row => filter.value === 'all' || row.pipeline === filter.value);
    if (!rows.length) { list.append(el('p', 'ยังไม่มีรายการในขอบเขตนี้ ไม่มีการสร้างข้อมูลตัวอย่างแทน')); return; }
    rows.forEach(row => {
      const card = el('article');
      const badges = el('div', undefined, 'badges');
      badges.append(el('span', modes[row.source_mode], 'badge'),
        el('span', row.validation_status === 'validated' ? 'ผ่านการประเมินตามขอบเขตที่ระบุ' : 'ผลทดลอง / ยังไม่รับรองคุณภาพ', 'badge experimental'));
      card.append(badges, el('h2', (row.pipeline === 'dfp' ? 'DFP' : 'พฤติกรรมไฟล์') + ' · Agent ' + row.endpoint_id));
      const facts = el('div', undefined, 'facts');
      for (const [title, value] of [['เวลาเหตุการณ์', date(row.event_time)], ['เวลาตรวจพบ', date(row.detected_at)],
        ['ตัวตรวจ', row.detector_id + ' / ' + row.detector_version], ['ความครบถ้วนของข้อมูล', coverageNames[row.coverage_status]],
        [scoreNames[row.score_semantics], row.score === null ? 'ไม่มีคะแนน' : row.score]]) {
        const cell = el('p'); cell.append(el('small', title), el('span', value)); facts.append(cell);
      }
      card.append(facts); lines(card, 'สิ่งที่ตรวจพบ', row.findings); lines(card, 'ข้อจำกัด', row.limitations);
      const recommendation = el('div', undefined, 'recommendation');
      recommendation.append(el('h3', row.recommendation.action === 'investigate' ? 'คำแนะนำ: ตรวจสอบเพิ่มเติม' : 'คำแนะนำ: พิจารณาแยก endpoint ออกจากเครือข่าย'),
        el('p', row.recommendation.reason), el('small', 'ผู้ดูแลต้องพิจารณาและดำเนินการเอง ระบบนี้ไม่ส่งคำสั่ง'));
      card.append(recommendation);
      const evidence = el('details'); evidence.append(el('summary', 'หลักฐานอ้างอิงและรุ่นข้อมูล'),
        el('pre', JSON.stringify({ alert_id: row.alert_id, alert_revision: row.alert_revision,
          feature_contract: row.feature_contract, evidence_refs: row.evidence_refs }, null, 2)));
      card.append(evidence);
      const decision = el('div', undefined, 'decision');
      decision.append(el('h3', 'บันทึกการตัดสินใจ'));
      const actionLabel = el('label', 'การตัดสินใจ');
      const action = el('select');
      Object.entries(labels).forEach(([value, label]) => { const option = el('option', label); option.value = value; action.append(option); });
      actionLabel.append(action);
      const reasonLabel = el('label', 'เหตุผล (ไม่ใส่รหัสผ่านหรือข้อมูลส่วนตัว)');
      const reason = el('textarea'); reason.maxLength = 500; reasonLabel.append(reason);
      const save = el('button', 'บันทึกความเห็น', 'save'); save.type = 'button';
      const message = el('p', '', 'message'); message.setAttribute('role', 'status');
      const unresolved = pending.get(row.alert_id);
      if (unresolved) {
        action.value = unresolved.action; reason.value = unresolved.reason;
        action.disabled = reason.disabled = true; save.textContent = 'ลองส่งรายการเดิมอีกครั้ง';
        message.textContent = 'รายการก่อนหน้ายังไม่ทราบผล ลองส่งรายการเดิมเพื่อป้องกันบันทึกซ้ำ';
      }
      if (report.principal.role !== 'reviewer') {
        action.disabled = reason.disabled = save.disabled = true;
        message.textContent = 'บัญชีนี้ดูข้อมูลได้ แต่ไม่มีสิทธิ์บันทึกการตัดสินใจ';
      }
      save.addEventListener('click', async () => {
        if (save.disabled) return;
        if (!pending.has(row.alert_id)) {
          const note = reason.value.trim();
          if (!note) { message.textContent = 'กรุณาระบุเหตุผล'; reason.focus(); return; }
          pending.set(row.alert_id, { request_id: requestId(), alert_id: row.alert_id,
            alert_revision: row.alert_revision, expected_seq: row.latest_seq, action: action.value, reason: note });
        }
        save.disabled = action.disabled = reason.disabled = true;
        message.textContent = 'กำลังบันทึก…';
        const body = pending.get(row.alert_id);
        try {
          const response = await fetch('/api/nexus/v1/decisions', { method: 'POST', credentials: 'same-origin',
            cache: 'no-store', redirect: 'error', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body), signal: AbortSignal.timeout(15000) });
          if (response.status === 409) {
            pending.delete(row.alert_id); await load();
            status.textContent = 'ข้อมูลหรือคำตัดสินเปลี่ยนแล้ว กรุณาทบทวนรายการล่าสุดก่อนบันทึกอีกครั้ง'; return;
          }
          if (!response.ok) throw Error();
          const result = await response.json();
          if (result.response_executed !== false || result.decision?.request_id !== body.request_id ||
            result.decision?.alert_revision !== body.alert_revision) throw Error();
          pending.delete(row.alert_id); await load();
          if (report) status.textContent = 'บันทึกความเห็นแล้ว ไม่มีการส่งคำสั่งบล็อกหรือแยกเครื่อง';
        } catch {
          message.textContent = 'ยังยืนยันผลไม่ได้ กดลองส่งรายการเดิมอีกครั้ง ห้ามถือว่าบล็อกหรือแยกเครื่องแล้ว';
          save.textContent = 'ลองส่งรายการเดิมอีกครั้ง'; save.disabled = false;
        }
      });
      decision.append(actionLabel, reasonLabel, save, message); card.append(decision);
      if (row.retired === true) {
        action.disabled = reason.disabled = save.disabled = true;
        message.textContent = 'รายการเก่า อ่านประวัติเท่านั้น ไม่มีการรับคำตัดสินใหม่';
      }
      const history = el('details'); history.append(el('summary', 'ประวัติการตัดสินใจ (' + row.history.length + ')'));
      const entries = el('ol', undefined, 'history');
      row.history.forEach(record => {
        const entry = el('li'); entry.append(el('strong', labels[record.action]),
          el('p', record.reason), el('small', record.actor_ref + ' · ' + date(record.decided_at)));
        const reviewed = row.revision_evidence?.[record.alert_revision];
        entry.append(el('small', record.alert_revision === row.alert_revision
          ? 'คำตัดสินต่อข้อมูลรุ่นที่แสดง' : 'คำตัดสินต่อข้อมูลรุ่นก่อน'));
        const prior = el('details');
        prior.append(el('summary', 'หลักฐานและคำแนะนำ ณ วันที่ตัดสินใจ'));
        if (reviewed) {
          prior.append(el('pre', JSON.stringify({ alert_revision: record.alert_revision,
            detector_id: reviewed.detector_id, detector_version: reviewed.detector_version,
            feature_contract: reviewed.feature_contract, findings: reviewed.findings,
            limitations: reviewed.limitations, evidence_refs: reviewed.evidence_refs,
            recommendation: reviewed.recommendation }, null, 2)));
        } else {
          prior.append(el('p', 'ยังไม่มีสำเนาหลักฐานรุ่นนี้ อย่านำคำตัดสินเดิมไปอ้างกับคำแนะนำใหม่'));
        }
        entry.append(prior); entries.append(entry);
      });
      if (!row.history.length) entries.append(el('li', 'ยังไม่มีการตัดสินใจ'));
      history.append(entries); card.append(history); list.append(card);
    });
  }
  async function load() {
    if (loading) return;
    loading = true; report = null; list.replaceChildren(); auth.hidden = true;
    status.textContent = 'กำลังตรวจสิทธิ์และโหลดรายการ…';
    try {
      const response = await fetch('/api/nexus/v1/decisions', { credentials: 'same-origin',
        cache: 'no-store', redirect: 'error', signal: AbortSignal.timeout(15000) });
      if (response.status === 401) { auth.hidden = false; status.textContent = 'ต้องยืนยันตัวตนด้วยบัญชีผู้ทบทวน'; return; }
      if (response.status === 503) { status.textContent = 'ระบบทบทวนยังไม่เปิดใช้งาน หรือข้อมูลที่รับรองยังไม่พร้อม'; return; }
      if (!response.ok) throw Error();
      const data = await response.json();
      if (!['nexus-human-review-v1', 'nexus-human-review-v2'].includes(data.schema_version) || data.automated_response_allowed !== false ||
        data.response_execution_enabled !== false || !Array.isArray(data.items) || data.items.length > 20 ||
        !['viewer', 'reviewer'].includes(data.principal?.role)) throw Error();
      report = data; render();
      status.textContent = data.items.length + ' รายการ · ผู้ใช้ ' + data.principal.actor_ref + ' · ไม่มีการตอบสนองอัตโนมัติ';
    } catch { report = null; list.replaceChildren(); status.textContent = 'โหลดข้อมูลไม่สำเร็จ กรุณาลองใหม่ ไม่มีการสร้างผลตรวจทดแทน'; }
    finally { loading = false; }
  }
  filter.addEventListener('change', render);
  document.getElementById('reload').addEventListener('click', load);
  load();
})();
