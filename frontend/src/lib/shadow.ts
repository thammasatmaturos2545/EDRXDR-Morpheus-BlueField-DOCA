export type Doc = Record<string, unknown>;
export type Pair = { key: string; severity: Doc | null; behavioral: Doc | null; status: "matched" | "conflict" | "severity_only" | "behavioral_only" };
export const FIELDS = ["schema_version", "processing_mode", "production_ready", "automated_response_allowed", "event_uid", "source", "raw_sha256", "captured_at_utc", "scored_at_utc", "wazuh_rule_id", "wazuh_rule_level", "high_severity_score", "threshold", "predicted_label", "model_name", "false_positive_candidate", "weak_label_disagreement", "analysis_state", "routing_status", "ae_scored", "ae_ratio", "semantic_novelty", "model_version"];
const object = (v: unknown): v is Doc => v !== null && typeof v === "object" && !Array.isArray(v);
const hash = (v: unknown) => typeof v === "string" && /^[a-f0-9]{64}$/.test(v);
const date = (v: unknown) => typeof v === "string" && Number.isFinite(Date.parse(v));
const integer = (v: unknown) => typeof v === "number" && Number.isSafeInteger(v) && v >= 0;
const name = (v: unknown) => typeof v === "string" && v.trim().length > 0 && v.length <= 512;
const scoredStates = new Set(["baseline_consistent", "behavioral_anomaly", "behavioral_anomaly+semantic_novelty", "semantic_novelty"]);
const unscoredStates = new Set(["limited_history", "novel_cohort", "fallback_supported", "insufficient_feature_diversity", "no_temporal_dev_evidence"]);
const routes = new Set(["local_model", "limited_history", "novel_cohort", "fallback_supported"]);

// Fail closed instead of showing partial counts as a complete pilot.
export function documents(value: unknown, kind: "severity" | "behavioral"): Map<string, Doc> {
  if (!object(value) || value.timed_out !== false || !object(value._shards) || value._shards.failed !== 0 || !object(value.hits)) throw new Error("Incomplete search");
  const hits = value.hits;
  if (!object(hits.total) || hits.total.relation !== "eq" || !integer(hits.total.value) || !Array.isArray(hits.hits) || hits.total.value !== hits.hits.length || hits.hits.length > 500) throw new Error("Pilot limit or incomplete results");
  const rows = new Map<string, Doc>();
  for (const hit of hits.hits) {
    if (!object(hit) || !object(hit._source)) throw new Error("Invalid document");
    const d = hit._source;
    const s = d.source;
    if (d.schema_version !== `shadow-${kind}-1` || d.processing_mode !== "shadow" || d.production_ready !== false || d.automated_response_allowed !== false || !hash(d.event_uid) || !hash(d.raw_sha256) || !date(d.captured_at_utc) || !date(d.scored_at_utc) || !object(s) || typeof s.cluster_id !== "string" || !s.cluster_id || s.topic !== "wazuh-alerts" || !integer(s.partition) || !integer(s.offset) || !(s.timestamp_ms === null || integer(s.timestamp_ms))) throw new Error("Invalid shadow identity");
    if (!(name(d.wazuh_rule_id) || integer(d.wazuh_rule_id)) || !(d.wazuh_rule_level === null || integer(d.wazuh_rule_level) && Number(d.wazuh_rule_level) <= 15)) throw new Error("Invalid rule");
    if (kind === "severity") {
      const score = d.high_severity_score;
      const knownLevel = d.wazuh_rule_level !== null;
      if (!name(d.model_name) || typeof score !== "number" || !Number.isFinite(score) || score < 0 || score > 1 || d.threshold !== 0.5 || d.predicted_label !== (score >= 0.5 ? "high_severity" : "low_severity") || d.false_positive_candidate !== (knownLevel ? score >= 0.5 && Number(d.wazuh_rule_level) < 7 : null) || d.weak_label_disagreement !== (knownLevel ? (score >= 0.5) !== (Number(d.wazuh_rule_level) >= 7) : null)) throw new Error("Invalid severity");
    } else {
      if (!name(d.model_version) || typeof d.ae_scored !== "boolean" || typeof d.semantic_novelty !== "boolean" || typeof d.analysis_state !== "string" || typeof d.routing_status !== "string" || !routes.has(d.routing_status)) throw new Error("Invalid behavioral");
      if (d.ae_scored ? typeof d.ae_ratio !== "number" || !Number.isFinite(d.ae_ratio) || d.ae_ratio < 0 : d.ae_ratio !== null) throw new Error("Invalid AE coverage");
      if (d.ae_scored ? !scoredStates.has(d.analysis_state) || d.routing_status !== "local_model" : !unscoredStates.has(d.analysis_state)) throw new Error("Inconsistent AE state");
      if (!d.ae_scored && d.routing_status === "local_model" && !["insufficient_feature_diversity", "no_temporal_dev_evidence"].includes(d.analysis_state)) throw new Error("Inconsistent local model state");
      if (d.routing_status !== "local_model" && d.analysis_state !== d.routing_status) throw new Error("Inconsistent routing state");
      if (d.ae_scored && (d.analysis_state.includes("semantic_novelty") !== d.semantic_novelty)) throw new Error("Inconsistent behavioral result");
    }
    const key = JSON.stringify([d.event_uid, s.cluster_id, s.topic, s.partition, s.offset]);
    if (rows.has(key)) throw new Error("Ambiguous duplicate occurrence");
    // Explicit projection: never expose raw log or unknown fields to the browser.
    // Project only validated fields for this model kind. Extra opposite-kind fields
    // could contain arbitrary nested content even if the requested name is allowed.
    const kindFields = kind === "severity"
      ? ["high_severity_score", "threshold", "predicted_label", "model_name", "false_positive_candidate", "weak_label_disagreement"]
      : ["analysis_state", "routing_status", "ae_scored", "ae_ratio", "semantic_novelty", "model_version"];
    const baseFields = ["schema_version", "processing_mode", "production_ready", "automated_response_allowed", "event_uid", "raw_sha256", "captured_at_utc", "scored_at_utc", "wazuh_rule_id", "wazuh_rule_level"];
    const safe = Object.fromEntries([...baseFields, ...kindFields].map(f => [f, d[f]]));
    safe.source = { cluster_id: s.cluster_id, topic: s.topic, partition: s.partition, offset: s.offset, timestamp_ms: s.timestamp_ms };
    rows.set(key, safe);
  }
  return rows;
}

export function joinShadow(severity: Map<string, Doc>, behavioral: Map<string, Doc>) {
  const events: Pair[] = [...new Set([...severity.keys(), ...behavioral.keys()])].map(key => {
    const s = severity.get(key) ?? null, b = behavioral.get(key) ?? null;
    const equal = s && b && ["raw_sha256", "captured_at_utc", "wazuh_rule_id", "wazuh_rule_level"].every(f => s[f] === b[f]) && (s.source as Doc).timestamp_ms === (b.source as Doc).timestamp_ms;
    return { key, severity: s, behavioral: b, status: s && b ? (equal ? "matched" : "conflict") : s ? "severity_only" : "behavioral_only" };
  });
  events.sort((a,b) => Date.parse(String((b.severity ?? b.behavioral)?.captured_at_utc)) - Date.parse(String((a.severity ?? a.behavioral)?.captured_at_utc)));
  return { events, counts: { severity: severity.size, behavioral: behavioral.size, matched: events.filter(e => e.status === "matched").length, conflicts: events.filter(e => e.status === "conflict").length, unmatched: events.filter(e => e.status.endsWith("_only")).length, ae_scored: [...behavioral.values()].filter(d => d.ae_scored === true).length, novelty: [...behavioral.values()].filter(d => d.semantic_novelty === true).length, candidates: [...severity.values()].filter(d => d.false_positive_candidate === true).length } };
}
