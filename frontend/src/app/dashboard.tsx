"use client";
import Link from "next/link";
import ModelQuality from "./model-quality";
import { isQualityEvidence } from "../lib/model-quality";
import { useEffect, useState } from "react";
type Row = Record<string, unknown>;
type Feed = { data: Row | null; error: string; updated: string };
function object(v: unknown): v is Row { return !!v && typeof v === "object" && !Array.isArray(v); }
function text(v: unknown) { return typeof v === "string" || typeof v === "number" ? String(v) : "—"; }
function numeric(v: unknown): v is number { return typeof v === "number" && Number.isFinite(v); }
function level(v: unknown): v is number { return numeric(v) && Number.isInteger(v) && v >= 0 && v <= 15; }
function time(v: unknown) { return typeof v === "string" && Number.isFinite(Date.parse(v)) ? new Date(v).toLocaleString("th-TH") : "—"; }
function rows(f: Feed, key: string): Row[] { const v = f.data?.[key]; return Array.isArray(v) ? v.filter(object) : []; }
function state(v: unknown) { return v === true || v === "ready" || v === "online" ? "online" : v === false || v === "offline" ? "offline" : v === "waiting" ? "waiting" : "unknown"; }
function useFeed(url: string | null, key?: string) {
 const [feed, setFeed] = useState<Feed>({ data: null, error: "", updated: "" });
 const [refresh, setRefresh] = useState(0);
 useEffect(() => {
  if (!url) return;
  let active = true; let timer: ReturnType<typeof setTimeout>;
  const controller = new AbortController();
  async function load() {
   try {
    const response = await fetch(url!, { cache: "no-store", signal: AbortSignal.any([controller.signal, AbortSignal.timeout(20000)]) });
    const data: unknown = await response.json();
    if (!response.ok || !object(data) || data.error) throw new Error(object(data) && typeof data.error === "string" ? data.error : `API failed (${response.status})`);
    if (key && (!Array.isArray(data[key]) || !(data[key] as unknown[]).every(object))) throw new Error("รูปแบบข้อมูล API ไม่ถูกต้อง");
    if (url === "/api/model-quality" && !isQualityEvidence(data)) throw new Error("รูปแบบรายงาน Model Quality ไม่ถูกต้อง");
    if (active) setFeed({ data, error: "", updated: new Date().toISOString() });
   } catch (error) { if (active) setFeed(old => ({ ...old, error: error instanceof Error ? error.message : "อ่าน API ไม่สำเร็จ" })); }
   finally { if (active) timer = setTimeout(load, 15000); }
  }
  void load(); return () => { active = false; controller.abort(); clearTimeout(timer); };
 }, [url, key, refresh]);
 return { ...feed, reload: () => setRefresh(v => v + 1) };
}
function Notice({ feed }: { feed: Feed }) { return <p className="feed-note" aria-live="polite">{feed.error ? <span role="alert" className="error">{feed.error} · {feed.data ? "ข้อมูลด้านล่างเป็นข้อมูลเก่า" : "ยังไม่มีข้อมูลยืนยัน"}</span> : feed.data ? `อ่านสำเร็จล่าสุด ${time(feed.updated)}` : "กำลังอ่าน API…"}</p>; }
function Metric({ label, value, detail }: { label: string; value: unknown; detail: string }) { return <div className="metric"><span>{label}</span><strong>{text(value)}</strong><small>{detail}</small></div>; }
const services = [["wazuhAgent", "Wazuh Agent"], ["wazuhManager", "Wazuh Manager"], ["wazuhIndexer", "Wazuh Indexer"], ["wazuhDashboard", "Wazuh Dashboard"], ["wazuhForwarder", "Wazuh Forwarder"], ["bluefield", "BlueField-3"], ["doca", "DOCA"], ["kafka", "Kafka"], ["normalizer", "Normalizer"], ["morpheus", "Morpheus"], ["gpuFabric", "H100 Fabric"], ["indexer", "Indexer"], ["opensearch", "OpenSearch"]];
function objectValue(value: unknown): Record<string, unknown> | null {
  if (
    value === null ||
    typeof value !== "object" ||
    Array.isArray(value)
  ) {
    return null;
  }

  return value as Record<string, unknown>;
}

export default function Dashboard({ replayOnly = false }: { replayOnly?: boolean }) {
 const status = useFeed(replayOnly ? null : "/api/status");
 const wazuh = useFeed(replayOnly ? null : "/api/wazuh", "alerts");
 const live = useFeed(replayOnly ? null : "/api/events", "events");
 const replay = useFeed("/api/replay/events", "events");
 const quality = useFeed("/api/model-quality");
 const alerts = rows(wazuh, "alerts"); const events = rows(replay, "events");
 const liveEvents = rows(live, "events").filter(e => e.processing_mode === "live" && typeof e.analysis_engine === "string" && !/simulat|replay/i.test(e.analysis_engine));
 const comparable = events.filter(e => level(e.wazuh_rule_level) && ["high_severity", "low_severity"].includes(String(e.predicted_label)));
 const mismatches = comparable.filter(e => (Number(e.wazuh_rule_level) >= 7) !== (e.predicted_label === "high_severity"));
 return <main className="dashboard"><header className="topbar"><div><div className="eyebrow">EDRXDR / SECURITY OPERATIONS</div><h1>{replayOnly ? "Replay Results" : "Security Dashboard"}</h1><p>สถานะบริการสด ผล replay และคุณภาพโมเดล แยกตามหลักฐาน</p></div><button onClick={() => { status.reload(); wazuh.reload(); live.reload(); replay.reload(); quality.reload(); }}>อัปเดตข้อมูล</button></header>
 <nav><Link href="/">Dashboard</Link><a href={replayOnly ? "/#live" : "#live"}>Live Services</a><a href="#replay">Replay Results</a><a href="#quality">Model Quality</a><Link href="/replay">เปิด /replay ↗</Link><Link href="/shadow">Shadow Results</Link></nav>
 {!replayOnly && <section id="live"><div className="eyebrow">01 / LIVE</div><h2>Live Services</h2><p>Online = ตรวจพบบริการทำงาน · Offline = พบสถานะหยุด · Unknown = ตรวจยืนยันไม่ได้ · สถานะบริการไม่ยืนยัน event flow</p><Notice feed={status}/><div className="service-grid">{services.map(([key, label]) => { const s = state(status.error ? null : status.data?.[key]); return <div className="service" key={key}><span>{label}</span><strong className={`state ${s}`}>● {s}</strong></div>; })}</div>
 <div className="subsection"><h3>Wazuh Endpoint Alerts</h3><p>Severity จาก Wazuh โดยตรง แยกจาก AI score · จำนวนเฉพาะรายการล่าสุดที่ API ส่งกลับ</p><Notice feed={wazuh}/><div className="metrics"><Metric label="รายการที่อ่านได้" value={wazuh.data ? alerts.length : null} detail="สูงสุด 100 บรรทัดล่าสุด"/><Metric label="Wazuh level ≥ 7" value={wazuh.data ? alerts.filter(e => level(e.rule_level) && e.rule_level >= 7).length : null} detail="เกณฑ์แบ่งกลุ่มในหน้านี้"/><Metric label="Wazuh level ≥ 12" value={wazuh.data ? alerts.filter(e => level(e.rule_level) && e.rule_level >= 12).length : null} detail="เฉพาะรายการที่อ่านได้"/></div>
 <div className="table-wrap"><table><thead><tr>{["เวลา", "Agent", "Rule", "Wazuh severity", "Description"].map(v => <th key={v}>{v}</th>)}</tr></thead><tbody>{alerts.map((e,i) => <tr key={`${text(e.id)}-${i}`}><td>{time(e.timestamp)}</td><td>{text(e.agent_name)}</td><td>{text(e.rule_id)}</td><td>{level(e.rule_level) ? `Level ${e.rule_level}` : "Unknown"}</td><td>{text(e.description)}</td></tr>)}</tbody></table></div>{wazuh.data && !alerts.length && <p>API ส่งกลับโดยไม่มีรายการ Wazuh</p>}</div>
 <div className="subsection"><h3>Live AI Evidence</h3><Notice feed={live}/><p>เฉพาะเอกสาร processing_mode=live และ engine ที่ไม่ใช่ simulator หรือ replay; เอกสารไม่ระบุ mode ยังยืนยันเป็น live ไม่ได้</p><div className="table-wrap"><table><thead><tr><th>เวลา</th><th>Engine</th><th>AI score</th><th>AI class</th></tr></thead><tbody>{liveEvents.map((e,i) => <tr key={`${text(e.id)}-${i}`}><td>{time(e.timestamp)}</td><td>{text(e.analysis_engine)}</td><td>{numeric(e.threat_score) ? e.threat_score : "Unknown"}</td><td>{text(e.threat_class)}</td></tr>)}</tbody></table></div>{live.data && !liveEvents.length && <p>ไม่พบหลักฐาน live AI ในรายการที่อ่านได้</p>}</div></section>}
 <section id="replay"><div className="eyebrow">02 / REPLAY</div><h2>Replay Results <span className="tag amber">EXPERIMENTAL</span></h2><p>ผลทดลองจาก OpenSearch ผ่าน /api/replay/events · ไม่ยืนยันสุขภาพบริการสดหรือความพร้อม production</p><Notice feed={replay}/><div className="metrics"><Metric label="เอกสารตรงเงื่อนไขใน index" value={replay.data?.total} detail="mode=replay · production_ready=false"/><Metric label="รายการที่แสดง" value={replay.data ? events.length : null} detail="สูงสุด 100 รายการล่าสุด"/><Metric label="ผลไม่ตรงกัน" value={replay.data ? mismatches.length : null} detail={`เทียบได้ ${replay.data ? comparable.length : "—"} รายการ · ไม่ใช่ accuracy`}/></div>
 <div className="table-wrap"><table><thead><tr>{["เวลาประมวลผล / Event", "Rule", "Wazuh severity", "AI score / threshold", "AI prediction", "Model", "Behavioral", "Behavioral evidence", "เปรียบเทียบ"].map(v => <th key={v}>{v}</th>)}</tr></thead><tbody>{events.map((e,i) => <tr key={`${text(e.id)}-${i}`}><td>{time(e.scored_at_utc)}<small>{text(e.event_uid)}</small></td><td>{text(e.wazuh_rule_id)}</td><td>{level(e.wazuh_rule_level) ? `Level ${e.wazuh_rule_level}` : "Unknown"}</td><td>{numeric(e.high_severity_score) ? e.high_severity_score.toFixed(6) : "Unknown"}<small>threshold {text(e.threshold)}</small></td><td>{text(e.predicted_label)}</td><td>{text(e.model_name)}</td><td>{e.behavioral_analysis ? text(objectValue(e.behavioral_analysis)?.analysis_state) : "ไม่มีผลจับคู่"}</td><td>{e.behavioral_analysis ? <>{objectValue(e.behavioral_analysis)?.ae_ratio === null || objectValue(e.behavioral_analysis)?.ae_ratio === undefined ? "AE: not scored" : `AE ${Number(objectValue(e.behavioral_analysis)?.ae_ratio).toFixed(2)}×`}<small>{`routing ${text(objectValue(e.behavioral_analysis)?.routing_status)} · support ${text(objectValue(e.behavioral_analysis)?.train_cohort_support)} · novelty ${objectValue(e.behavioral_analysis)?.semantic_novelty === true ? "yes" : "no"}`}</small></> : "—"}</td><td>{!comparable.includes(e) ? "ข้อมูลไม่ครบ" : mismatches.includes(e) ? "ไม่ตรงกัน" : "ตรงกัน"}</td></tr>)}</tbody></table></div>{replay.data && !events.length && <p>ยังไม่มีผล replay ตรงเงื่อนไขใน index</p>}<p className="footnote">เทียบ Wazuh level ≥ 7 กับ high_severity ตามเกณฑ์ทดลอง · Severity AI score ไม่ใช่ความน่าจะเป็นของการโจมตี · Behavioral anomaly/novelty เป็นหลักฐานเชิงพฤติกรรม ไม่ใช่ malicious classification</p></section>
 <section id="quality"><div className="eyebrow">03 / MODEL</div><h2>Model Quality</h2>
 <p>ผลประเมินจากรายงานจริงของรอบ offline แยกจากรายการ replay และสถานะบริการสด</p>
 <Notice feed={quality}/><ModelQuality data={quality.data}/></section><footer>อ่าน API ทุก 15 วินาที · เวลาอ่าน API แยกจากเวลา event · ไม่มีข้อมูลจำลอง</footer></main>;
}
