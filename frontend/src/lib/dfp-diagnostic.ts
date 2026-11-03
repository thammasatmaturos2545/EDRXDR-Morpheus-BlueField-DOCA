import { createHash } from "node:crypto";
import { constants } from "node:fs";
import { open } from "node:fs/promises";

export const DFP_BUNDLE_PATH = "/mnt/nexus-copilot-mQTssj/dfp-diagnostic-published-v1/diagnostic.json";
export const DFP_MODEL = "ecacecb3128f9ac6987315e2a1861fb02ac873f9fc42ddc11798a9fc0c25157e";
export const DFP_CAPTURE = "6e8478a917eebe277e725b746c08b481f34f4b805f7a7d6e24a096ed1c68510f";
export const DFP_REPORT = "e88839c64f9221b88c653126359046d2a053507f82653b249861eef13fdd6fc1";
export const DFP_FEATURES = "90a5d3871341a6580bff524ff40edf75cc0cc4add1ea6d2841b2b895165d1fd2";
export const MAX_DFP_BYTES = 128 * 1024;
type Obj = Record<string, unknown>;
type Observation = { observation_id: string; window_start_utc: string; record_count: number;
  reconstruction_score: number; nominally_inside_observation_interval: boolean; syscollector_record_count: number;
  coverage_status: "unknown"; window_complete: false };
const topFields = "schema_version processing_mode source_type agent_id identity_basis model_name model_version model_sha256 source_capture_sha256 features_sha256 diagnostic_report_sha256 feature_contract score_semantics window_seconds source_coverage_accepted quality_metrics_evaluated threshold_selected production_ready automated_response_allowed live_deployed bert_replaced observations".split(" ");
const rowFields = "observation_id window_start_utc record_count reconstruction_score nominally_inside_observation_interval syscollector_record_count coverage_status window_complete".split(" ");
function object(v: unknown): v is Obj { return !!v && typeof v === "object" && !Array.isArray(v); }
function requireValue(v: unknown): asserts v { if (!v) throw new Error("Invalid DFP diagnostic evidence"); }
function keys(v: Obj, wanted: string[]) { return Object.keys(v).sort().join("|") === [...wanted].sort().join("|"); }
function uint(v: unknown): v is number { return typeof v === "number" && Number.isSafeInteger(v) && v >= 0; }
function finite(v: unknown): v is number { return typeof v === "number" && Number.isFinite(v) && v >= 0; }
function canonical(v: Obj) { return JSON.stringify(Object.fromEntries(Object.keys(v).sort().map(k => [k, v[k]]))); }
export function observationId(window: string) {
  return createHash("sha256").update(canonical({ schema_version: "wazuh-dfp-diagnostic-bundle-1",
    model_sha256: DFP_MODEL, source_capture_sha256: DFP_CAPTURE, features_sha256: DFP_FEATURES,
    diagnostic_report_sha256: DFP_REPORT, window_start_utc: window })).digest("hex");
}
export function validateDfpBundle(value: unknown) {
  requireValue(object(value) && keys(value, topFields));
  const v = value;
  requireValue(v.schema_version === "wazuh-dfp-diagnostic-bundle-1" && v.processing_mode === "offline_frozen_cpu_diagnostic" &&
    v.source_type === "frozen_archive_window_scores" && v.agent_id === "003" && v.identity_basis === "manager_agent_id_not_physical_device_verified");
  requireValue(v.model_name === "EDRXDR-ARCHIVE-CPU-PROTOTYPE" && v.model_version === "1" && v.model_sha256 === DFP_MODEL &&
    v.source_capture_sha256 === DFP_CAPTURE && v.features_sha256 === DFP_FEATURES && v.diagnostic_report_sha256 === DFP_REPORT &&
    v.feature_contract === "wazuh-archive-cpu-prototype-1" && v.window_seconds === 300 &&
    v.score_semantics === "mean_squared_reconstruction_error_transformed_numeric_features");
  for (const k of ["source_coverage_accepted", "quality_metrics_evaluated", "threshold_selected", "production_ready",
    "automated_response_allowed", "live_deployed", "bert_replaced"]) requireValue(v[k] === false);
  requireValue(Array.isArray(v.observations) && v.observations.length === 12);
  const ids = new Set<string>(); let previous = -Infinity, total = 0, interior = 0;
  const rows: Observation[] = v.observations.map((raw: unknown) => {
    requireValue(object(raw) && keys(raw, rowFields));
    requireValue(typeof raw.window_start_utc === "string" && /^\d{4}-\d\d-\d\dT\d\d:\d\d:00\+00:00$/.test(raw.window_start_utc));
    const time = Date.parse(raw.window_start_utc);
    requireValue(Number.isFinite(time) && time % 300000 === 0 && time > previous &&
      new Date(time).toISOString() === raw.window_start_utc.replace("+00:00", ".000Z")); previous = time;
    requireValue(typeof raw.observation_id === "string" && raw.observation_id === observationId(raw.window_start_utc) && !ids.has(raw.observation_id));
    ids.add(raw.observation_id);
    requireValue(uint(raw.record_count) && raw.record_count > 0 && finite(raw.reconstruction_score) &&
      uint(raw.syscollector_record_count) && raw.syscollector_record_count <= raw.record_count &&
      typeof raw.nominally_inside_observation_interval === "boolean" && raw.coverage_status === "unknown" && raw.window_complete === false);
    total += raw.record_count; interior += Number(raw.nominally_inside_observation_interval);
    return { observation_id: raw.observation_id, window_start_utc: raw.window_start_utc, record_count: raw.record_count,
      reconstruction_score: raw.reconstruction_score, nominally_inside_observation_interval: raw.nominally_inside_observation_interval,
      syscollector_record_count: raw.syscollector_record_count, coverage_status: "unknown", window_complete: false };
  });
  requireValue(total === 845 && interior === 10);
  return { ...v, observations: rows, read_complete: true, total: rows.length, record_total: total,
    nominal_interior_windows: interior, boundary_windows: rows.length - interior };
}

export async function readDfpDiagnostic(expectedHash: string) {
  requireValue(/^[0-9a-f]{64}$/.test(expectedHash));
  const handle = await open(DFP_BUNDLE_PATH, constants.O_RDONLY | constants.O_NOFOLLOW);
  try {
    const before = await handle.stat();
    requireValue(before.isFile() && before.nlink === 1 && before.size > 0 && before.size <= MAX_DFP_BYTES &&
      (before.mode & 0o077) === 0 && typeof process.getuid === "function" && before.uid === process.getuid());
    const buffer = Buffer.alloc(MAX_DFP_BYTES + 1);
    const part = await handle.read(buffer, 0, buffer.length, 0);
    const after = await handle.stat();
    requireValue(part.bytesRead === before.size && before.size === after.size && before.ino === after.ino &&
      before.dev === after.dev && before.mtimeMs === after.mtimeMs);
    const raw = buffer.subarray(0, part.bytesRead);
    requireValue(createHash("sha256").update(raw).digest("hex") === expectedHash);
    return { ...validateDfpBundle(JSON.parse(raw.toString("utf8"))), artifact_sha256: expectedHash };
  } finally { await handle.close(); }
}
