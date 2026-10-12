export type BluefieldShadowDoc = {
  id: string;
  schema_version: "shadow-bluefield-1";
  processing_mode: "shadow";
  evidence_mode: "archived_normalized_replay";
  historical: true;
  production_ready: false;
  automated_response_allowed: false;
  source_type: "bluefield";
  measurement_scope: "host_interface_counters";
  sample_uid: string;
  input_sha256: string;
  capture_scope_sha256: string;
  timestamp: string;
  ingested_at_utc: string;
  source: {
    cluster_id: string;
    topic: "shadow-bluefield-input-v1";
    partition: number;
    offset: number;
  };
  ibdev: string;
  interface: string | null;
  operstate: string | null;
  carrier: 0 | 1 | null;
  rx_packets: number | null;
  tx_packets: number | null;
  rx_bytes: number | null;
  tx_bytes: number | null;
  rx_errors: number | null;
  tx_errors: number | null;
  delta_rx_packets: number | null;
  delta_tx_packets: number | null;
  delta_rx_bytes: number | null;
  delta_tx_bytes: number | null;
  delta_rx_errors: number | null;
  delta_tx_errors: number | null;
  delta_status: {
    rx_packets: string;
    tx_packets: string;
    rx_bytes: string;
    tx_bytes: string;
    rx_errors: string;
    tx_errors: string;
  };
  sample_interval_seconds: number | null;
};

type Obj = Record<string, unknown>;

export const BLUEFIELD_SHADOW_INDEX = "shadow-bluefield-v1";

export const BLUEFIELD_SHADOW_FIELDS = [
  "schema_version",
  "processing_mode",
  "evidence_mode",
  "historical",
  "production_ready",
  "automated_response_allowed",
  "source_type",
  "measurement_scope",
  "sample_uid",
  "input_sha256",
  "capture_scope_sha256",
  "timestamp",
  "ingested_at_utc",
  "source",
  "ibdev",
  "interface",
  "operstate",
  "carrier",
  "rx_packets",
  "tx_packets",
  "rx_bytes",
  "tx_bytes",
  "rx_errors",
  "tx_errors",
  "delta_rx_packets",
  "delta_tx_packets",
  "delta_rx_bytes",
  "delta_tx_bytes",
  "delta_rx_errors",
  "delta_tx_errors",
  "delta_status",
  "sample_interval_seconds",
] as const;

const counters = [
  "rx_packets",
  "tx_packets",
  "rx_bytes",
  "tx_bytes",
  "rx_errors",
  "tx_errors",
] as const;

const deltaStates = new Set([
  "first_sample",
  "interface_changed",
  "sample_gap",
  "unavailable",
  "baseline_unavailable",
  "counter_decreased",
  "computed",
]);

const object = (v: unknown): v is Obj =>
  v !== null && typeof v === "object" && !Array.isArray(v);

const hash = (v: unknown): v is string =>
  typeof v === "string" && /^[a-f0-9]{64}$/.test(v);

const date = (v: unknown): v is string =>
  typeof v === "string" && Number.isFinite(Date.parse(v));

const name = (v: unknown): v is string =>
  typeof v === "string" && v.trim().length > 0 && v.length <= 512;

const uint = (v: unknown): v is number =>
  typeof v === "number" &&
  Number.isSafeInteger(v) &&
  v >= 0;

const nullableUint = (v: unknown): v is number | null =>
  v === null || uint(v);

const nullableName = (v: unknown): v is string | null =>
  v === null || name(v);

type ValidatedMeasurement = {
  ibdev: string;
  interface: string | null;
  operstate: string | null;
  carrier: 0 | 1 | null;
  rx_packets: number | null;
  tx_packets: number | null;
  rx_bytes: number | null;
  tx_bytes: number | null;
  rx_errors: number | null;
  tx_errors: number | null;
  delta_rx_packets: number | null;
  delta_tx_packets: number | null;
  delta_rx_bytes: number | null;
  delta_tx_bytes: number | null;
  delta_rx_errors: number | null;
  delta_tx_errors: number | null;
  delta_status: Record<(typeof counters)[number], string>;
  sample_interval_seconds: number | null;
};

function validateMeasurement(d: Obj): asserts d is Obj & ValidatedMeasurement {
  if (!name(d.ibdev)) throw new Error("Invalid ibdev");
  if (!nullableName(d.interface)) throw new Error("Invalid interface");
  if (!nullableName(d.operstate)) throw new Error("Invalid operstate");

  if (!(d.carrier === null || d.carrier === 0 || d.carrier === 1)) {
    throw new Error("Invalid carrier");
  }

  for (const key of counters) {
    if (!nullableUint(d[key])) throw new Error(`Invalid counter: ${key}`);
  }

  if (!object(d.delta_status)) throw new Error("Missing delta status");

  for (const key of counters) {
    const status = d.delta_status[key];
    const delta = d[`delta_${key}`];

    if (typeof status !== "string" || !deltaStates.has(status)) {
      throw new Error(`Invalid delta status: ${key}`);
    }

    if (status === "computed") {
      if (!uint(delta)) throw new Error(`Computed delta invalid: ${key}`);
    } else if (delta !== null) {
      throw new Error(`Non-computed delta must remain null: ${key}`);
    }
  }

  const interval = d.sample_interval_seconds;
  if (
    !(
      interval === null ||
      (typeof interval === "number" &&
        Number.isFinite(interval) &&
        interval > 0)
    )
  ) {
    throw new Error("Invalid sample interval");
  }
}

export function bluefieldShadowDocuments(value: unknown): BluefieldShadowDoc[] {
  if (
    !object(value) ||
    value.timed_out !== false ||
    !object(value._shards) ||
    value._shards.failed !== 0 ||
    !object(value.hits)
  ) {
    throw new Error("Incomplete BlueField shadow search");
  }

  const hits = value.hits;
  if (
    !object(hits.total) ||
    hits.total.relation !== "eq" ||
    !uint(hits.total.value) ||
    !Array.isArray(hits.hits) ||
    hits.total.value !== hits.hits.length ||
    hits.hits.length > 100
  ) {
    throw new Error("BlueField shadow result incomplete or over limit");
  }

  const result: BluefieldShadowDoc[] = [];
  const ids = new Set<string>();

  for (const hit of hits.hits) {
    if (!object(hit) || !name(hit._id) || !object(hit._source)) {
      throw new Error("Invalid BlueField shadow hit");
    }

    const d = hit._source;

    if (
      d.schema_version !== "shadow-bluefield-1" ||
      d.processing_mode !== "shadow" ||
      d.evidence_mode !== "archived_normalized_replay" ||
      d.historical !== true ||
      d.production_ready !== false ||
      d.automated_response_allowed !== false ||
      d.source_type !== "bluefield" ||
      d.measurement_scope !== "host_interface_counters" ||
      !hash(d.sample_uid) ||
      !hash(d.input_sha256) ||
      !hash(d.capture_scope_sha256) ||
      !date(d.timestamp) ||
      !date(d.ingested_at_utc) ||
      !object(d.source)
    ) {
      throw new Error("Invalid BlueField shadow identity/safety flags");
    }

    const source = d.source;
    if (
      !name(source.cluster_id) ||
      source.topic !== "shadow-bluefield-input-v1" ||
      !uint(source.partition) ||
      !uint(source.offset)
    ) {
      throw new Error("Invalid BlueField shadow source coordinates");
    }

    validateMeasurement(d);

    if (ids.has(hit._id)) throw new Error("Duplicate BlueField shadow document id");
    ids.add(hit._id);

    // Explicit projection: do not expose raw_event, capture_scope or unknown fields.
    result.push({
      id: hit._id,
      schema_version: "shadow-bluefield-1",
      processing_mode: "shadow",
      evidence_mode: "archived_normalized_replay",
      historical: true,
      production_ready: false,
      automated_response_allowed: false,
      source_type: "bluefield",
      measurement_scope: "host_interface_counters",
      sample_uid: d.sample_uid,
      input_sha256: d.input_sha256,
      capture_scope_sha256: d.capture_scope_sha256,
      timestamp: d.timestamp,
      ingested_at_utc: d.ingested_at_utc,
      source: {
        cluster_id: source.cluster_id,
        topic: "shadow-bluefield-input-v1",
        partition: source.partition,
        offset: source.offset,
      },
      ibdev: d.ibdev,
      interface: d.interface,
      operstate: d.operstate,
      carrier: d.carrier,
      rx_packets: d.rx_packets,
      tx_packets: d.tx_packets,
      rx_bytes: d.rx_bytes,
      tx_bytes: d.tx_bytes,
      rx_errors: d.rx_errors,
      tx_errors: d.tx_errors,
      delta_rx_packets: d.delta_rx_packets,
      delta_tx_packets: d.delta_tx_packets,
      delta_rx_bytes: d.delta_rx_bytes,
      delta_tx_bytes: d.delta_tx_bytes,
      delta_rx_errors: d.delta_rx_errors,
      delta_tx_errors: d.delta_tx_errors,
      delta_status: {
        rx_packets: d.delta_status.rx_packets,
        tx_packets: d.delta_status.tx_packets,
        rx_bytes: d.delta_status.rx_bytes,
        tx_bytes: d.delta_status.tx_bytes,
        rx_errors: d.delta_status.rx_errors,
        tx_errors: d.delta_status.tx_errors,
      },
      sample_interval_seconds: d.sample_interval_seconds,
    });
  }

  result.sort(
    (a, b) =>
      Date.parse(a.timestamp) - Date.parse(b.timestamp) ||
      a.ibdev.localeCompare(b.ibdev) ||
      a.source.offset - b.source.offset,
  );

  return result;
}
