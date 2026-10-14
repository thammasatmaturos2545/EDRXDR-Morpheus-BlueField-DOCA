"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { EventRow, Source, filterEvents, parseEvents, record, serviceState } from "../lib/soc";
import "./soc.css";

const date = (value: string | null) => value ? new Date(value).toLocaleString("th-TH", { hour12: false }) : "Unknown";
const show = (value: string | number | null) => value === null ? "Unknown" : String(value);
const endpoints = { wazuh: "/api/wazuh", ai: "/api/events" };
type Feed = { source: Source; rows: EventRow[] | null; received: string | null; error: boolean };

export default function Soc() {
  const [source, setSource] = useState<Source>("wazuh");
  const [feed, setFeed] = useState<Feed>({ source: "wazuh", rows: null, received: null, error: false });
  const [services, setServices] = useState<Record<string, unknown> | null>(null);
  const [query, setQuery] = useState(""); const [minimum, setMinimum] = useState(0); const [hours, setHours] = useState(0);
  const [selected, setSelected] = useState<EventRow | null>(null);
  const [revision, setRevision] = useState(0); const [paused, setPaused] = useState(false);
  const [now, setNow] = useState(0);
  useEffect(() => { const tick = () => setNow(Date.now()); tick(); const timer = setInterval(tick, 10000); return () => clearInterval(timer); }, []);
  useEffect(() => {
    if (paused) return;
    let active = true; let timer: ReturnType<typeof setTimeout> | undefined;
    const controller = new AbortController();
    async function load() {
      const options = { cache: "no-store" as const, signal: AbortSignal.any([controller.signal, AbortSignal.timeout(15000)]) };
      await Promise.all([
        (async () => { try {
          const response = await fetch(endpoints[source], options); if (!response.ok) throw new Error("Unavailable");
          const rows = parseEvents(await response.json(), source);
          if (active) setFeed({ source, rows, received: new Date().toISOString(), error: false });
        } catch { if (active) setFeed({ source, rows: null, received: null, error: true }); } })(),
        (async () => { try {
          const response = await fetch("/api/status", options); const data: unknown = await response.json();
          if (!response.ok || !record(data) || data.error) throw new Error("Unavailable");
          if (active) setServices(data);
        } catch { if (active) setServices(null); } })(),
      ]);
      if (active) timer = setTimeout(load, 15000);
    }
    void load(); return () => { active = false; controller.abort(); if (timer) clearTimeout(timer); };
  }, [source, revision, paused]);
  const rows = feed.source === source ? feed.rows : null;
  const filtered = rows ? filterEvents(rows, query, minimum, hours, now) : [];
  const latest = rows?.reduce<string | null>((last, row) => row.timestamp && (!last || Date.parse(row.timestamp) > Date.parse(last)) ? row.timestamp : last, null) ?? null;
  const age = latest && now ? Math.floor((now - Date.parse(latest)) / 60000) : null;
  const stale = feed.received && now - Date.parse(feed.received) > 45000;
  const stats = [
    ["เหตุการณ์ในชุดที่อ่านได้", rows === null ? "—" : rows.length, "สูงสุด 100 รายการ ไม่ใช่ยอดทั้งหมด"],
    ["Wazuh severity ≥ 7", rows === null ? "—" : rows.filter(e => e.level !== null && e.level >= 7).length, "เกณฑ์คัดกรอง ไม่ใช่การยืนยันภัย"],
    ["เครื่องที่ระบุชื่อได้", rows === null ? "—" : new Set(rows.map(e => e.host).filter(Boolean)).size, "เฉพาะชุดข้อมูลนี้ ไม่ใช่จำนวนเครื่องทั้งหมด"],
    ["รายการที่มี AI score", rows === null ? "—" : rows.filter(e => e.score !== null).length, source === "wazuh" ? "ยังไม่ได้จับคู่กับผล AI" : "ไม่รวมผล Demo / Replay / Shadow"],
  ];
  return <main className="soc">
    <header className="soc-head"><div><span className="soc-kicker">SECURITY OPERATIONS CENTER</span><h1>ภาพรวมเหตุการณ์</h1><p>ตรวจเหตุการณ์จากหลักฐานจริง แล้วเปิดรายละเอียดเพื่อวิเคราะห์ต่อ</p></div><span className="soc-scope">LIVE DATA SOURCES</span></header>
    <div className="soc-metrics">{stats.map(([label, value, note]) => <article key={label}><span>{label}</span><strong>{value}</strong><small>{note}</small></article>)}</div>
    <div className="soc-health"><div><span className="soc-kicker">DATA VISIBILITY</span><h2>ความสดและสถานะบริการ</h2><p>เวลาของ event ล่าสุด: {date(latest)}{age !== null && <strong> · {age < 0 ? "เวลาอยู่ในอนาคต — ตรวจ clock" : `${age} นาทีที่ผ่านมา`}</strong>}</p><small>การอ่าน API สำเร็จไม่ยืนยันว่ามีข้อมูลใหม่ · สถานะบริการไม่ยืนยัน event flow</small></div><div className="soc-services">{[["wazuhManager", "Wazuh"], ["bluefield", "BlueField"], ["doca", "DOCA"], ["morpheus", "Morpheus"]].map(([key, label]) => <div key={key}><span>{label}</span><b className={`soc-state-${paused || stale ? "unknown" : serviceState(services?.[key])}`}>{paused || stale ? "unknown" : serviceState(services?.[key])}</b></div>)}<Link href="/details#live">ดูบริการทั้งหมด →</Link></div></div>
    <section className="soc-events" aria-labelledby="events-title"><div className="soc-section-title"><div><span className="soc-kicker">EVENT EXPLORER</span><h2 id="events-title">รายการสำหรับวิเคราะห์</h2></div><div className="soc-actions"><button onClick={() => setPaused(!paused)}>{paused ? "อ่านอัตโนมัติต่อ" : "พักการอ่าน"}</button><button disabled={paused} onClick={() => setRevision(v => v + 1)}>อ่านล่าสุด</button></div></div>
    <div className="soc-tabs" role="group" aria-label="ชุดข้อมูล"><button aria-pressed={source === "wazuh"} onClick={() => { setSource("wazuh"); setSelected(null); }}>Wazuh alerts</button><button aria-pressed={source === "ai"} onClick={() => { setSource("ai"); setSelected(null); }}>Live AI evidence</button></div>
    <div className="soc-filters"><label>ค้นหาเครื่อง / IP / Rule / Event ID<input value={query} onChange={e => setQuery(e.target.value)} placeholder="ค้นหาในรายการที่โหลดแล้ว…" /></label><label>Wazuh severity<select value={minimum} onChange={e => setMinimum(Number(e.target.value))}><option value={0}>ทุกระดับ / Unknown</option><option value={7}>Level ≥ 7</option><option value={12}>Level ≥ 12</option></select></label><label>เวลาเหตุการณ์<select value={hours} onChange={e => setHours(Number(e.target.value))}><option value={0}>ทั้งหมดที่ API ส่งกลับ</option><option value={1}>1 ชั่วโมงล่าสุด</option><option value={24}>24 ชั่วโมงล่าสุด</option></select></label></div>
    <p className="soc-feed" aria-live="polite">{paused ? "หยุดอ่านอัตโนมัติ — ข้อมูลค้าง ณ ครั้งที่อ่านล่าสุด" : feed.source === source && feed.error ? "อ่านข้อมูลไม่ได้ — Unknown ไม่ได้หมายถึง Offline หรือไม่มีเหตุการณ์" : rows === null ? "กำลังอ่าน API — ยังไม่มีจำนวนที่ยืนยัน" : `${filtered.length} จาก ${rows.length} รายการในชุดนี้ · อ่าน API เมื่อ ${date(feed.received)}${stale ? " · ข้อมูลเก่า" : ""}`}</p>
    <div className="soc-table"><table><thead><tr>{["เวลาเหตุการณ์", "เครื่อง / เหตุการณ์", "Rule", "Wazuh severity", "AI score / class", "รายละเอียด"].map(s => <th key={s}>{s}</th>)}</tr></thead><tbody>{filtered.map(e => <tr key={e.key}><td>{date(e.timestamp)}</td><td><strong>{show(e.host)}</strong><small>{e.description || "API ไม่ได้ส่งคำอธิบาย"}</small></td><td>{show(e.rule)}</td><td><span className={e.level !== null && e.level >= 12 ? "soc-level high" : "soc-level"}>{e.level === null ? "Unknown" : `Level ${e.level}`}</span></td><td>{e.score === null ? "ไม่มีคะแนนที่จับคู่" : String(e.score)}<small>{e.label || "—"}</small></td><td><button onClick={() => setSelected(e)} aria-label={`รายละเอียด ${e.id || e.key}`}>วิเคราะห์ →</button></td></tr>)}</tbody></table></div>
    {rows !== null && filtered.length === 0 && <div className="soc-empty"><h3>{rows.length ? "ไม่พบรายการตรงตัวกรอง" : "API ส่งกลับโดยไม่มีรายการ"}</h3><p>ผลนี้ไม่ยืนยันว่าไม่มีภัยคุกคาม ลองตรวจช่วงเวลาและแหล่งข้อมูล</p></div>}
    <div className="soc-note">Wazuh severity แยกจาก AI score · คะแนน AI ไม่ใช่ความน่าจะเป็นของการโจมตี · ไม่สร้าง case หรือสถานะตรวจสอบจนกว่าจะมี backend รองรับ</div></section>
    <footer>ตัวกรองใช้เฉพาะชุดล่าสุดที่โหลดแล้ว ไม่ใช่การค้นหาประวัติทั้งหมด · อ่าน API ทุก 15 วินาที</footer>
    {selected && <aside className="soc-detail" aria-label="รายละเอียดเหตุการณ์"><div className="soc-section-title"><div><span className="soc-kicker">EVIDENCE INSPECTOR</span><h2>รายละเอียดเหตุการณ์</h2></div><button onClick={() => setSelected(null)}>ปิด</button></div><p>สำเนาจากรายการที่เลือก — ไม่จับคู่ข้อมูลจากคนละแหล่งโดยอัตโนมัติ</p><dl>{[["แหล่งข้อมูล", source === "wazuh" ? "Wazuh" : "Live AI"], ["เวลาเหตุการณ์", date(selected.timestamp)], ["เครื่อง", selected.host], ["คำอธิบาย", selected.description], ["Rule", selected.rule], ["Wazuh severity", selected.level], ["AI score", selected.score], ["AI class", selected.label], ["Engine", selected.engine], ["Source IP", selected.srcIp], ["Destination IP", selected.dstIp], ["Event ID จาก API", selected.id], ["Event UID", selected.uid], ["Raw SHA256", selected.hash]].map(([name, value]) => <div key={String(name)}><dt>{name}</dt><dd>{show(value)}</dd></div>)}</dl><p className="soc-note">ฟิลด์ที่ API ไม่ส่งจะแสดง Unknown · หน้านี้ไม่เปิด automated response</p></aside>}
  </main>;
}
