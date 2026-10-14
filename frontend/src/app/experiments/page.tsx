"use client";
import Link from "next/link";
import { useState } from "react";
import { demoHref } from "../../lib/soc";
import "../soc.css";
export default function Experiments() {
  const [runInput, setRunInput] = useState("");
  const [runError, setRunError] = useState(false);
  return <main className="soc">
    <header className="soc-head"><div><span className="soc-kicker">EXPERIMENTAL RESULTS</span><h1>ผลทดลอง / ตรวจสอบระบบ</h1><p>ผลสำหรับประเมินและตรวจย้อนหลัง แยกจากรายการเหตุการณ์บนหน้า SOC</p></div><Link href="/">กลับหน้า SOC →</Link></header>
    <p className="soc-note">ไม่ยืนยันความพร้อม production · การเปิดดูผลไม่เริ่ม worker · หน้านี้ยังไม่มีการจำกัดสิทธิ์ตามบทบาท</p>
    <section aria-labelledby="demo-open-title" style={{ padding: 20, marginBottom: 20 }}>
      <span className="soc-kicker">BOUNDED DEMO / RUN EXPLORER</span><h2 id="demo-open-title">เปิดผล Demo ตาม Run ID</h2>
      <p id="demo-open-help">อ่านผลของรอบที่ระบุเท่านั้น ไม่เริ่ม worker หรือใช้ GPU · หน้าผลแสดงเวลาของรอบและสถานะ worker ตาม API</p>
      <form onSubmit={event => { event.preventDefault(); const href = demoHref(runInput); if (!href) { setRunError(true); return; } window.location.assign(href); }}>
        <label htmlFor="soc-demo-run">Run ID จากบรรทัด Run: ใน log ของ worker</label>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginTop: 8 }}>
          <input id="soc-demo-run" value={runInput} onChange={event => { setRunInput(event.target.value); setRunError(false); }} aria-describedby={runError ? "demo-open-help demo-open-error" : "demo-open-help"} aria-invalid={runError} placeholder="วาง Run ID ของรอบที่ต้องการดู" autoComplete="off" spellCheck={false} maxLength={80} style={{ flex: "1 1 280px", marginTop: 0 }} />
          <button type="submit">เปิดผลรอบนี้ →</button>
        </div>
        {runError && <p id="demo-open-error" role="alert">Run ID ไม่ถูกต้อง ต้องเป็น d ตามด้วยวันที่ 8 หลัก, t, เวลา 6 หลัก, ขีดกลาง และรหัส hex ตัวเล็ก 8 หลัก</p>}
      </form>
      <small>รูปแบบถูกต้องไม่ได้ยืนยันว่ารอบนั้นมีข้อมูล หาก API อ่านไม่ได้ หน้าผลจะแสดง unavailable</small>
    </section>

    <div className="soc-scopebar"><Link href="/overview">ภาพรวมผลทดลอง</Link><Link href="/shadow">Shadow Results</Link><Link href="/replay">Replay Results</Link><Link href="/bluefield">BlueField Historical</Link><Link href="/details#quality">คุณภาพโมเดล</Link></div>
  </main>;
}
