"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import type { parseDemo, parseWorker } from "@/lib/demo";
type Data = ReturnType<typeof parseDemo> & { fetched_at: string; worker: ReturnType<typeof parseWorker> };
const when = (v: unknown) => typeof v === "string" ? new Date(v).toLocaleString("th-TH", { timeZone: "Asia/Bangkok" }) : "—";
export default function Demo() {
  const [run, setRun] = useState("");
  const [active, setActive] = useState(true);
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState("");
  const [seen, setSeen] = useState<Record<string, string>>({});
  useEffect(() => { setRun(new URL(window.location.href).searchParams.get("run") ?? ""); }, []);
  useEffect(() => {
    if (!run || !active) return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    const controller = new AbortController();
    async function poll() {
      try {
        const reply = await fetch(`/api/demo?run=${encodeURIComponent(run)}`, { cache: "no-store", signal: AbortSignal.any([controller.signal, AbortSignal.timeout(12000)]) });
        if (!reply.ok) throw new Error("Unavailable");
        const value = await reply.json();
        if (value.mode !== "bounded_severity_demo" || value.run !== run || !Array.isArray(value.events)) throw new Error("Invalid response");
        if (stopped) return;
        setData(value); setError("");
        const now = new Date().toISOString();
        setSeen(old => Object.fromEntries(value.events.map((e: { id: string }) => [e.id, old[e.id] ?? now])));
      } catch {
        if (!stopped) { setData(null); setError("อ่านข้อมูลไม่ได้ / unavailable — ไม่แสดงค่าค้างเป็นข้อมูลสด"); }
      } finally { if (!stopped) timer = setTimeout(poll, 3000); }
    }
    void poll();
    return () => { stopped = true; controller.abort(); clearTimeout(timer); };
  }, [run, active]);
  const age = data ? Date.parse(data.fetched_at) - Date.parse(data.worker.observed_at_utc) : null;
  const stale = age === null || !Number.isFinite(age) || age < -5000 || age > 30000;
  const historical = data?.worker.phase === "stopped";
  return <main style={{ padding: 28, maxWidth: 1500, margin: "auto" }}>
    <Link href="/">← Overview</Link><h1>Severity flow demo</h1>
    <p>Wazuh → Kafka → Morpheus GPU Severity → Kafka → OpenSearch · bounded microbatch · automated response OFF</p>
    <p>Run: <code>{run || "ใส่ ?run=ชื่อรอบจาก worker"}</code></p>
    <button onClick={() => setActive(v => !v)}>{active ? "หยุดอ่านอัตโนมัติ" : "อ่านอัตโนมัติต่อ"}</button>
    <p role="status">{error || (!data ? "ยังไม่มีข้อมูลที่อ่านได้ —" : `${active ? "Polling ทุก 3 วินาทีหลัง request จบ" : "หยุด polling / ข้อมูลค้าง"} · API ${when(data.fetched_at)}`)}</p>
    {data && <>
      <section aria-label="สถานะรอบ" style={{ padding: 16, border: "1px solid #64748b", borderRadius: 8, marginTop: 16 }}>
        <h2>{historical ? "ผลย้อนหลัง — worker รายงานว่าหยุดแล้ว" : !active ? "พักการอ่าน — ไม่ยืนยันสถานะปัจจุบัน" : stale ? "สถานะยังยืนยันไม่ได้ — heartbeat ไม่สด" : "พบ heartbeat ล่าสุด ณ เวลา API"}</h2>
        <p>{historical ? "กำลังแสดงผลที่บันทึกไว้ การอ่านอัตโนมัติไม่ได้เริ่มประมวลผลใหม่ สถานะ worker ไม่ใช่หลักฐาน container exit" : "Heartbeat บอกการรายงานสถานะ ไม่ยืนยันว่าโมเดลกำลังประมวลผลต่อเนื่อง ตรวจรายการผลและเวลา Scored ประกอบ"}</p>
        <p>Worker: {data.worker.name} · {data.worker.phase}</p>
      </section>
      <p>จุดเริ่มรับเหตุการณ์: {when(data.worker.boundary_recorded_at_utc)} · heartbeat: {when(data.worker.observed_at_utc)}</p>
      <p>Session counters: captured {data.worker.session_counts.captured} / scored {data.worker.session_counts.scored} / indexed {data.worker.session_counts.indexed} · นับการประมวลผล อาจรวม retry</p>
      <p>Kafka lag ที่ worker รายงานล่าสุด: capture {data.worker.queue_lag.capture ?? "unknown"} / score {data.worker.queue_lag.score ?? "unknown"} / index {data.worker.queue_lag.index ?? "unknown"} · ไม่ใช่การตรวจ broker ณ ตอนเปิดหน้า</p>
      <p>เอกสารใน run: {data.total} · แสดงล่าสุด {data.shown} รายการจากหน้าต่าง 20 รายการ · Behavioral ไม่ได้รันใน worker นี้</p>
      <div style={{ overflowX: "auto" }}><table style={{ width: "100%", borderCollapse: "collapse" }}><thead><tr>{["Occurrence / hash", "Wazuh severity", "AI score / threshold", "Model", "เวลา / latency"].map(x => <th key={x} style={{ textAlign: "left", padding: 10 }}>{x}</th>)}</tr></thead>
      <tbody>{data.events.map(event => { const r = event.result; const source = r.source as Record<string, unknown>; return <tr key={event.id}>
        <td style={{ padding: 10, maxWidth: 280, overflowWrap: "anywhere" }}>UID {String(r.event_uid)}<br/>SHA256 {String(r.raw_sha256)}<br/>{String(source.topic)}:{String(source.partition)}:{String(source.offset)}</td>
        <td>Rule {String(r.wazuh_rule_id)}<br/>Level {r.wazuh_rule_level === null ? "unknown" : String(r.wazuh_rule_level)}</td>
        <td>{String(r.high_severity_score)} / {String(r.threshold)}<br/>{String(r.predicted_label)}</td><td style={{ maxWidth: 240, overflowWrap: "anywhere" }}>{String(r.model_name)}</td>
        <td>Captured {when(r.captured_at_utc)}<br/>Scored {when(r.scored_at_utc)}<br/>Index request เริ่ม {when(event.index_request_started_at)} (ไม่ใช่ ACK)<br/>Capture → score: {event.capture_to_score_ms.toFixed(1)} ms (รวมการรอ ไม่ใช่เวลา inference ล้วน)<br/>หน้านี้พบรายการเมื่อ {when(seen[event.id])} (เวลาเครื่องผู้ดู)<br/>เวลาเปิดดูไม่ใช้คำนวณ latency ของ pipeline</td>
      </tr>; })}</tbody></table></div>
    </>}
    <p>Source event time: unknown ในมุมมองนี้ · เวลาที่ browser พบไม่ใช่เวลาเกิดเหตุการณ์ · AI score ไม่ใช่ความน่าจะเป็นการโจมตี · production_ready=false</p>
  </main>;
}
