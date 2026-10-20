export type Obj = Record<string, unknown>;

const LIVE_SCHEMA = "live-severity-1";
const LIVE_ENGINE = "nvidia-morpheus-context-severity-v1";
const LIVE_MODEL =
  "wazuh-severity-context-v2-balanced-20261008T190719Z-1398863";

const obj = (
  v: unknown
): v is Obj =>
  !!v &&
  typeof v === "object" &&
  !Array.isArray(v);

const str = (
  v: unknown
) =>
  typeof v === "string" &&
  v.trim()
    ? v.trim()
    : null;

const int = (
  v: unknown
) =>
  typeof v === "number" &&
  Number.isSafeInteger(v) &&
  v >= 0
    ? v
    : null;

const finite = (
  v: unknown
) =>
  typeof v === "number" &&
  Number.isFinite(v)
    ? v
    : null;

const date = (
  v: unknown
) => {
  const s = str(v);

  return s &&
    Number.isFinite(
      Date.parse(s)
    )
      ? s
      : null;
};

const first = (
  ...vs: unknown[]
) => {
  for (const v of vs) {
    const s = str(v);

    if (s) {
      return s;
    }

    if (Array.isArray(v)) {
      for (const x of v) {
        const n = str(x);

        if (n) {
          return n;
        }
      }
    }
  }

  return null;
};

const eventUid = (
  r: Obj
) => {
  const uid = str(
    r.event_uid
  );

  return uid &&
    /^[0-9a-f]{64}$/.test(uid)
      ? uid
      : null;
};

function validateLiveAiRow(
  value: unknown
): Obj {
  if (!obj(value)) {
    throw new Error(
      "Invalid live AI row"
    );
  }

  const uid =
    eventUid(value);

  const s =
    finite(
      value.high_severity_score
    );

  if (
    value.schema_version !==
      LIVE_SCHEMA ||
    value.source_type !==
      "wazuh" ||
    value.processing_mode !==
      "live" ||
    value.analysis_engine !==
      LIVE_ENGINE ||
    value.model_name !==
      LIVE_MODEL ||
    value.production_ready !==
      false ||
    value.automated_response_allowed !==
      false
  ) {
    throw new Error(
      "Unexpected live AI contract"
    );
  }

  if (!uid) {
    throw new Error(
      "Invalid live AI event_uid"
    );
  }

  if (
    s === null ||
    s < 0 ||
    s > 1
  ) {
    throw new Error(
      "Invalid AI severity score"
    );
  }

  if (
    value.threshold !== 0.5
  ) {
    throw new Error(
      "Unexpected AI threshold"
    );
  }

  const expected =
    s >= 0.5
      ? "high_severity"
      : "low_severity";

  if (
    value.predicted_label !==
      expected
  ) {
    throw new Error(
      "AI score/label mismatch"
    );
  }

  if (
    value.source_topic !==
      "wazuh-alerts" ||
    int(
      value.source_partition
    ) === null ||
    int(
      value.source_offset
    ) === null
  ) {
    throw new Error(
      "Invalid Wazuh provenance"
    );
  }

  if (
    value.input_topic !==
      "morpheus-input" ||
    int(
      value.input_partition
    ) === null ||
    int(
      value.input_offset
    ) === null
  ) {
    throw new Error(
      "Invalid Morpheus provenance"
    );
  }

  if (
    !date(
      value.scored_at_utc
    )
  ) {
    throw new Error(
      "Invalid AI score timestamp"
    );
  }

  return value;
}

export function validateNexusAi(
  payload: unknown
): Obj[] {
  if (
    !obj(payload) ||
    !Array.isArray(
      payload.events
    ) ||
    payload.events.length > 100
  ) {
    throw new Error(
      "Invalid live AI payload"
    );
  }

  return payload.events.map(
    validateLiveAiRow
  );
}

/*
 * Live Wazuh ↔ AI correlation is deliberately strict:
 *
 * event_uid must exist on both sides and be exactly equal.
 *
 * No matching by:
 * - timestamp proximity
 * - rule id
 * - host / agent
 * - raw hash fallback
 * - source coordinates fallback
 * - latest AI result
 */
export function correlateWazuhAi(
  w: Obj,
  rows: Obj[],
  available = true
) {
  if (!available) {
    return {
      status: "unavailable",
      method: null,
      event: null,
    };
  }

  const uid =
    eventUid(w);

  if (!uid) {
    return {
      status: "not_found",
      method: null,
      event: null,
    };
  }

  const hits =
    rows.filter(
      (a) =>
        eventUid(a) === uid
    );

  if (!hits.length) {
    return {
      status: "not_found",
      method: null,
      event: null,
    };
  }

  if (hits.length !== 1) {
    return {
      status: "conflict",
      method: null,
      event: null,
    };
  }

  return {
    status: "matched",
    method: "event_uid",
    event: hits[0],
  };
}

const level = (
  r: Obj
) => {
  const v =
    int(
      r.rule_level ??
        r.wazuh_rule_level
    );

  return v !== null &&
    v <= 15
      ? v
      : null;
};

const severity = (
  v: number | null
) =>
  v === null
    ? "unknown"
    : v >= 12
      ? "critical"
      : v >= 7
        ? "high"
        : v >= 4
          ? "medium"
          : v >= 1
            ? "low"
            : "info";

const score = (
  r: Obj | null
) => {
  if (!r) {
    return null;
  }

  const v =
    finite(
      r.high_severity_score
    );

  return v !== null &&
    v >= 0 &&
    v <= 1
      ? v
      : null;
};

export function buildNexusSnapshot(
  wazuhPayload: unknown,
  aiPayload: unknown,
  options: {
    hours?: number;
    generatedAt?: string;
    aiAvailable?: boolean;
    lookupStatuses?: Record<string, "matched" | "not_found" | "conflict" | "unavailable" | "source_unavailable">;
  } = {}
) {
  if (
    !obj(wazuhPayload) ||
    !Array.isArray(
      wazuhPayload.alerts
    )
  ) {
    throw new Error(
      "Invalid Wazuh payload"
    );
  }

  const generatedAt =
    date(
      options.generatedAt
    ) ??
    new Date().toISOString();

  const hours =
    [1, 24, 168].includes(
      options.hours ?? 24
    )
      ? options.hours ?? 24
      : 24;

  const aiAvailable =
    options.aiAvailable !==
    false;

  const ais =
    aiAvailable
      ? validateNexusAi(aiPayload)
      : [];

  const rows =
    wazuhPayload.alerts
      .filter(
        (x): x is Obj =>
          obj(x)
      )
      .slice(0, options.lookupStatuses ? 200 : 100);

  const alerts =
    rows.map(
      (r, i) => {
        const l =
          level(r);

        const lookupStatus = options.lookupStatuses?.[eventUid(r) ?? ""];
        const c = lookupStatus && lookupStatus !== "matched"
          ? { status: lookupStatus === "source_unavailable" ? "unavailable" : lookupStatus, method: null, event: null }
          : correlateWazuhAi(
            r,
            ais,
            aiAvailable
          );

        const a =
          c.event as
            | Obj
            | null;

        const ts =
          date(
            r.timestamp ??
              r["@timestamp"]
          );

        const uid =
          eventUid(r);

        const hash =
          first(
            r.raw_sha256
          );

        const aiScore =
          score(a);

        const aiLabel =
          a
            ? first(
                a.predicted_label
              )
            : null;

        const aiEngine =
          a
            ? first(
                a.analysis_engine
              )
            : null;

        const aiModel =
          a
            ? first(
                a.model_name
              )
            : null;

        const aiScoredAt =
          a
            ? date(
                a.scored_at_utc
              )
            : null;

        return {
          id:
            first(
              uid,
              hash,
              r.id
            ) ??
            `wazuh-${
              first(
                r.rule_id
              ) ?? "unknown"
            }-${i}`,

          title:
            first(
              r.description,
              r.rule_description
            ) ??
            `Wazuh alert${
              first(
                r.rule_id
              )
                ? ` · Rule ${
                    first(
                      r.rule_id
                    )
                  }`
                : ""
            }`,

          severity:
            severity(l),

          status:
            "new",

          host:
            first(
              r.agent_name
            ) ??
            "Unknown",

          ip:
            first(
              r.agent_ip,
              r.src_ip
            ) ??
            "",

          user:
            first(
              r.user,
              r.dst_user,
              r.src_user
            ) ??
            "",

          source:
            "Wazuh",

          category:
            first(
              r.category
            ) ??
            "Endpoint alert",

          tactic:
            first(
              r.mitre_tactic,
              r.tactic
            ) ??
            "Unmapped",

          technique:
            first(
              r.mitre_id,
              r.technique
            ) ??
            "",

          technique_name:
            first(
              r.mitre_technique,
              r.technique_name
            ) ??
            "",

          created_at:
            ts,

          last_seen:
            ts,

          description:
            first(
              r.description,
              r.rule_description
            ) ??
            "Wazuh alert loaded from the current API snapshot.",

          rule_id:
            first(
              r.rule_id,
              r.wazuh_rule_id
            ) ??
            "",

          evidence: {
            uid_lookup_status: lookupStatus ?? null,
            wazuh_level:
              l,

            event_uid:
              uid,

            raw_sha256:
              hash,

            ai_status:
              c.status,

            ai_match_method:
              c.method,

            ai_score:
              aiScore,

            ai_label:
              aiLabel,

            // Compatibility for the uploaded NEXUS UI.
            ai_class:
              aiLabel,

            ai_engine:
              aiEngine,

            ai_model:
              aiModel,

            ai_scored_at:
              aiScoredAt,
          },

          timeline: [],
          tags: [],
        };
      }
    );

  const events =
    alerts.map(
      (a) => ({
        id:
          `event-${a.id}`,

        timestamp:
          a.last_seen,

        host:
          a.host,

        ip:
          a.ip,

        user:
          a.user,

        source:
          "Wazuh",

        event_type:
          "wazuh_alert",

        severity:
          a.severity,

        message:
          a.description,

        process:
          "",

        event_id:
          a.id,

        raw: {
          id:
            a.id,

          rule_id:
            a.rule_id,

          wazuh_level:
            a.evidence
              .wazuh_level,

          event_uid:
            a.evidence
              .event_uid,

          ai_status:
            a.evidence
              .ai_status,

          ai_match_method:
            a.evidence
              .ai_match_method,

          ai_score:
            a.evidence
              .ai_score,

          ai_label:
            a.evidence
              .ai_label,

          ai_model:
            a.evidence
              .ai_model,

          ai_scored_at:
            a.evidence
              .ai_scored_at,
        },
      })
    );

  const latest =
    rows
      .map(
        (r) =>
          date(
            r.timestamp ??
              r["@timestamp"]
          )
      )
      .filter(Boolean)
      .sort()
      .at(-1) ??
    null;

  return {
    schema_version: 1,

    generated_at:
      generatedAt,

    window_hours:
      hours,

    summary: {
      events_total:
        events.length,

      avg_triage_minutes:
        null,

      series: [],
    },

    alerts,
    endpoints: [],
    events,
    cases: [],

    sources:
      latest
        ? [
            {
              id: "wazuh",
              name: "Wazuh",
              kind: "endpoint",
              status: options.lookupStatuses ? "unknown" : "healthy",
              events:
                alerts.length,
              last_seen:
                latest,
              description:
                "Loaded Wazuh rows, including source-verified UID references when enabled. Counts are not total historical ingestion or service-health evidence.",
            },
          ]
        : [],

    meta: {
      production_ready: false,
      automated_response_allowed: false,
      demo: false,

      events_sampled:
        true,

      write_enabled:
        false,

      backend:
        "EDRXDR-Morpheus",

      description:
        aiAvailable
          ? "Exact event_uid AI correlation only; no timestamp, rule, host, hash, or proximity joins."
          : "Wazuh loaded; AI API unavailable. No AI result is inferred.",
    },
  };
}
