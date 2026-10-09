import { isQualityEvidence, metricNames, type MetricName } from "../lib/model-quality";

const labels: Record<MetricName, string> = {
  precision: "Precision",
  recall: "Recall",
  f1: "F1",
  false_positive_rate: "False-positive rate",
};
function percent(value: number | null) {
  return value === null ? "N/A" : `${(value * 100).toFixed(2)}%`;
}
function gate(passed: boolean) {
  return <span className={passed ? "online" : "error"}>{passed ? "PASS" : "FAIL"}</span>;
}

export default function ModelQuality({ data }: { data: unknown }) {
  if (!isQualityEvidence(data)) {
    return <div className="quality"><h3>ยังไม่มีรายงานที่ยืนยันได้</h3>
      <p>รอข้อมูลประเมินจาก API · สถานะ production ยังยืนยันไม่ได้จากรายงาน</p>
      <p className="footnote">ผล replay ที่อ่านได้ไม่ใช้แทนผลประเมินคุณภาพโมเดล</p>
    </div>;
  }
  const { quality, parity, source, run_id } = data;
  const issue = quality.per_rule["2901"];

  return <>
    <div className="quality-banner">
      <div><span className="eyebrow">DEVELOPMENT EVALUATION</span>
        <h3>{quality.production_ready ? "รายงานระบุ production_ready=true" : "โมเดลยังไม่พร้อม production"}</h3>
        <p>ประเมินความสอดคล้องกับ Wazuh severity บน development validation {quality.overall.n.toLocaleString()} รายการ
          · threshold {quality.threshold} · ไม่ใช่ผลทดสอบบน fresh holdout หรือความแม่นยำในการตรวจจับการโจมตี</p>
      </div>
      <div className="gate-summary">Numeric quality gate<br/>{gate(quality.development_numeric_gate_pass)}</div>
    </div>

    <div className="metrics quality-metrics">
      {metricNames.map(key => <div className="metric" key={key}>
        <span>{labels[key]}</span><strong>{percent(quality.overall[key])}</strong>
        <small>เกณฑ์เสนอ {key === "false_positive_rate" ? "≤" : "≥"} {percent(quality.proposed_limits[key])}
          {" · "}{gate(quality.proposed_gate_results[key])}</small>
      </div>)}
    </div>

    {issue && issue.fp > 0 && <div className="warning">
      <strong>Rule 2901: false positives {issue.fp.toLocaleString()} จาก low-severity {issue.fp + issue.tn} รายการ</strong>
      <p>FPR {percent(issue.false_positive_rate)} · ต้องรายงานแยกจากผลรวม ไม่ใช้ผล integration PASS เป็นเหตุอนุมัติโมเดล</p>
    </div>}

    <div className="quality-grid">
      <div className="quality"><h3>Offline Integration</h3>
        <dl className="evidence-list">
          <div><dt>Morpheus / Hugging Face parity</dt><dd className={parity.status === "PASS" ? "online" : "error"}>{parity.status}</dd></div>
          <div><dt>Inputs compared</dt><dd>{parity.compared_rows.toLocaleString()} / {parity.rows.toLocaleString()}</dd></div>
          <div><dt>Maximum absolute score error</dt><dd>{parity.max_absolute_score_error}</dd></div>
          <div><dt>Raw reconstruction</dt><dd>{parity.raw_event_check.status} · {parity.raw_event_check.reconstructed_rows.toLocaleString()} rows</dd></div>
          <div><dt>Test / reserve used</dt><dd>{parity.held_out_data_used || parity.raw_event_check.held_out_data_used ? "Yes" : "No"}</dd></div>
        </dl>
        <p className="footnote">ยืนยันเฉพาะรอบ offline ที่ระบุ ไม่ยืนยัน live services หรือการไหลของข้อมูลในปัจจุบัน</p>
      </div>
      <div className="quality"><h3>Evaluation Scope</h3>
        <p className="mono">{parity.checkpoint}</p>
        <p>TP {quality.overall.tp} · FP {quality.overall.fp} · TN {quality.overall.tn} · FN {quality.overall.fn}</p>
        <p>Shadow authorization ในรายงาน: {quality.shadow_authorized ? "Yes" : "No"}</p>
        <ul className="limitations">{quality.limitations.map(item => <li key={item}>{item}</li>)}</ul>
        <p className="footnote">เกณฑ์ตัวเลขเป็นข้อเสนอสำหรับ development ไม่ใช่ SLA หรือคำอนุมัติ deploy; ข้อจำกัดเรื่อง coverage ยังต้องประเมินแยก</p>
      </div>
    </div>

    <h3 className="table-title">ผลแยกราย rule</h3>
    <div className="table-wrap"><table>
      <thead><tr>{["Wazuh rule", "N", "TP", "FP", "TN", "FN", "Precision", "Recall", "F1", "FPR"].map(label => <th key={label}>{label}</th>)}</tr></thead>
      <tbody>{Object.entries(quality.per_rule).map(([rule, result]) => <tr key={rule}>
        <td>{rule}</td><td>{result.n}</td><td>{result.tp}</td><td className={result.fp ? "amber" : undefined}>{result.fp}</td>
        <td>{result.tn}</td><td>{result.fn}</td>
        {metricNames.map(key => <td key={key}>{percent(result[key])}</td>)}
      </tr>)}</tbody>
    </table></div>
    <p className="footnote">N/A หมายถึงรายงานไม่มีค่าที่คำนวณได้ ไม่แทนด้วย 0 หรือคะแนนผ่าน</p>

    <details className="report-source"><summary>แหล่งที่มาและตัวระบุรายงาน</summary>
      <p>Run: <span className="mono">{run_id}</span></p>
      <p>อ่านผ่าน <a href="/api/model-quality" target="_blank" rel="noreferrer">Model Quality API ↗</a> จากไฟล์รายงานบนเซิร์ฟเวอร์ ไม่ได้ประเมินโมเดลใหม่เมื่อเปิดหน้าเว็บ</p>
      <dl className="hash-list">
        <dt>Quality report SHA-256</dt><dd>{source.quality_sha256}</dd>
        <dt>Parity report SHA-256</dt><dd>{source.parity_sha256}</dd>
        <dt>Model weights SHA-256 (from report)</dt><dd>{parity.checkpoint_weights_sha256}</dd>
        <dt>Dataset manifest SHA-256 (from report)</dt><dd>{parity.dataset_manifest_sha256}</dd>
      </dl>
      <p className="footnote">Hash ของรายงานระบุไฟล์ที่อ่าน ส่วน weights/dataset hashes เป็นข้อมูลอ้างอิงจากรายงาน ไม่ใช่การตรวจ weights ที่กำลังใช้งานอยู่</p>
    </details>
  </>;
}
