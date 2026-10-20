export type ObservedEndpoint = {
  id: string;
  agent_id: string;
  host: string;
  ip: string;
  os: string;
  status: "unknown";
  risk: null;
  last_seen: string | null;
  department: string;
  user: string;
  agent_version: string;
};

function text(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function timestamp(value: unknown): string | null {
  const raw = text(value);
  if (!raw) return null;

  // Wazuh commonly uses timezone offsets such as +0000.
  const normalized = raw.replace(
    /([+-]\d{2})(\d{2})$/,
    "$1:$2"
  );

  const ms = Date.parse(normalized);
  return Number.isFinite(ms)
    ? new Date(ms).toISOString()
    : null;
}

export function buildObservedEndpoints(
  rows: unknown
): ObservedEndpoint[] {
  if (!Array.isArray(rows)) return [];

  const found = new Map<string, ObservedEndpoint>();

  for (const row of rows) {
    if (!row || typeof row !== "object" || Array.isArray(row)) {
      continue;
    }

    const r = row as Record<string, unknown>;
    const agentId = text(r.agent_id);

    // Exclude manager-local ID 000 and rows without a valid ID.
    if (!/^\d{3}$/.test(agentId) || agentId === "000") {
      continue;
    }

    const host = text(r.agent_name);
    if (!host) continue;

    const ip = text(r.agent_ip);
    const seen = timestamp(r.timestamp ?? r["@timestamp"]);
    const existing = found.get(agentId);

    if (!existing) {
      found.set(agentId, {
        id: `wazuh-agent-${agentId}`,
        agent_id: agentId,
        host,
        ip: ip || "Unknown",
        os: "Unknown",
        status: "unknown",
        risk: null,
        last_seen: seen,
        department: "Not provided",
        user: "Not provided",
        agent_version: "Not provided",
      });
      continue;
    }

    // Preserve the most recent observed information per Agent ID.
    if (seen && (!existing.last_seen || seen > existing.last_seen)) {
      existing.last_seen = seen;
      existing.host = host;
      if (ip) existing.ip = ip;
    }
  }

  return [...found.values()].sort((a, b) =>
    a.agent_id.localeCompare(b.agent_id)
  );
}
