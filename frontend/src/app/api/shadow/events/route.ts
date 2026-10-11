import { NextResponse } from "next/server";
import { documents, FIELDS, joinShadow } from "@/lib/shadow";

export const dynamic = "force-dynamic";
const headers = { "Cache-Control": "no-store" };

export async function GET() {
  const base = process.env.SHADOW_OPENSEARCH_URL;
  if (!base) return NextResponse.json({ error: "ยังไม่ได้กำหนดการเชื่อมต่อ Shadow OpenSearch" }, { status: 503, headers });
  try {
    const url = new URL(base);
    if (!["http:", "https:"].includes(url.protocol) || url.username || url.password || url.search || url.hash || url.pathname !== "/") throw new Error("Invalid endpoint");
    const get = async (kind: "severity" | "behavioral") => {
      const response = await fetch(`${url.origin}/shadow-${kind}-v1/_search`, {
        method: "POST", headers: { "Content-Type": "application/json" }, cache: "no-store", redirect: "error",
        signal: AbortSignal.timeout(10000),
        body: JSON.stringify({ size: 500, track_total_hits: true, _source: FIELDS, query: { match_all: {} } }),
      });
      if (!response.ok) throw new Error("Search failed");
      return documents(await response.json(), kind);
    };
    const [severity, behavioral] = await Promise.all([get("severity"), get("behavioral")]);
    return NextResponse.json({ mode: "shadow", fetched_at: new Date().toISOString(), ...joinShadow(severity, behavioral) }, { headers });
  } catch {
    return NextResponse.json({ error: "อ่าน Shadow ไม่สำเร็จ: ตรวจการเชื่อมต่อ, schema, คู่ซ้ำ หรือจำนวนเกินขอบเขต 500 รายการต่อ index — ไม่แสดงผลบางส่วนเป็นผลครบ" }, { status: 502, headers });
  }
}
