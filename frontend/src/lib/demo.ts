import { documents, type Doc } from "./shadow";
export const RUN = /^d[0-9]{8}t[0-9]{6}-[0-9a-f]{8}$/;
const obj = (v: unknown): v is Doc => !!v && typeof v === "object" && !Array.isArray(v);
const date = (v: unknown): v is string => typeof v === "string" && Number.isFinite(Date.parse(v));
export function parseDemo(value: unknown, run: string) {
  if (!RUN.test(run) || !obj(value) || value.timed_out !== false || !obj(value._shards) || value._shards.failed !== 0 || !obj(value.hits)) throw new Error("Incomplete search");
  const hits = value.hits;
  if (!obj(hits.total) || hits.total.relation !== "eq" || typeof hits.total.value !== "number" || !Number.isSafeInteger(hits.total.value) || hits.total.value < 0 || !Array.isArray(hits.hits) || hits.hits.length !== Math.min(hits.total.value, 20)) throw new Error("Invalid window");
  const events = hits.hits.map((hit: unknown) => {
    if (!obj(hit) || typeof hit._id !== "string" || !obj(hit._source)) throw new Error("Invalid hit");
    const d = hit._source;
    if (d.doc_type !== "event" || d.run_id !== run || d.production_ready !== false || d.automated_response_allowed !== false || d.indexed_at_meaning !== "index_request_started" || !date(d.indexed_at_utc)) throw new Error("Invalid demo scope");
    const rows = documents({ timed_out: false, _shards: { failed: 0 }, hits: { total: { relation: "eq", value: 1 }, hits: [{ _source: d.result }] } }, "severity");
    const result = [...rows.values()][0];
    const latency = Date.parse(String(result.scored_at_utc)) - Date.parse(String(result.captured_at_utc));
    if (latency < 0 || Date.parse(d.indexed_at_utc) < Date.parse(String(result.scored_at_utc))) throw new Error("Invalid timestamps");
    return { id: hit._id, result, index_request_started_at: d.indexed_at_utc, capture_to_score_ms: latency };
  });
  return { total: hits.total.value, shown: events.length, window: "latest_20" as const, events };
}
export function parseWorker(value: unknown, run: string) {
  if (!obj(value) || value.found !== true || !obj(value._source)) throw new Error("Missing worker");
  const d = value._source;
  if (d.doc_type !== "worker" || d.run_id !== run || d.worker !== "bounded-morpheus-severity-demo" || d.production_ready !== false || d.automated_response_allowed !== false || !date(d.observed_at_utc) || !date(d.boundary_recorded_at_utc) || !["waiting", "scoring", "stopped", "failed"].includes(String(d.phase)) || !obj(d.session_counts)) throw new Error("Invalid worker");
  const counts = Object.fromEntries(["captured", "scored", "indexed"].map(key => {
    const n = (d.session_counts as Doc)[key];
    if (typeof n !== "number" || !Number.isSafeInteger(n) || n < 0) throw new Error("Invalid counter");
    return [key, n];
  }));
  const lag: Record<string, number | null> = {};
  if (!obj(d.queue_lag)) throw new Error("Missing lag");
  for (const key of ["capture", "score", "index"]) {
    const n = d.queue_lag[key];
    if (!(n === null || typeof n === "number" && Number.isSafeInteger(n) && n >= 0)) throw new Error("Invalid lag");
    lag[key] = n;
  }
  return { queue_lag: lag, name: String(d.worker), phase: String(d.phase), observed_at_utc: d.observed_at_utc, boundary_recorded_at_utc: d.boundary_recorded_at_utc, session_counts: counts };
}
