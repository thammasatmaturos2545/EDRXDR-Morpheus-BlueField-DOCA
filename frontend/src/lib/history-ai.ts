import { readCompleteAi } from './copilot-ai-reader';

type Row = { event_uid?: unknown; rule_id?: unknown };
type Fields = { ai_status: 'matched' | 'not_scored' | 'conflict' | 'unavailable';
  ai_score: number | null; ai_label: string | null };
const empty = (ai_status: Fields['ai_status']): Fields => ({ ai_status, ai_score: null, ai_label: null });
const uidPattern = /^[0-9a-f]{64}$/;

export async function enrichHistoryPage<T extends Row>(rows: T[]) {
  if (!Array.isArray(rows) || rows.length > 100 || rows.some(r => !r || typeof r !== 'object' || Array.isArray(r))) {
    throw Error('Invalid history page');
  }
  const uids = [...new Set(rows.map(r => r.event_uid).filter((v): v is string => typeof v === 'string' && uidPattern.test(v)))];
  const results = new Map<string, Fields>();
  let lookupStatus: 'ok' | 'unavailable' = 'ok';
  // Bounded batches reuse complete shard/count/provenance validation. A failed
  // batch clears all results for this page, never leaves stale partial matches.
  const deadline = AbortSignal.timeout(15000);
  let position = 0;
  async function worker() {
    while (position < uids.length) {
      const batch = uids.slice(position, position += 8);
      const result = await readCompleteAi(batch, (input, init) => fetch(input, {
        ...init, signal: AbortSignal.any([deadline, ...(init?.signal ? [init.signal] : [])])
      }));
      if (result.complete !== true) throw Error('Incomplete history AI read');
      for (const uid of batch) {
        const matches = result.payload.events.filter(event => event.event_uid === uid);
        if (!matches.length) results.set(uid, empty('not_scored'));
        else if (matches.length !== 1) results.set(uid, empty('conflict'));
        else {
          const row = matches[0];
          results.set(uid, { ai_status: 'matched', ai_score: row.high_severity_score as number,
            ai_label: row.predicted_label as string });
        }
      }
    }
  }
  if (uids.length) {
    const completed = await Promise.allSettled([worker(), worker()]);
    if (completed.some(r => r.status === 'rejected')) { lookupStatus = 'unavailable'; results.clear(); }
  }
  return { ai_lookup_status: lookupStatus, events: rows.map(row => {
    const uid = row.event_uid;
    const fields = typeof uid !== 'string' || !uidPattern.test(uid) || lookupStatus === 'unavailable'
      ? empty('unavailable') : results.get(uid) ?? empty('not_scored');
    return { ...row, ...fields };
  }) };
}
