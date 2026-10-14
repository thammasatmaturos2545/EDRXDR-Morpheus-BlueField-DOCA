export type EventRow = {
  key: string; id: string | null; timestamp: string | null; host: string | null;
  rule: string | null; description: string | null; level: number | null;
  score: number | null; label: string | null; engine: string | null;
  uid: string | null; hash: string | null; srcIp: string | null; dstIp: string | null;
};
export type Source = "wazuh" | "ai";
export function demoHref(value: string): string | null {
  const run = value.trim();
  return /^d[0-9]{8}t[0-9]{6}-[0-9a-f]{8}$/.test(run) ? `/demo?run=${encodeURIComponent(run)}` : null;
}
export function record(v: unknown): v is Record<string, unknown> {
  return !!v && typeof v === "object" && !Array.isArray(v);
}
function str(v: unknown) { return typeof v === "string" && v.trim() && v !== "unknown" ? v : null; }
function num(v: unknown) { return typeof v === "number" && Number.isFinite(v) ? v : null; }
export function parseEvents(input: unknown, source: Source): EventRow[] {
  if (!record(input) || input.error) throw new Error("Invalid response");
  const items = input[source === "wazuh" ? "alerts" : "events"];
  if (!Array.isArray(items) || items.length > 100 || !items.every(record)) throw new Error("Invalid event list");
  // Never silently count replay/simulator/unclassified documents as live AI.
  if (source === "ai" && items.some(e => e.processing_mode !== "live" || typeof e.analysis_engine !== "string" || !e.analysis_engine.trim() || /simulat|replay|shadow/i.test(e.analysis_engine))) throw new Error("Unverified live scope");
  return items.map((e, i) => {
    const value = num(source === "wazuh" ? e.rule_level : e.wazuh_rule_level);
    const stamp = str(e.timestamp);
    return {
      key: `${source}:${i}`, id: str(e.id), timestamp: stamp && Number.isFinite(Date.parse(stamp)) ? stamp : null,
      host: str(e.agent_name), rule: str(source === "wazuh" ? e.rule_id : e.wazuh_rule_id),
      description: str(e.description), level: value !== null && Number.isInteger(value) && value >= 0 && value <= 15 ? value : null,
      score: source === "ai" ? num(e.threat_score) : null,
      label: source === "ai" ? str(e.threat_class) : null, engine: source === "ai" ? str(e.analysis_engine) : null,
      uid: str(e.event_uid), hash: str(e.raw_sha256), srcIp: str(e.src_ip), dstIp: str(e.dst_ip),
    };
  });
}
export function serviceState(value: unknown) {
  return ["online", "offline", "waiting", "unknown"].includes(String(value)) ? String(value) : "unknown";
}
export function filterEvents(rows: EventRow[], query: string, minimum: number, hours: number, now: number) {
  const needle = query.trim().toLowerCase();
  return rows.filter(e => (!needle || [e.id, e.uid, e.host, e.rule, e.description, e.srcIp, e.dstIp].some(v => v?.toLowerCase().includes(needle)))
    && (minimum === 0 || (e.level !== null && e.level >= minimum))
    && (hours === 0 || (e.timestamp !== null && Date.parse(e.timestamp) <= now && Date.parse(e.timestamp) >= now - hours * 3600000)));
}
