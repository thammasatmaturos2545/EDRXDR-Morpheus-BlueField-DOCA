import { createHash } from "node:crypto";
import { validateNexusAi, type Obj } from "./nexus-soc";

export const LOOKUP_INDEX = "edrxdr-wazuh-uid-lookup-v1";
export type LookupStatus = "matched" | "not_found" | "conflict" | "unavailable" | "source_unavailable";
export type SourceRef = { uid: string; index: string; id: string };
export type LookupResult = { event_uid: string; status: LookupStatus; source: "uid_lookup"; alert?: Obj };
const uidPattern = /^[0-9a-f]{64}$/;
const indexPattern = /^wazuh-alerts-4\.x-\d{4}\.\d{2}\.\d{2}$/;
const isObj = (v: unknown): v is Obj => !!v && typeof v === "object" && !Array.isArray(v);
const hash = (s: string) => createHash("sha256").update(s, "utf8").digest("hex");
const part = (v: unknown): string | null => typeof v === "string" ? v.trim() || null :
  typeof v === "number" && Number.isSafeInteger(v) ? String(v) : null;
const text = (v: unknown): string | null => typeof v === "string" && v.trim() ? v.trim() : null;
const list = (v: unknown) => Array.isArray(v) ? v.filter((x): x is string => typeof x === "string").slice(0, 100) : [];

export function canonicalWazuhUid(raw: unknown): string | null {
  if (!isObj(raw) || !isObj(raw.manager) || !isObj(raw.agent)) return null;
  const parts = [part(raw.manager.name), part(raw.agent.id), part(raw.id)];
  if (parts.some(p => p === null)) return null;
  if ((parts as string[]).some(p => Buffer.from(p, "utf8").toString("utf8") !== p)) return null;
  return hash("wazuh-v1|" + (parts as string[]).map(p => `${Buffer.byteLength(p, "utf8")}:${p}`).join("|"));
}

export function validateRefs(refs: SourceRef[]): void {
  if (!Array.isArray(refs) || refs.length > 100) throw new Error("Invalid references");
  for (const r of refs) {
    if (!uidPattern.test(r.uid) || !indexPattern.test(r.index) || typeof r.id !== "string" ||
        !r.id || [...r.id].length > 512) throw new Error("Invalid reference");
  }
}

export function lookupQuery(uids: string[]): string {
  if (!uids.length || uids.length > 100 || new Set(uids).size !== uids.length || uids.some(u => !uidPattern.test(u))) {
    throw new Error("Invalid UID request");
  }
  return uids.map(uid => JSON.stringify({ index: LOOKUP_INDEX }) + "\n" + JSON.stringify({
    size: 2, track_total_hits: true, query: { term: { event_uid: uid } },
    _source: ["schema_version", "event_uid", "source_index", "source_document_id", "production_ready", "automated_response_allowed"],
  }) + "\n").join("");
}

function parseOne(uid: string, value: unknown): { status: LookupStatus; ref?: SourceRef } {
  if (!isObj(value) || value.error || value.timed_out !== false || !isObj(value._shards) || !isObj(value.hits)) throw new Error("Incomplete lookup");
  const s = value._shards, total = value.hits.total, hits = value.hits.hits;
  if (!Number.isSafeInteger(s.total) || (s.total as number) < 1 || s.successful !== s.total || s.failed !== 0 ||
      !isObj(total) || total.relation !== "eq" || !Number.isSafeInteger(total.value) || (total.value as number) < 0 ||
      !Array.isArray(hits) || hits.length !== Math.min(total.value as number, 2)) throw new Error("Incomplete lookup count");
  const refs: SourceRef[] = [];
  for (const hit of hits) {
    if (!isObj(hit) || hit._index !== LOOKUP_INDEX || !isObj(hit._source)) throw new Error("Invalid lookup hit");
    const d = hit._source;
    if (Object.keys(d).sort().join(",") !== "automated_response_allowed,event_uid,production_ready,schema_version,source_document_id,source_index" ||
        d.schema_version !== LOOKUP_INDEX || d.event_uid !== uid || d.production_ready !== false || d.automated_response_allowed !== false ||
        typeof d.source_index !== "string" || typeof d.source_document_id !== "string") throw new Error("Invalid lookup contract");
    const ref = { uid, index: d.source_index, id: d.source_document_id };
    validateRefs([ref]);
    const id = hash([ref.index, ref.id].map(p => `${Buffer.byteLength(p, "utf8")}:${p}`).join("|"));
    if (hit._id !== id) throw new Error("Invalid source reference hash");
    refs.push(ref);
  }
  if (total.value === 0) return { status: "not_found" };
  if (total.value !== 1) return { status: "conflict" };
  return { status: "matched", ref: refs[0] };
}

export function parseLookup(uids: string[], value: unknown) {
  if (!isObj(value) || !Array.isArray(value.responses) || value.responses.length !== uids.length) throw new Error("Invalid msearch response");
  return value.responses.map((v, i) => {
    try { return { uid: uids[i], ...parseOne(uids[i], v) }; }
    catch { return { uid: uids[i], status: "unavailable" as LookupStatus }; }
  });
}

function projectSource(raw: Obj, uid: string): Obj {
  const rule = isObj(raw.rule) ? raw.rule : {}, agent = isObj(raw.agent) ? raw.agent : {};
  const data = isObj(raw.data) ? raw.data : {}, mitre = isObj(rule.mitre) ? rule.mitre : {};
  const level = typeof rule.level === "number" && Number.isInteger(rule.level) && rule.level >= 0 && rule.level <= 15 ? rule.level : null;
  const timestamp = text(raw.timestamp);
  return { event_uid: uid, timestamp: timestamp && Number.isFinite(Date.parse(timestamp)) ? timestamp : null,
    rule_id: part(rule.id), rule_level: level, description: text(rule.description),
    agent_id: part(agent.id), agent_name: text(agent.name), agent_ip: text(agent.ip),
    src_ip: text(data.srcip), src_user: text(data.srcuser), dst_user: text(data.dstuser),
    mitre_id: list(mitre.id), mitre_tactic: list(mitre.tactic), mitre_technique: list(mitre.technique) };
}

export function parseSources(refs: SourceRef[], value: unknown, aiRows: Obj[]): LookupResult[] {
  validateRefs(refs);
  if (!isObj(value) || !Array.isArray(value.docs) || value.docs.length !== refs.length) throw new Error("Invalid source mget");
  const docs = value.docs;
  return refs.map((ref, i) => {
    const base = { event_uid: ref.uid, source: "uid_lookup" as const };
    const doc = docs[i];
    if (!isObj(doc) || doc._index !== ref.index || doc._id !== ref.id || doc.error || doc.found !== true || !isObj(doc._source)) {
      return { ...base, status: "source_unavailable" };
    }
    if (canonicalWazuhUid(doc._source) !== ref.uid) return { ...base, status: "conflict" };
    const alert = projectSource(doc._source, ref.uid);
    const ai = aiRows.find(a => a.event_uid === ref.uid);
    if (!ai || part(ai.wazuh_rule_id) !== alert.rule_id || ai.wazuh_rule_level !== alert.rule_level) {
      return { ...base, status: "conflict" };
    }
    return { ...base, status: "matched", alert };
  });
}

export async function augmentWithUidLookup(wazuh: unknown, aiPayload: unknown,
  io: { search: (body: string) => Promise<unknown>; sources: (refs: SourceRef[]) => Promise<unknown> }) {
  if (!isObj(wazuh) || !Array.isArray(wazuh.alerts) || wazuh.alerts.length > 100) throw new Error("Invalid current Wazuh window");
  const ai = validateNexusAi(aiPayload);
  const uids = [...new Set(ai.map(a => a.event_uid as string))];
  let results: LookupResult[] = [];
  if (uids.length) {
    try {
      const lookup = parseLookup(uids, await io.search(lookupQuery(uids)));
      const refs: SourceRef[] = [];
      for (const item of lookup) {
        if (ai.filter(a => a.event_uid === item.uid).length !== 1) results.push({ event_uid: item.uid, status: "conflict", source: "uid_lookup" });
        else if (item.ref) refs.push(item.ref);
        else results.push({ event_uid: item.uid, status: item.status, source: "uid_lookup" });
      }
      if (refs.length) {
        try { results.push(...parseSources(refs, await io.sources(refs), ai)); }
        catch { results.push(...refs.map(r => ({ event_uid: r.uid, status: "source_unavailable" as const, source: "uid_lookup" as const }))); }
      }
    } catch { results = uids.map(uid => ({ event_uid: uid, status: "unavailable", source: "uid_lookup" })); }
  }
  // Recent Wazuh rows retain their original source; historical rows are added only after source verification.
  const alerts = wazuh.alerts.filter(isObj).map(r => ({ ...r }));
  for (const result of results) {
    if (result.status !== "matched" || !result.alert) continue;
    const positions = alerts.flatMap((a, i) => a.event_uid === result.event_uid ? [i] : []);
    if (positions.length > 1) { result.status = "conflict"; delete result.alert; }
    else if (positions.length === 1) alerts[positions[0]] = result.alert;
    else alerts.push(result.alert);
  }
  return { wazuh: { alerts }, statuses: Object.fromEntries(results.map(r => [r.event_uid, r.status])),
    evidence: results.map(({ event_uid, status, source }) => ({ event_uid, status, source })) };
}
