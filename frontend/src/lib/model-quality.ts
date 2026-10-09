/** Report contracts, not inferred deployment or live-service states. */
export type Metrics = {
  n: number;
  tp: number;
  fp: number;
  tn: number;
  fn: number;
  precision: number | null;
  recall: number | null;
  f1: number | null;
  false_positive_rate: number | null;
};

export const metricNames = ["precision", "recall", "f1", "false_positive_rate"] as const;
export type MetricName = (typeof metricNames)[number];
export type QualityReport = {
  scope: "development_only";
  threshold: number;
  overall: Metrics;
  per_rule: Record<string, Metrics>;
  proposed_limits: Record<MetricName, number>;
  proposed_gate_results: Record<MetricName | "per_rule", boolean>;
  development_numeric_gate_pass: boolean;
  shadow_authorized: boolean;
  production_ready: boolean;
  limitations: string[];
};
export type ParityReport = {
  status: "PASS" | "FAIL";
  rows: number;
  compared_rows: number;
  max_absolute_score_error: number;
  threshold: number;
  checkpoint: string;
  checkpoint_weights_sha256: string;
  dataset_manifest_sha256: string;
  held_out_data_used: boolean;
  raw_event_check: {
    status: "PASS" | "FAIL";
    reconstructed_rows: number;
    held_out_data_used: boolean;
  };
};
export type QualityEvidence = {
  run_id: string;
  checked_at: string;
  source: { quality_sha256: string; parity_sha256: string };
  quality: QualityReport;
  parity: ParityReport;
};

function record(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
function count(value: unknown): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
}
function ratio(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 1;
}
function hash(value: unknown): value is string {
  return typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
}
function metrics(value: unknown): value is Metrics {
  if (!record(value) || !["n", "tp", "fp", "tn", "fn"].every(key => count(value[key]))) return false;
  if (!metricNames.every(key => value[key] === null || ratio(value[key]))) return false;
  return value.n === Number(value.tp) + Number(value.fp) + Number(value.tn) + Number(value.fn);
}
export function isQualityReport(value: unknown): value is QualityReport {
  if (!record(value) || value.scope !== "development_only" || !ratio(value.threshold) || !metrics(value.overall)) return false;
  if (!record(value.per_rule) || !Object.values(value.per_rule).every(metrics)) return false;
  const limits = value.proposed_limits;
  const gates = value.proposed_gate_results;
  if (!record(limits) || !metricNames.every(key => ratio(limits[key]))) return false;
  if (!record(gates) || ![...metricNames, "per_rule"].every(key => typeof gates[key] === "boolean")) return false;
  return ["development_numeric_gate_pass", "shadow_authorized", "production_ready"].every(key => typeof value[key] === "boolean")
    && Array.isArray(value.limitations) && value.limitations.every(item => typeof item === "string");
}
export function isParityReport(value: unknown): value is ParityReport {
  if (!record(value) || !["PASS", "FAIL"].includes(String(value.status))) return false;
  const raw = value.raw_event_check;
  return count(value.rows) && count(value.compared_rows) && value.compared_rows <= value.rows
    && typeof value.max_absolute_score_error === "number" && Number.isFinite(value.max_absolute_score_error) && value.max_absolute_score_error >= 0
    && ratio(value.threshold) && typeof value.checkpoint === "string" && value.checkpoint.length > 0
    && hash(value.checkpoint_weights_sha256) && hash(value.dataset_manifest_sha256)
    && typeof value.held_out_data_used === "boolean" && record(raw)
    && ["PASS", "FAIL"].includes(String(raw.status)) && count(raw.reconstructed_rows)
    && typeof raw.held_out_data_used === "boolean";
}
export function isQualityEvidence(value: unknown): value is QualityEvidence {
  return record(value) && typeof value.run_id === "string" && typeof value.checked_at === "string"
    && record(value.source) && hash(value.source.quality_sha256) && hash(value.source.parity_sha256)
    && isQualityReport(value.quality) && isParityReport(value.parity);
}
