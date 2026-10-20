'use strict';
(() => {
  const status = document.getElementById('status'), list = document.getElementById('list');
  const filter = document.getElementById('filter'), auth = document.getElementById('auth');
  let report = null;
  function el(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = String(text);
    if (className) node.className = className;
    return node;
  }
  function render() {
    list.replaceChildren();
    if (!report) return;
    report.results.filter(r => filter.value === 'all' || r.event_uid === filter.value).forEach((row, i) => {
      const card = el('article');
      card.append(el('span', 'รอ Analyst ตรวจ', 'badge'), el('h2', 'เหตุการณ์ ' + (i + 1)), el('div', row.event_uid, 'uid'));
      card.append(el('p', row.draft.summary_th.text));
      const scores = el('div', undefined, 'scores');
      const wazuh = el('div'); wazuh.append(el('small', 'Wazuh level'), el('div', row.evidence.wazuh_level + ' / 15', 'score'));
      const ai = el('div'); ai.append(el('small', 'Morpheus AI · ' + row.evidence.ai_status),
        el('div', (row.evidence.ai_score * 100).toFixed(1) + ' / 100', 'score'));
      scores.append(wazuh, ai); card.append(scores);
      for (const [key, title] of [['facts','ข้อเท็จจริง'],['hypotheses','ข้อสันนิษฐาน'],['unknowns','สิ่งที่ยังไม่ทราบ'],['suggested_checks','ตรวจเพิ่มเติมโดย Analyst']]) {
        card.append(el('h3', title, 'section-title'));
        if (!row.draft[key].length) { card.append(el('small', 'ไม่มีรายการจากโมเดล')); continue; }
        const ul = el('ul');
        row.draft[key].forEach(claim => {
          const li = el('li'); li.append(el('span', claim.text), el('div', claim.evidence_uids.join(', '), 'uid')); ul.append(li);
        }); card.append(ul);
      }
      const details = el('details');
      details.append(el('summary', 'หลักฐานต้นทางและ UID citation'), el('pre', JSON.stringify(row.evidence, null, 2)));
      card.append(details); list.append(card);
    });
  }
  async function load() {
    report = null; list.replaceChildren(); auth.style.display = 'none';
    filter.replaceChildren(el('option', 'ทั้งหมด 8 รายการ')); filter.firstChild.value = 'all';
    status.textContent = 'กำลังตรวจสิทธิ์และโหลดผลสรุป…';
    try {
      const response = await fetch('/api/nexus/v1/copilot/review', {
        credentials: 'same-origin', cache: 'no-store', redirect: 'error', signal: AbortSignal.timeout(15000),
      });
      if (response.status === 401) { auth.style.display = 'block'; status.textContent = 'ต้องยืนยันตัวตนก่อนดูหลักฐาน'; return; }
      if (!response.ok) throw Error();
      const data = await response.json();
      if (data.saved_review_only !== true || data.automated_response_allowed !== false ||
        !Array.isArray(data.results) || data.results.length !== 8) throw Error();
      report = data;
      report.results.forEach(row => { const option = el('option', row.event_uid.slice(0, 16) + '…'); option.value = row.event_uid; filter.append(option); });
      status.textContent = 'Local gpt-oss-20b · 8 สรุปที่รอตรวจ · สร้างเมื่อ ' + report.generated_at +
        ' · evidence hash ' + report.input_evidence_hash.slice(0, 16) + '…';
      render();
    } catch { status.textContent = 'ผลสรุปไม่พร้อมใช้งานหรือไม่ผ่านการตรวจ กรุณาตรวจ candidate API'; }
  }
  filter.addEventListener('change', render);
  document.getElementById('reload').addEventListener('click', load);
  load();
})();
