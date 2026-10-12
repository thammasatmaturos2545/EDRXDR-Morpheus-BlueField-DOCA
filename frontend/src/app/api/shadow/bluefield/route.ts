import { NextResponse } from "next/server";
import {
  BLUEFIELD_SHADOW_FIELDS,
  BLUEFIELD_SHADOW_INDEX,
  bluefieldShadowDocuments,
} from "@/lib/bluefield-shadow";

export const dynamic = "force-dynamic";

const headers = { "Cache-Control": "no-store" };

function endpoint(): URL {
  const raw = process.env.SHADOW_OPENSEARCH_URL;
  if (!raw) throw new Error("Missing Shadow OpenSearch endpoint");

  const url = new URL(raw);
  if (
    !["http:", "https:"].includes(url.protocol) ||
    url.username ||
    url.password ||
    url.search ||
    url.hash ||
    url.pathname !== "/"
  ) {
    throw new Error("Invalid Shadow OpenSearch endpoint");
  }
  return url;
}

export async function GET() {
  if (!process.env.SHADOW_OPENSEARCH_URL) {
    return NextResponse.json(
      { error: "ยังไม่ได้กำหนดการเชื่อมต่อ Shadow OpenSearch" },
      { status: 503, headers },
    );
  }

  try {
    const url = endpoint();
    const response = await fetch(
      `${url.origin}/${BLUEFIELD_SHADOW_INDEX}/_search`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        cache: "no-store",
        redirect: "error",
        signal: AbortSignal.timeout(10000),
        body: JSON.stringify({
          size: 100,
          track_total_hits: true,
          _source: BLUEFIELD_SHADOW_FIELDS,
          sort: [
            { timestamp: { order: "asc", unmapped_type: "date" } },
            { ibdev: { order: "asc", unmapped_type: "keyword" } },
          ],
          query: {
            bool: {
              filter: [
                { term: { schema_version: "shadow-bluefield-1" } },
                { term: { processing_mode: "shadow" } },
                { term: { evidence_mode: "archived_normalized_replay" } },
                { term: { historical: true } },
                { term: { production_ready: false } },
                { term: { automated_response_allowed: false } },
              ],
            },
          },
        }),
      },
    );

    if (!response.ok) throw new Error("BlueField shadow search failed");

    const records = bluefieldShadowDocuments(await response.json());

    return NextResponse.json(
      {
        mode: "shadow_bluefield",
        historical: true,
        live: false,
        production_ready: false,
        automated_response_allowed: false,
        source_index: BLUEFIELD_SHADOW_INDEX,
        fetched_at: new Date().toISOString(),
        counts: {
          records: records.length,
          interfaces: new Set(
            records
              .map((record) => record.interface)
              .filter((value): value is string => typeof value === "string"),
          ).size,
          carrier_unknown: records.filter((r) => r.carrier === null).length,
          rx_zero: records.filter((r) => r.rx_bytes === 0).length,
          first_sample: records.filter(
            (r) => r.delta_status.rx_bytes === "first_sample",
          ).length,
          computed: records.filter(
            (r) => r.delta_status.rx_bytes === "computed",
          ).length,
        },
        records,
      },
      { headers },
    );
  } catch {
    return NextResponse.json(
      {
        error:
          "อ่าน BlueField Shadow ไม่สำเร็จ: ตรวจ endpoint, schema, safety flags, duplicate IDs หรือจำนวนเกินขอบเขต — ไม่แสดงผลบางส่วนเป็นผลครบ",
      },
      { status: 502, headers },
    );
  }
}
