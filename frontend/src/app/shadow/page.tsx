"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import type { Doc, Pair, joinShadow } from "@/lib/shadow";
import BluefieldShadow from "./bluefield-shadow";

type Result = ReturnType<typeof joinShadow> & { fetched_at: string };
const text = (v: unknown) => v === null || v === undefined ? "—" : String(v);
const time = (v: unknown) => typeof v === "string" ? new Date(v).toLocaleString("th-TH", { timeZone: "Asia/Bangkok" }) : "—";
const labels = { matched: "คู่ตรงกัน / hash ตรง", conflict: "ข้อมูลคู่ขัดแย้ง", severity_only: "ขาด Behavioral", behavioral_only: "ขาด Severity" };

export default function ShadowPage() {
  const [data, setData] = useState<Result | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [refresh, setRefresh] = useState(0);
  const [filter, setFilter] = useState("all");
  useEffect(() => {
    const controller = new AbortController();
    async function read() {
      setLoading(true); setError(""); setData(null);
      try {
        const response = await fetch("/api/shadow/events", { cache: "no-store", signal: AbortSignal.any([controller.signal, AbortSignal.timeout(15000)]) });
        const body = await response.json();
        if (!response.ok) throw new Error(body.error || "อ่านข้อมูลไม่สำเร็จ");
        if (!body || body.mode !== "shadow" || !Array.isArray(body.events) || !body.counts || typeof body.fetched_at !== "string") throw new Error("รูปแบบข้อมูล Shadow ไม่ถูกต้อง");
        if (!controller.signal.aborted) setData(body);
      } catch (e) { if (!controller.signal.aborted) setError(e instanceof Error ? e.message : "อ่านข้อมูลไม่สำเร็จ"); }
      finally { if (!controller.signal.aborted) setLoading(false); }
    }
    void read(); return () => controller.abort();
  }, [refresh]);
  const rows = data?.events.filter(e => filter === "all" || (filter === "candidate" ? e.severity?.false_positive_candidate === true : filter === "not_scored" ? e.behavioral?.ae_scored === false : e.status !== "matched")) ?? [];
  const metric = (label: string, value: unknown, note: string) => <div className="metric"><span>{label}</span><strong>{data ? text(value) : "—"}</strong><small>{note}</small></div>;
  const c = data?.counts;
  return <main className="dashboard">
    <header className="topbar"><div><div className="eyebrow">EDRXDR / SHADOW PILOT</div><h1>Shadow Results</h1><p>ผลจริงจาก batch ที่บันทึกไว้ · ไม่ใช่การตรวจจับสดต่อเนื่อง</p></div><button disabled={loading} onClick={() => setRefresh(n => n+1)}>{loading ? "กำลังอ่าน…" : "อ่านผลล่าสุด"}</button></header>
    <nav><Link href="/">Dashboard</Link><Link href="/replay">Replay</Link><Link href="/shadow" aria-current="page">Shadow</Link></nav>
    <div className="warning">ต้นแบบเพื่อการประเมิน · Automated response OFF<p>Severity ประมาณระดับ Wazuh ไม่ใช่โอกาสถูกโจมตี · Behavioral novelty ไม่ยืนยันว่าเป็นภัย · ไม่มีคะแนน AE ไม่ได้แปลว่าปลอดภัย</p></div>
    <p aria-live="polite">{loading ? "กำลังอ่านทั้งสอง index…" : error ? <span role="alert" className="error">{error}</span> : `อ่านข้อมูลเมื่อ ${time(data?.fetched_at)} (เวลาไทย) — ไม่ใช่เวลาที่เกิดเหตุการณ์`}</p>
    <div className="metrics">
      {metric("Severity / Behavioral", c ? `${c.severity} / ${c.behavioral}` : null, "จำนวนเอกสารทั้งหมดที่อ่านครบจากแต่ละ index")}
      {metric("จับคู่ตรงกัน", c?.matched, "ตรวจ occurrence และ raw hash; ไม่ใช่ accuracy")}
      {metric("ขาดคู่ / ขัดแย้ง", c ? `${c.unmatched} / ${c.conflicts}` : null, "ยังไม่ถือว่าเป็นคู่ผลที่ยืนยันแล้ว")}
      {metric("False-positive candidates", c?.candidates, "โมเดลทำนายสูง แต่ Wazuh level < 7; ยังไม่ยืนยัน FP")}
      {metric("AE-scored / Behavioral", c ? `${c.ae_scored} / ${c.behavioral}` : null, "coverage ของ autoencoder ในผลชุดนี้")}
      {metric("Semantic novelty", c?.novelty, "ความใหม่เทียบข้อมูลฝึก ไม่ใช่จำนวนการโจมตี")}
    </div>
    <section><h2>เหตุการณ์และผลสองโมเดล</h2><p>แยกเหตุการณ์ด้วย UID + cluster/topic/partition/offset · เวลาที่แสดงในตารางคือเวลาคัดลอกเข้า Shadow</p>
      <label>แสดง: <select value={filter} onChange={e => setFilter(e.target.value)} style={{background: "#152236", color: "#e3eaf5", padding: 10, marginBottom: 16}}><option value="all">ทั้งหมด</option><option value="candidate">Severity candidates</option><option value="not_scored">ยังไม่ได้คะแนน AE</option><option value="unmatched">ขาดคู่ / ขัดแย้ง</option></select></label>
      {!loading && !error && rows.length === 0 && <p>ไม่พบรายการในตัวกรองนี้</p>}
      <div className="table-wrap"><table><thead><tr><th>คัดลอกเมื่อ</th><th>Rule / Wazuh level</th><th>Severity</th><th>Behavioral</th><th>การจับคู่ / หลักฐาน</th></tr></thead><tbody>{rows.map(row => <EventRow key={row.key} row={row}/>)}</tbody></table></div>
    </section><BluefieldShadow /><footer>อ่านจาก Shadow indexes เท่านั้น · สูงสุด 500 เอกสารต่อ index; เกินขอบเขตจะแจ้งข้อผิดพลาด · ข้อมูลสอง index อาจเปลี่ยนระหว่างการอ่าน หากกำลังรัน batch ให้ตรวจซ้ำหลังจบ</footer>
  </main>;
}

function EventRow({ row }: { row: Pair }) {
  const s = row.severity, b = row.behavioral, d = (s ?? b) as Doc;
  return <tr><td>{time(d.captured_at_utc)}</td><td>{text(d.wazuh_rule_id)} / {text(d.wazuh_rule_level)}</td>
    <td>{s ? <>{text(s.predicted_label)}<br/><strong>{Number(s.high_severity_score).toFixed(4)}</strong><small>threshold {text(s.threshold)}</small>{s.false_positive_candidate === true && <span className="amber">Weak-label FP candidate</span>}</> : "ไม่มีผล Severity"}</td>
    <td>{b ? <>{text(b.analysis_state)}<small>{b.ae_scored ? `AE ratio: ${Number(b.ae_ratio).toFixed(3)}` : "ไม่มีคะแนน AE — ไม่ใช่ผลปลอดภัย"}</small><small>Novelty: {b.semantic_novelty ? "พบ" : "ไม่พบ"}</small></> : "ไม่มีผล Behavioral"}</td>
    <td><span className={row.status === "matched" ? "online" : "amber"}>{labels[row.status]}</span><details><summary style={{cursor:"pointer", marginTop:8}}>ดูข้อมูลอ้างอิง</summary><small className="mono">UID: {text(d.event_uid)}</small><small className="mono">Source: {JSON.stringify(d.source)}</small><small className="mono">Severity hash: {text(s?.raw_sha256)}</small><small>Behavioral rule / level: {text(b?.wazuh_rule_id)} / {text(b?.wazuh_rule_level)}</small><small>Behavioral captured: {time(b?.captured_at_utc)}</small><small className="mono">Behavioral hash: {text(b?.raw_sha256)}</small><small>Severity model: {text(s?.model_name)}</small><small>Behavioral model: {text(b?.model_version)}</small><small>Severity scored: {time(s?.scored_at_utc)}</small><small>Behavioral scored: {time(b?.scored_at_utc)}</small></details></td></tr>;
}
