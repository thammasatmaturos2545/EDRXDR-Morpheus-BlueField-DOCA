import { NextResponse } from "next/server";

import {
  parseLiveAiSearch,
} from "../../../lib/live-ai";

export const dynamic =
  "force-dynamic";

const OPENSEARCH_URL =
  process.env.OPENSEARCH_URL ||
  "http://localhost:9200";

export async function GET() {
  try {
    const response =
      await fetch(
        `${OPENSEARCH_URL}/edrxdr-events-*/_search`,
        {
          method: "POST",

          headers: {
            "Content-Type":
              "application/json",
          },

          body: JSON.stringify({
            size: 100,

            track_total_hits: true,

            _source: [
              "schema_version",
              "event_uid",
              "source_type",
              "processing_mode",
              "analysis_engine",
              "model_name",
              "text_contract_version",
              "high_severity_score",
              "predicted_label",
              "threshold",
              "wazuh_rule_id",
              "wazuh_rule_level",
              "source_topic",
              "source_partition",
              "source_offset",
              "input_topic",
              "input_partition",
              "input_offset",
              "scored_at_utc",
              "production_ready",
              "automated_response_allowed",
            ],

            sort: [
              {
                scored_at_utc: {
                  order: "desc",
                  unmapped_type:
                    "date",
                },
              },
              {
                event_uid: {
                  order: "asc",
                  unmapped_type:
                    "keyword",
                },
              },
            ],

            query: {
              bool: {
                filter: [
                  {
                    term: {
                      schema_version:
                        "live-severity-1",
                    },
                  },
                  {
                    term: {
                      source_type:
                        "wazuh",
                    },
                  },
                  {
                    term: {
                      processing_mode:
                        "live",
                    },
                  },
                  {
                    term: {
                      analysis_engine:
                        "nvidia-morpheus-context-severity-v1",
                    },
                  },
                  {
                    term: {
                      model_name:
                        "wazuh-severity-context-v2-balanced-20261008T190719Z-1398863",
                    },
                  },
                  {
                    term: {
                      production_ready:
                        false,
                    },
                  },
                  {
                    term: {
                      automated_response_allowed:
                        false,
                    },
                  },
                ],
              },
            },
          }),

          cache: "no-store",

          signal:
            AbortSignal.timeout(
              10000
            ),
        }
      );

    if (!response.ok) {
      return NextResponse.json(
        {
          total: 0,
          events: [],
          error:
            "OpenSearch request failed",
        },
        {
          status: 503,
        }
      );
    }

    const body =
      await response.json();

    const result =
      parseLiveAiSearch(body);

    return NextResponse.json(
      result,
      {
        headers: {
          "Cache-Control":
            "no-store",
        },
      }
    );
  } catch (error) {
    console.error(
      "Live AI API error:",
      error
    );

    return NextResponse.json(
      {
        total: 0,
        events: [],
        error:
          "Live AI data is unavailable or invalid",
      },
      {
        status: 503,
      }
    );
  }
}
