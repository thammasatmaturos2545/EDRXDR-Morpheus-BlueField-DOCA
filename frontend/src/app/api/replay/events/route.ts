import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const headers = { "Cache-Control": "no-store" };

export async function GET() {
  const base = process.env.REPLAY_OPENSEARCH_URL;

  if (!base) {
    return NextResponse.json(
      { error: "ยังไม่ได้กำหนดการเชื่อมต่อ OpenSearch สำหรับ replay" },
      { status: 503, headers }
    );
  }

  try {
    const response = await fetch(
      `${base.replace(/\/+$/, "")}/replay-severity-v1/_search`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          size: 100,
          track_total_hits: true,
          sort: [
            {
              scored_at_utc: {
                order: "desc",
                unmapped_type: "date",
              },
            },
          ],
          query: {
            bool: {
              filter: [
                { term: { processing_mode: "replay" } },
                { term: { schema_version: "replay-severity-1" } },
                { term: { production_ready: false } },
              ],
            },
          },
          _source: [
            "event_uid",
            "scored_at_utc",
            "wazuh_rule_id",
            "wazuh_rule_level",
            "high_severity_score",
            "predicted_label",
            "threshold",
            "model_name",
            "processing_mode",
            "production_ready",
          ],
        }),
        cache: "no-store",
        signal: AbortSignal.timeout(10000),
      }
    );

    if (!response.ok) {
      return NextResponse.json(
        { error: "อ่านข้อมูล replay จาก OpenSearch ไม่สำเร็จ" },
        { status: 502, headers }
      );
    }

    type Hit = {
      _id: string;
      _source: Record<string, unknown>;
    };

    const data = await response.json();
    if (!Array.isArray(data.hits?.hits) || data.timed_out || (data._shards?.failed ?? 0) > 0) {
      throw new Error("Invalid search response");
    }

    const events = data.hits.hits.map((hit: Hit) => ({
      ...hit._source,
      id: hit._id,
    }));

    return NextResponse.json(
      {
        mode: "replay",
        total: data.hits?.total?.value ?? null,
        events,
      },
      { headers }
    );
  } catch {
    return NextResponse.json(
      { error: "เชื่อมต่อ OpenSearch สำหรับ replay ไม่ได้หรือหมดเวลา" },
      { status: 502, headers }
    );
  }
}
