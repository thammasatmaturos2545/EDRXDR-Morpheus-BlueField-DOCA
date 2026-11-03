(() => {
  'use strict';
  let active = null, generation = 0;
  const make = (tag, text, cls) => { const node = document.createElement(tag); if (text !== undefined) node.textContent = String(text); if (cls) node.className = cls; return node; };
  const finite = n => typeof n === 'number' && Number.isFinite(n) && n >= 0;
  function mount() {
    active?.abort(); const token = ++generation;
    const root = document.getElementById('dfp-diagnostic-root'); if (!root) return;
    root.replaceChildren();
    root.append(make('h1', 'DFP Diagnostic · Agent003'));
    root.append(make('p', 'Frozen CPU result · Offline diagnostic · ยังไม่ใช่ Live detection · Automated response OFF', 'notice warn'));
    root.append(make('p', 'ข้อมูลใหม่หลังชุดฝึก · ยังไม่ผ่าน quality acceptance และยังไม่ได้แทน BERT'));
    const reload = make('button', 'โหลดผลอีกครั้ง', 'button'); reload.type = 'button';
    const status = make('p', 'กำลังตรวจสิทธิ์และอ่านผล DFP…'); status.setAttribute('role', 'status');
    const detail = make('div'); root.append(reload, status, detail);
    let request = 0;
    const current = id => generation === token && request === id && root.isConnected &&
      document.getElementById('dfp-diagnostic-root') === root && location.hash === '#dfpdiagnostic';
    async function load() {
      active?.abort(); const controller = new AbortController(); active = controller; const id = ++request;
      detail.replaceChildren(); status.replaceChildren(); status.textContent = 'กำลังอ่านผล DFP…'; reload.disabled = true;
      const timer = setTimeout(() => controller.abort(), 10000);
      try {
        const response = await fetch('/api/nexus/v1/dfp-diagnostic', {
          method: 'GET', credentials: 'same-origin', cache: 'no-store', redirect: 'error', signal: controller.signal
        });
        if (!current(id)) return;
        if (response.status === 401) {
          status.textContent = 'ต้องเข้าสู่ระบบเพื่ออ่านผล DFP ';
          const link = make('a', 'Sign in'); link.href = '/api/nexus/v1/dfp-diagnostic'; status.append(link); return;
        }
        if (!response.ok) throw new Error();
        const data = await response.json(); if (!current(id)) return;
        if (!data || data.schema_version !== 'wazuh-dfp-diagnostic-bundle-1' || data.processing_mode !== 'offline_frozen_cpu_diagnostic' ||
          data.source_type !== 'frozen_archive_window_scores' || data.agent_id !== '003' || data.read_complete !== true ||
          data.model_name !== 'EDRXDR-ARCHIVE-CPU-PROTOTYPE' || data.model_version !== '1' ||
          data.model_sha256 !== 'ecacecb3128f9ac6987315e2a1861fb02ac873f9fc42ddc11798a9fc0c25157e' ||
          data.source_capture_sha256 !== '6e8478a917eebe277e725b746c08b481f34f4b805f7a7d6e24a096ed1c68510f' ||
          !/^[0-9a-f]{64}$/.test(data.artifact_sha256) || data.source_coverage_accepted !== false ||
          data.quality_metrics_evaluated !== false || data.production_ready !== false || data.automated_response_allowed !== false ||
          data.live_deployed !== false || data.bert_replaced !== false || data.threshold_selected !== false ||
          data.score_semantics !== 'mean_squared_reconstruction_error_transformed_numeric_features' ||
          data.total !== 12 || data.record_total !== 845 || data.nominal_interior_windows !== 10 || data.boundary_windows !== 2 ||
          !Array.isArray(data.observations) || data.observations.length !== 12) throw new Error();
        const ids = new Set(), fragment = document.createDocumentFragment(); let sum = 0, interior = 0, previous = -Infinity;
        const section = make('section', undefined, 'panel'); section.style.padding = '16px'; section.style.marginTop = '16px';
        section.append(make('h2', 'ผลโมเดลบนข้อมูลใหม่'));
        section.append(make('p', '845 records · 12 windows · 10 อยู่เต็มช่วงสังเกต · 2 ทับขอบรอบ'));
        section.append(make('p', 'คะแนนเป็นค่าเฉลี่ย squared reconstruction error หลังแปลง features ไม่ใช่ probability, z-score หรือ severity'));
        section.append(make('p', 'Coverage ยังไม่ยืนยัน · ไม่มี alert threshold · agent ID ยังไม่ใช่หลักฐานยืนยันตัวเครื่องทางกายภาพ'));
        const table = make('table'), head = make('thead'), hr = make('tr');
        for (const label of ['เวลา window (UTC)', 'Records', 'Reconstruction score', 'ช่วงข้อมูล', 'Syscollector records']) hr.append(make('th', label));
        head.append(hr); const body = make('tbody'); table.append(head, body);
        for (const item of data.observations) {
          const time = Date.parse(item?.window_start_utc);
          if (!item || !/^[0-9a-f]{64}$/.test(item.observation_id) || ids.has(item.observation_id) ||
            typeof item.window_start_utc !== 'string' || !/^\d{4}-\d\d-\d\dT\d\d:\d\d:00\+00:00$/.test(item.window_start_utc) ||
            !Number.isFinite(time) || time % 300000 !== 0 || time <= previous ||
            !Number.isSafeInteger(item.record_count) || item.record_count <= 0 || !finite(item.reconstruction_score) ||
            typeof item.nominally_inside_observation_interval !== 'boolean' || item.coverage_status !== 'unknown' || item.window_complete !== false ||
            !Number.isSafeInteger(item.syscollector_record_count) || item.syscollector_record_count < 0 || item.syscollector_record_count > item.record_count) throw new Error();
          ids.add(item.observation_id); previous = time; sum += item.record_count; interior += Number(item.nominally_inside_observation_interval);
          const tr = make('tr');
          for (const value of [item.window_start_utc, item.record_count, item.reconstruction_score,
            item.nominally_inside_observation_interval ? 'เต็มช่วงเวลา · coverage unknown' : 'ทับขอบรอบ · coverage unknown', item.syscollector_record_count]) tr.append(make('td', value));
          body.append(tr);
        }
        if (sum !== 845 || interior !== 10) throw new Error();
        const wrapper = make('div', undefined, 'table-wrapper'); wrapper.append(table); section.append(wrapper);
        section.append(make('p', 'Syscollector เป็นบริบทกิจกรรม ไม่ใช่ป้ายว่าโจมตี คะแนนสูงอย่างเดียวไม่ยืนยันภัย'));
        fragment.append(section);
        const proof = make('details'), summary = make('summary', 'หลักฐานและรุ่นโมเดล'); proof.append(summary);
        for (const [label, value] of [['Model SHA256', data.model_sha256], ['Capture SHA256', data.source_capture_sha256], ['Bundle SHA256', data.artifact_sha256]]) {
          const p = make('p', label + ': ' + value, 'mono'); p.style.overflowWrap = 'anywhere'; proof.append(p);
        }
        fragment.append(proof); detail.replaceChildren(fragment);
        status.textContent = 'อ่านผลครบ 12 windows · ไม่มีการเรียกโมเดลใหม่จากหน้านี้';
      } catch {
        if (current(id)) { detail.replaceChildren(); status.textContent = 'ผล DFP ปิดอยู่ ไม่พร้อมใช้งาน หรือไม่ผ่านการตรวจ ไม่มีผลเก่ามาแสดงแทน'; }
      } finally { clearTimeout(timer); if (current(id)) reload.disabled = false; }
    }
    reload.onclick = load; load();
  }
  window.addEventListener('hashchange', () => { active?.abort(); generation++; });
  window.NexusDfpDiagnostic = Object.freeze({ mount });
})();
