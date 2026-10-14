export type Obj = Record<string, unknown>;

export type LiveAiEvent = {
  schema_version: "live-severity-1";
  event_uid: string;
  source_type: "wazuh";

  processing_mode: "live";

  analysis_engine:
    "nvidia-morpheus-context-severity-v1";

  model_name: string;

  high_severity_score: number;

  predicted_label:
    | "high_severity"
    | "low_severity";

  threshold: 0.5;

  wazuh_rule_id: string | null;
  wazuh_rule_level: number | null;

  source_topic: "wazuh-alerts";
  source_partition: number;
  source_offset: number;

  input_topic: "morpheus-input";
  input_partition: number;
  input_offset: number;

  scored_at_utc: string;

  production_ready: false;
  automated_response_allowed: false;
};

const SCHEMA =
  "live-severity-1";

const ENGINE =
  "nvidia-morpheus-context-severity-v1";

const MODEL =
  "wazuh-severity-context-v2-balanced-" +
  "20261008T190719Z-1398863";

const TEXT_CONTRACT =
  "wazuh-context-v2-raw-1";

function obj(
  value: unknown
): value is Obj {
  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value)
  );
}

function hex64(
  value: unknown
): value is string {
  return (
    typeof value === "string" &&
    /^[0-9a-f]{64}$/.test(value)
  );
}

function uint(
  value: unknown
): value is number {
  return (
    typeof value === "number" &&
    Number.isSafeInteger(value) &&
    value >= 0
  );
}

function date(
  value: unknown
): value is string {
  return (
    typeof value === "string" &&
    value.length > 0 &&
    Number.isFinite(
      Date.parse(value)
    ) &&
    (
      value.endsWith("Z") ||
      /[+-]\d\d:\d\d$/.test(value)
    )
  );
}

function score(
  value: unknown
): value is number {
  return (
    typeof value === "number" &&
    Number.isFinite(value) &&
    value >= 0 &&
    value <= 1
  );
}

export function validateLiveAi(
  value: unknown
): LiveAiEvent {
  if (!obj(value)) {
    throw new Error(
      "Invalid live AI document"
    );
  }

  const d = value;

  if (
    d.schema_version !== SCHEMA ||
    d.source_type !== "wazuh" ||
    d.processing_mode !== "live" ||
    d.analysis_engine !== ENGINE ||
    d.model_name !== MODEL ||
    d.text_contract_version !==
      TEXT_CONTRACT
  ) {
    throw new Error(
      "Unexpected live AI contract"
    );
  }

  if (
    d.production_ready !== false ||
    d.automated_response_allowed !==
      false
  ) {
    throw new Error(
      "Unsafe live AI state"
    );
  }

  if (!hex64(d.event_uid)) {
    throw new Error(
      "Invalid event_uid"
    );
  }

  if (!score(d.high_severity_score)) {
    throw new Error(
      "Invalid AI severity score"
    );
  }

  if (d.threshold !== 0.5) {
    throw new Error(
      "Unexpected threshold"
    );
  }

  const expected =
    d.high_severity_score >= 0.5
      ? "high_severity"
      : "low_severity";

  if (
    d.predicted_label !== expected
  ) {
    throw new Error(
      "Score/label mismatch"
    );
  }

  if (
    d.source_topic !==
      "wazuh-alerts" ||
    !uint(d.source_partition) ||
    !uint(d.source_offset)
  ) {
    throw new Error(
      "Invalid Wazuh provenance"
    );
  }

  if (
    d.input_topic !==
      "morpheus-input" ||
    !uint(d.input_partition) ||
    !uint(d.input_offset)
  ) {
    throw new Error(
      "Invalid inference provenance"
    );
  }

  if (!date(d.scored_at_utc)) {
    throw new Error(
      "Invalid scoring timestamp"
    );
  }

  const level =
    d.wazuh_rule_level;

  if (
    level !== null &&
    (
      typeof level !== "number" ||
      !Number.isInteger(level) ||
      level < 0 ||
      level > 15
    )
  ) {
    throw new Error(
      "Invalid Wazuh rule level"
    );
  }

  const rawRuleId =
    d.wazuh_rule_id;

  const ruleId =
    rawRuleId === null ||
    rawRuleId === undefined
      ? null
      : (
          typeof rawRuleId === "string" ||
          typeof rawRuleId === "number"
        )
        ? String(rawRuleId)
        : null;

  if (
    rawRuleId !== null &&
    rawRuleId !== undefined &&
    ruleId === null
  ) {
    throw new Error(
      "Invalid Wazuh rule id"
    );
  }

  /*
   * Browser projection intentionally excludes:
   * artifact_hashes
   * vocab_hash_sha256
   * engine_sha256
   * worker_sha256
   * raw_event
   * full_log
   * text_input
   */
  return {
    schema_version:
      "live-severity-1",

    event_uid:
      d.event_uid,

    source_type:
      "wazuh",

    processing_mode:
      "live",

    analysis_engine:
      ENGINE,

    model_name:
      MODEL,

    high_severity_score:
      d.high_severity_score,

    predicted_label:
      expected,

    threshold:
      0.5,

    wazuh_rule_id:
      ruleId,

    wazuh_rule_level:
      level ?? null,

    source_topic:
      "wazuh-alerts",

    source_partition:
      d.source_partition,

    source_offset:
      d.source_offset,

    input_topic:
      "morpheus-input",

    input_partition:
      d.input_partition,

    input_offset:
      d.input_offset,

    scored_at_utc:
      d.scored_at_utc,

    production_ready:
      false,

    automated_response_allowed:
      false,
  };
}

export function parseLiveAiSearch(
  value: unknown
): {
  total: number;
  events: LiveAiEvent[];
} {
  if (!obj(value)) {
    throw new Error(
      "Invalid OpenSearch response"
    );
  }

  if (
    value.timed_out !== false
  ) {
    throw new Error(
      "OpenSearch search timed out"
    );
  }

  const shards =
    value._shards;

  if (
    !obj(shards) ||
    shards.failed !== 0
  ) {
    throw new Error(
      "OpenSearch shard failure"
    );
  }

  const hitsObject =
    value.hits;

  if (!obj(hitsObject)) {
    throw new Error(
      "Missing hits"
    );
  }

  const totalObject =
    hitsObject.total;

  if (
    !obj(totalObject) ||
    totalObject.relation !== "eq" ||
    !uint(totalObject.value)
  ) {
    throw new Error(
      "Invalid total hits"
    );
  }

  const hits =
    hitsObject.hits;

  if (!Array.isArray(hits)) {
    throw new Error(
      "Invalid hit list"
    );
  }

  if (hits.length > 100) {
    throw new Error(
      "Unbounded live AI result"
    );
  }

  const events =
    hits.map((hit) => {
      if (
        !obj(hit) ||
        !obj(hit._source)
      ) {
        throw new Error(
          "Invalid OpenSearch hit"
        );
      }

      return validateLiveAi(
        hit._source
      );
    });

  const seen =
    new Set<string>();

  for (const event of events) {
    if (
      seen.has(event.event_uid)
    ) {
      throw new Error(
        "Duplicate live AI event_uid"
      );
    }

    seen.add(
      event.event_uid
    );
  }

  return {
    total:
      totalObject.value,

    events,
  };
}
