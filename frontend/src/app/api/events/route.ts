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

          sort: [
            {
              timestamp: {
                order: "desc",
                unmapped_type: "date",
              },
            },
          ],

          query: {
            match_all: {},
          },
        }),

        cache: "no-store",
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

    const events =
      data.hits?.hits?.map(
        (hit: {
          _id: string;
          _index: string;
          _source: Record<string, unknown>;
        }) => ({
          id: hit._id,
          index: hit._index,
          ...hit._source,
        })
      ) ?? [];

    return NextResponse.json({
      total: data.hits?.total?.value ?? 0,
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
