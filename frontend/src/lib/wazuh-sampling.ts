export function selectBalancedWazuhAlerts<
  T extends { agent_id?: unknown }
>(alerts: readonly T[]): T[] {
  const buckets = new Map<string, number[]>();

  for (let i = alerts.length - 1; i >= 0; i--) {
    const raw = alerts[i].agent_id;
    const agent =
      typeof raw === "string" && raw.trim()
        ? raw
        : "unknown";

    if (!buckets.has(agent)) buckets.set(agent, []);
    const bucket = buckets.get(agent)!;
    if (bucket.length < 25) bucket.push(i);
  }

  const selected = new Set<number>();

  for (let round = 0; round < 25 && selected.size < 100; round++) {
    for (const bucket of buckets.values()) {
      if (selected.size >= 100) break;
      const index = bucket[round];
      if (index !== undefined) selected.add(index);
    }
  }

  for (let i = alerts.length - 1; i >= 0 && selected.size < 100; i--) {
    selected.add(i);
  }

  return [...selected]
    .sort((a, b) => b - a)
    .map((index) => alerts[index]);
}
