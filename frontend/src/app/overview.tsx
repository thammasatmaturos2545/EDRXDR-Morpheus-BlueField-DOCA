"use client";
import Link from "next/link";
import { useEffect, useState } from "react";

type Summary = { fetched: string; values: Record<string, number> };
type Feed = { data: Summary | null; error: boolean; loading: boolean };
function summary(value: unknown, bluefield: boolean): Summary {
  if (!value || typeof value !== "object") throw new Error("Invalid response");
  const v = value as Record<string, unknown>;
  if (v.mode !== (bluefield ? "shadow_bluefield" : "shadow") || typeof v.fetched_at !== "string" || !Number.isFinite(Date.parse(v.fetched_at))) throw new Error("Invalid mode");
  if (bluefield && (v.historical !== true || v.live !== false || v.production_ready !== false || v.automated_response_allowed !== false)) throw new Error("Invalid scope");
  const fields = bluefield ? ["records", "interfaces", "carrier_unknown", "first_sample", "computed"] : ["severity", "behavioral", "matched", "conflicts", "unmatched", "candidates", "ae_scored", "novelty"];
  if (!v.counts || typeof v.counts !== "object") throw new Error("Missing counts");
  const counts = v.counts as Record<string, unknown>;
  const values: Record<string, number> = {};
  for (const key of fields) {
    const n = counts[key];
    if (typeof n !== "number" || !Number.isSafeInteger(n) || n < 0 || n > 1000) throw new Error("Invalid count");
    values[key] = n;
  }
  if (bluefield ? values.records > 500 || [values.interfaces, values.carrier_unknown, values.first_sample, values.computed].some(n => n > values.records) : values.severity > 500 || values.behavioral > 500 || values.matched + values.conflicts > Math.min(values.severity, values.behavioral) || values.candidates > values.severity || values.ae_scored > values.behavioral) throw new Error("Inconsistent counts");
  return { fetched: v.fetched_at, values };
}
export { summary };

function useSummary(url: string, bluefield: boolean, revision: number): Feed {
  const [feed, setFeed] = useState<Feed>({ data: null, error: false, loading: true });
  useEffect(() => {
    const controller = new AbortController();
    setFeed({ data: null, error: false, loading: true });
    void (async () => {
      try {
        const response = await fetch(url, { cache: "no-store", signal: AbortSignal.any([controller.signal, AbortSignal.timeout(15000)]) });
        if (!response.ok) throw new Error("Unavailable");
        const data = summary(await response.json(), bluefield);
        if (!controller.signal.aborted) setFeed({ data, error: false, loading: false });
      } catch {
        if (!controller.signal.aborted) setFeed({ data: null, error: true, loading: false });
      }
    })();
    return () => controller.abort();
  }, [url, bluefield, revision]);
  return feed;
}
const when = (v: string) => new Date(v).toLocaleString("th-TH", { timeZone: "Asia/Bangkok" });
function Status({ feed }: { feed: Feed }) {
  return <p className="overview-source" role="status">{feed.loading ? "กำลังอ่านผลที่บันทึกไว้…" : feed.error ? "ยังอ่านไม่ได้ — เปิดหน้ารายละเอียดเพื่อตรวจการเชื่อมต่อ" : `อ่าน API เมื่อ ${when(feed.data!.fetched)} · ไม่ใช่เวลาเหตุการณ์`}</p>;
}
function Value({ feed, field }: { feed: Feed; field: string }) {
  return <strong>{feed.data ? feed.data.values[field].toLocaleString("th-TH") : "—"}</strong>;
}

export default function Overview() {
  const [revision, setRevision] = useState(0);
  const [source, setSource] = useState("all");
  const shadow = useSummary("/api/shadow/events", false, revision);
  const bluefield = useSummary("/api/shadow/bluefield", true, revision);
  return <main className="overview">
    <header className="overview-hero">
      <div><div className="eyebrow">SECURITY OPERATIONS / RESEARCH</div><h1>Security overview</h1><p>ผลทดลอง Endpoint และ Network · ตรวจสอบย้อนกลับถึงหลักฐาน</p></div>
      <div className="overview-guide"><span className="scope-label">STORED EVIDENCE</span><p>ผลที่บันทึกไว้ · ไม่ใช่การเฝ้าระวังสด</p></div>
    </header>
    <div className="console-toolbar">
      <label>แหล่งข้อมูล<select value={source} onChange={e => setSource(e.target.value)}><option value="all">ทั้งหมด / All sources</option><option value="endpoint">Endpoint / Shadow</option><option value="network">Network / BlueField</option></select></label>
      <div className="console-scope"><span>ขอบเขตข้อมูล</span><strong>ชุดข้อมูลที่ API ส่งกลับ</strong><small>ไม่มีตัวกรองช่วงเวลา</small></div>
      <button disabled={shadow.loading || bluefield.loading} onClick={() => setRevision(n => n + 1)}>↻ อ่านข้อมูลอีกครั้ง</button>
    </div>
    <div className="overview-heading"><div><span className="eyebrow">01 / EVIDENCE</span><h2>ผลทดลองที่ตรวจสอบได้</h2></div><span className="overview-caption">ตัวเลขจาก API · ไม่มีข้อมูลแทนเมื่ออ่านไม่ได้</span></div>
    <div className={`overview-grid source-${source}`}>
      <section hidden={source === "network"} className="overview-card"><div className="overview-card-title"><span className="scope-label">ENDPOINT / SHADOW</span><span className="overview-number">01</span></div><h2>ผลสองโมเดล<br/>บนเหตุการณ์เดียวกัน</h2><p>เปรียบเทียบ Severity และ Behavioral จาก batch ที่เก็บไว้</p>
        <div className="overview-primary"><Value feed={shadow} field="matched"/><span>คู่ที่ข้อมูลตรงกัน<br/><small>การจับคู่ข้อมูล ไม่ใช่ accuracy</small></span></div>
        <dl className="overview-stats"><div><dt>Severity / Behavioral</dt><dd>{shadow.data ? `${shadow.data.values.severity} / ${shadow.data.values.behavioral}` : "—"}</dd></div><div><dt>ขาดคู่ / ขัดแย้ง</dt><dd>{shadow.data ? `${shadow.data.values.unmatched} / ${shadow.data.values.conflicts}` : "—"}</dd></div><div><dt>FP candidates · ยังไม่ยืนยัน</dt><dd>{shadow.data?.values.candidates ?? "—"}</dd></div><div><dt>มีคะแนน AE / Behavioral</dt><dd>{shadow.data ? `${shadow.data.values.ae_scored} / ${shadow.data.values.behavioral}` : "—"}</dd></div></dl>
        <Status feed={shadow}/><Link className="overview-link" href="/shadow">ตรวจผล Shadow <span aria-hidden="true">↗</span></Link>
      </section>
      <section hidden={source === "endpoint"} className="overview-card"><div className="overview-card-title"><span className="scope-label">NETWORK / BLUEFIELD</span><span className="overview-number">02</span></div><h2>Telemetry ย้อนหลัง<br/>รักษาความหมายของข้อมูล</h2><p>ผล BlueField Shadow จากข้อมูลย้อนหลัง ไม่ใช่สถานะ link ปัจจุบัน</p>
        <div className="overview-primary"><Value feed={bluefield} field="records"/><span>รายการใน Shadow<br/><small>host interface counters</small></span></div>
        <dl className="overview-stats"><div><dt>Interfaces ในชุดข้อมูล</dt><dd>{bluefield.data?.values.interfaces ?? "—"}</dd></div><div><dt>Carrier ไม่ทราบค่า</dt><dd>{bluefield.data?.values.carrier_unknown ?? "—"}</dd></div><div><dt>ตัวอย่างแรก · ไม่มี delta</dt><dd>{bluefield.data?.values.first_sample ?? "—"}</dd></div><div><dt>รายการที่คำนวณ delta แล้ว</dt><dd>{bluefield.data?.values.computed ?? "—"}</dd></div></dl>
        <Status feed={bluefield}/><Link className="overview-link" href="/bluefield">ตรวจหลักฐาน BlueField <span aria-hidden="true">↗</span></Link>
      </section>
    </div>
    <div className="overview-heading"><div><span className="eyebrow">02 / EXPLORE</span><h2>เลือกดูให้ตรงคำถาม</h2></div></div>
    <div className="overview-shortcuts"><Link href="/replay"><span>REPLAY</span><h3>ผลทดลองย้อนหลัง ↗</h3><p>ดูคะแนนและผลพฤติกรรมรายเหตุการณ์</p></Link><Link href="/details#quality"><span>MODEL QUALITY</span><h3>โมเดลทำได้แค่ไหน ↗</h3><p>ดูรายงานประเมินและข้อจำกัด แยกจากจำนวนจับคู่</p></Link><Link href="/details#live"><span>SYSTEM STATUS</span><h3>ตรวจสถานะบริการ ↗</h3><p>สถานะจากเครื่องที่รันเว็บ ไม่ใช่หลักฐานว่า pipeline ไหลครบ</p></Link></div>
    <section className="overview-reading"><div><span className="eyebrow">READ THE RESULTS</span><h2>สามเรื่องที่ต้องแยกกัน</h2></div><div><h3>Severity ≠ การโจมตี</h3><p>โมเดลประมาณระดับ Wazuh; candidate ยังต้องตรวจสอบ</p></div><div><h3>ไม่มีคะแนน ≠ ปลอดภัย</h3><p>ไม่มี AE score คือข้อมูลยังไม่ครอบคลุมการให้คะแนน</p></div><div><h3>Unknown ≠ ศูนย์</h3><p>null คือไม่ทราบค่า ส่วน 0 คือค่าศูนย์ที่อ่านได้</p></div></section>
    <footer>ต้นแบบเพื่อการวิจัยและประเมิน · ไม่ใช่การรับรองความพร้อม production · อ่านข้อมูลเมื่อเปิดหน้าและเมื่อกดรีเฟรช</footer>
  </main>;
}
