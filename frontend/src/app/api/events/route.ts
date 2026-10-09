import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const OPENSEARCH_URL =
  process.env.OPENSEARCH_URL || "http://localhost:9200";

export async function GET() {
  try {
    const response = await fetch(
      `${OPENSEARCH_URL}/edrxdr-events-*/_search`,
      {
        method: "POST",

        headers: {
          "Content-Type": "application/json",
        },

        body: JSON.stringify({
          size: 100,
          track_total_hits: true,

          sort: [
            {
              timestamp: {
                order: "desc",
                unmapped_type: "date",
              },
            },
          ],

          query: {
            bool: { filter: [{ term: { processing_mode: "live" } }], must_not: [{ term: { analysis_engine: "morpheus-simulator" } }] },
          },
        }),

        cache: "no-store",
        signal: AbortSignal.timeout(10000),
      }
    );

    if (!response.ok) {
      const text = await response.text();

      return NextResponse.json(
        {
          error: "OpenSearch request failed",
          details: text,
        },
        {
          status: response.status,
        }
      );
    }

    const data = await response.json();

    if (!Array.isArray(data.hits?.hits) || data.timed_out || (data._shards?.failed ?? 0) > 0) throw new Error("Invalid or incomplete OpenSearch response");
    const events =
      data.hits?.hits?.map(
        (hit: {
          _id: string;
          _index: string;
          _source: Record<string, unknown>;
        }) => ({
          ...hit._source,
          id: hit._id,
          index: hit._index,
        })
      ) ?? [];

    return NextResponse.json({
      total: data.hits?.total?.value ?? null,
      events,
    });
  } catch (error) {
    console.error(error);

    return NextResponse.json(
      {
        error: "Cannot connect to OpenSearch",
      },
      {
        status: 500,
      }
    );
  }
}
