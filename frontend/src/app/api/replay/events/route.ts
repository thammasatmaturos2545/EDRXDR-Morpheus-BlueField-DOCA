import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const headers = {
  "Cache-Control": "no-store",
};

type ReplaySource = Record<string, unknown> & {
  schema_version?: unknown;
  event_uid?: unknown;
  processing_mode?: unknown;
  production_ready?: unknown;
  scored_at_utc?: unknown;
};

type BehavioralDocument = ReplaySource & {
  behavioral_document_id: string;
};

type Hit = {
  _id: string;
  _source: ReplaySource;
};

type SearchResponse = {
  timed_out?: boolean;
  _shards?: {
    failed?: number;
  };
  hits?: {
    total?: {
      value?: number;
    };
    hits?: Hit[];
  };
};

async function searchIndex(
  base: string,
  index: string,
  body: Record<string, unknown>,
  optional = false
): Promise<SearchResponse> {
  const response = await fetch(
    `${base.replace(/\/+$/, "")}/${index}/_search`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
      cache: "no-store",
      signal: AbortSignal.timeout(10000),
    }
  );

  if (optional && response.status === 404) {
    return {
      hits: {
        total: { value: 0 },
        hits: [],
      },
    };
  }

  if (!response.ok) {
    throw new Error(
      `OpenSearch ${index} returned ${response.status}`
    );
  }

  const data = (await response.json()) as SearchResponse;

  if (
    !Array.isArray(data.hits?.hits) ||
    data.timed_out ||
    (data._shards?.failed ?? 0) > 0
  ) {
    throw new Error(
      `Invalid OpenSearch response from ${index}`
    );
  }

  return data;
}

export async function GET() {
  const base = process.env.REPLAY_OPENSEARCH_URL;

  if (!base) {
    return NextResponse.json(
      {
        error:
          "ยังไม่ได้กำหนดการเชื่อมต่อ OpenSearch สำหรับ replay",
      },
      {
        status: 503,
        headers,
      }
    );
  }

  try {
    const severityBody = {
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
            {
              term: {
                processing_mode: "replay",
              },
            },
            {
              term: {
                schema_version:
                  "replay-severity-1",
              },
            },
            {
              term: {
                production_ready: false,
              },
            },
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
    };

    /*
     * Behavioral index currently uses dynamic mappings.
     * Read the small replay index without term filters and
     * validate schema/mode/readiness here instead.
     */
    const behavioralBody = {
      size: 500,
      track_total_hits: true,
      sort: [
        {
          scored_at_utc: {
            order: "desc",
            unmapped_type: "date",
          },
        },
      ],
      _source: [
        "schema_version",
        "event_uid",
        "scored_at_utc",
        "processing_mode",
        "production_ready",
        "automated_response_allowed",
        "model_version",
        "analysis_state",
        "routing_status",
        "train_cohort_support",
        "ae_reconstruction_error",
        "ae_threshold",
        "ae_ratio",
        "ae_anomaly",
        "semantic_novelty",
        "command_class",
        "command_class_train_support",
        "package_argument_count",
        "wazuh_rule_id",
        "wazuh_rule_level",
      ],
    };

    const [
      severityData,
      behavioralData,
    ] = await Promise.all([
      searchIndex(
        base,
        "replay-severity-v1",
        severityBody
      ),
      searchIndex(
        base,
        "replay-behavioral-v1",
        behavioralBody,
        true
      ),
    ]);

    const severityHits =
      severityData.hits?.hits ?? [];

    const behavioralHits =
      behavioralData.hits?.hits ?? [];

    const behavioralDocuments =
      behavioralHits
        .map(
          (hit): BehavioralDocument => ({
            ...hit._source,
            behavioral_document_id: hit._id,
          })
        )
        .filter(
          (source) =>
            source.schema_version ===
              "replay-behavioral-1" &&
            source.processing_mode ===
              "replay" &&
            source.production_ready === false
        );

    /*
     * Behavioral results are sorted newest first.
     * Keep the newest result for each event_uid.
     */
    const behavioralByUid = new Map<
      string,
      Record<string, unknown>
    >();

    for (const source of behavioralDocuments) {
      const uid = source.event_uid;

      if (
        typeof uid === "string" &&
        uid.length > 0 &&
        !behavioralByUid.has(uid)
      ) {
        behavioralByUid.set(
          uid,
          source
        );
      }
    }

    const severityUids = new Set<string>();

    let behavioralJoined = 0;

    const events = severityHits.map(
      (hit) => {
        const source = hit._source;
        const uid = source.event_uid;

        let behavioralAnalysis:
          | Record<string, unknown>
          | null = null;

        if (
          typeof uid === "string" &&
          uid.length > 0
        ) {
          severityUids.add(uid);

          behavioralAnalysis =
            behavioralByUid.get(uid) ??
            null;
        }

        if (behavioralAnalysis) {
          behavioralJoined += 1;
        }

        return {
          ...source,
          id: hit._id,
          behavioral_analysis:
            behavioralAnalysis,
        };
      }
    );

    const behavioralOrphans =
      Array.from(
        behavioralByUid.keys()
      ).filter(
        (uid) =>
          !severityUids.has(uid)
      ).length;

    return NextResponse.json(
      {
        mode: "replay",

        total:
          severityData.hits?.total
            ?.value ?? null,

        behavioral_total:
          behavioralByUid.size,

        behavioral_joined:
          behavioralJoined,

        behavioral_orphans:
          behavioralOrphans,

        events,
      },
      {
        headers,
      }
    );
  } catch {
    return NextResponse.json(
      {
        error:
          "เชื่อมต่อ OpenSearch สำหรับ replay ไม่ได้หรือหมดเวลา",
      },
      {
        status: 502,
        headers,
      }
    );
  }
}
