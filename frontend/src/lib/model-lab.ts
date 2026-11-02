import { createHash } from "node:crypto";

const INDEX = "edrxdr-ai-lab-v1";
const MODELS = {
  dfp: ["EDRXDR-LAB-DUO-generic_user", "1", "75bd72e5120acdb7fc5888d94be28a3de8bcaddf49a1b74937512de3eda14cec"],
  ransomware: ["ransomw-model-short-rf", "1", "9a03cab79a239da935828911bd101a2055337c768737b02b819bc13bed6a627f"],
};
const fields = "schema_version observation_id pipeline_id model_name model_version model_sha256 processing_mode source_type source_artifact_sha256 source_record_ref adapter_sha256 observed_at_utc scores details production_ready automated_response_allowed quality_metrics_evaluated".split(" ");
const identityFields = "schema_version pipeline_id model_name model_version model_sha256 source_type source_artifact_sha256 source_record_ref adapter_sha256".split(" ");
type Obj = Record<string, unknown>;
function object(v: unknown): v is Obj { return !!v && typeof v === "object" && !Array.isArray(v); }
function requireValue(ok: unknown): asserts ok { if (!ok) throw new Error("Invalid lab response"); }
function keys(v: Obj, wanted: string[]) { return Object.keys(v).sort().join("|") === [...wanted].sort().join("|"); }
function hex(v: unknown) { return typeof v === "string" && /^[0-9a-f]{64}$/.test(v); }
function number(v: unknown): v is number { return typeof v === "number" && Number.isFinite(v); }
function canonical(v: Obj) { return JSON.stringify(Object.fromEntries(Object.keys(v).sort().map(k => [k, v[k]]))); }

export function validateObservation(value: unknown): Obj {
  requireValue(object(value) && keys(value, fields));
  const v = value;
  requireValue(v.schema_version === "morpheus-lab-observation-1" && v.processing_mode === "dataset_replay");
  requireValue(v.pipeline_id === "dfp" || v.pipeline_id === "ransomware");
  const model = MODELS[v.pipeline_id];
  requireValue([v.model_name, v.model_version, v.model_sha256].every((x, i) => x === model[i]));
  requireValue([v.observation_id, v.model_sha256, v.source_artifact_sha256, v.adapter_sha256].every(hex));
  requireValue(v.source_type === "model_result_artifact");
  requireValue(v.production_ready === false && v.automated_response_allowed === false && v.quality_metrics_evaluated === false);
  requireValue(typeof v.observed_at_utc === "string" && /(?:Z|\+00:00)$/.test(v.observed_at_utc) && Number.isFinite(Date.parse(v.observed_at_utc)));
  requireValue(object(v.scores) && object(v.details));
  const scores = v.scores, details = v.details;
  if (v.pipeline_id === "dfp") {
    requireValue(keys(scores, ["mean_abs_z", "max_abs_z"]));
    requireValue(number(scores.mean_abs_z) && number(scores.max_abs_z) && scores.mean_abs_z >= 0 && scores.max_abs_z >= scores.mean_abs_z);
    requireValue(keys(details, ["execution_backend", "input_scope"]) && details.execution_backend === "gpu" && details.input_scope === "duo_sample_result");
    requireValue(typeof v.source_record_ref === "string" && /^csv-row:[1-9][0-9]*$/.test(v.source_record_ref));
  } else {
    requireValue(keys(scores, ["output_0", "output_1"]));
    requireValue(number(scores.output_0) && number(scores.output_1) && scores.output_0 >= 0 && scores.output_0 <= 1 && scores.output_1 >= 0 && scores.output_1 <= 1 && Math.abs(scores.output_0 + scores.output_1 - 1) <= 1e-4);
    requireValue(keys(details, ["execution_backend", "input_scope", "class_mapping", "input_features", "snapshots", "feature_order_sha256"]));
    requireValue(details.execution_backend === "cpu" && details.input_scope === "nvidia_training_csv_window" && details.class_mapping === "unverified" && details.input_features === 297);
    requireValue(details.feature_order_sha256 === "ff504a45944322a33a148eb34e5a0e165d14bafca4e06119078f150daf34839b");
    const s = details.snapshots;
    requireValue(Array.isArray(s) && s.length === 3 && s.every((n, i) => Number.isSafeInteger(n) && n >= 0 && n === s[0] + i));
    requireValue(v.source_record_ref === "json-object:0");
  }
  const identity = Object.fromEntries(identityFields.map(k => [k, v[k]]));
  requireValue(createHash("sha256").update(canonical(identity)).digest("hex") === v.observation_id);
  return v;
}

export function parseLabQuery(url: string) {
  const params = new URL(url).searchParams;
  for (const k of params.keys()) requireValue(["page", "pipeline"].includes(k) && params.getAll(k).length === 1);
  const page = params.get("page") ?? "1", pipeline = params.get("pipeline") ?? "all";
  requireValue(/^[1-9][0-9]?$/.test(page) && Number(page) <= 20);
  requireValue(["all", "dfp", "ransomware"].includes(pipeline));
  return { page: Number(page), pipeline };
}

export function projectLabResult(raw: unknown, query: { page: number; pipeline: string }) {
  requireValue(object(raw) && raw.timed_out === false && object(raw._shards));
  requireValue(raw._shards.failed === 0 && Number.isSafeInteger(raw._shards.total) && (raw._shards.total as number) > 0 && raw._shards.successful === raw._shards.total);
  requireValue(object(raw.hits) && object(raw.hits.total) && raw.hits.total.relation === "eq");
  const count = raw.hits.total.value;
  requireValue(typeof count === "number" && Number.isSafeInteger(count) && count >= 0 && count <= 1000);
  requireValue(Array.isArray(raw.hits.hits) && raw.hits.hits.length === count);
  const ids = new Set();
  const events = raw.hits.hits.map(hit => {
    requireValue(object(hit) && hit._index === INDEX);
    const event = validateObservation(hit._source);
    requireValue(hit._id === event.observation_id && !ids.has(hit._id)); ids.add(hit._id);
    return event;
  }).sort((a, b) => String(a.observation_id).localeCompare(String(b.observation_id)));
  const filtered = events.filter(e => query.pipeline === "all" || e.pipeline_id === query.pipeline);
  return { source: INDEX, schema_version: "morpheus-lab-observation-1", processing_mode: "dataset_replay",
    production_ready: false, automated_response_allowed: false, quality_metrics_evaluated: false,
    complete: true, total: filtered.length, batch_total: events.length, page: query.page, page_size: 50,
    pipeline: query.pipeline, counts: { dfp: events.filter(e => e.pipeline_id === "dfp").length, ransomware: events.filter(e => e.pipeline_id === "ransomware").length },
    observations: filtered.slice((query.page - 1) * 50, query.page * 50) };
}

export async function readModelLab(query: { page: number; pipeline: string }, fetcher: typeof fetch = fetch) {
  const response = await fetcher("http://127.0.0.1:9200/edrxdr-ai-lab-v1/_search?allow_partial_search_results=false", {
    method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ size: 1000, track_total_hits: true, query: { match_all: {} } }),
    cache: "no-store", redirect: "error", signal: AbortSignal.timeout(10000)
  });
  requireValue(response.ok && response.headers.get("content-type")?.includes("application/json"));
  requireValue(response.body && Number(response.headers.get("content-length") || 0) <= 2 * 1024 * 1024);
  const reader = response.body.getReader(), chunks: Uint8Array[] = []; let bytes = 0;
  try {
    while (true) { const part = await reader.read(); if (part.done) break;
      bytes += part.value.byteLength; requireValue(bytes <= 2 * 1024 * 1024); chunks.push(part.value); }
  } finally { await reader.cancel().catch(() => {}); reader.releaseLock(); }
  return projectLabResult(JSON.parse(Buffer.concat(chunks).toString("utf8")), query);
}
