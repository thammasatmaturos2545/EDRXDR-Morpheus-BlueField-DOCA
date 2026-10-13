import { NextResponse } from "next/server";
import { RUN, parseDemo, parseWorker } from "@/lib/demo";
export const dynamic = "force-dynamic";
const headers = { "Cache-Control": "no-store" };
export async function GET(request: Request) {
  const run = new URL(request.url).searchParams.get("run") ?? "";
  if (!RUN.test(run)) return NextResponse.json({ error: "Invalid demo run" }, { status: 400, headers });
  try {
    const base = new URL(process.env.SHADOW_OPENSEARCH_URL ?? "");
    if (!["http:", "https:"].includes(base.protocol) || base.username || base.password || base.pathname !== "/" || base.search || base.hash) throw new Error("Invalid backend");
    const index = `demo-severity-${run}`;
    const options = { cache: "no-store" as const, redirect: "error" as const, signal: AbortSignal.timeout(10000) };
    const [search, worker] = await Promise.all([
      fetch(`${base.origin}/${index}/_search`, { ...options, method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ size: 20, track_total_hits: true, query: { term: { doc_type: "event" } }, sort: [{ "result.scored_at_utc": "desc" }], _source: ["doc_type", "run_id", "production_ready", "automated_response_allowed", "indexed_at_utc", "indexed_at_meaning", "result"] }) }),
      fetch(`${base.origin}/${index}/_doc/worker`, options),
    ]);
    if (!search.ok || !worker.ok) throw new Error("Unavailable");
    return NextResponse.json({ mode: "bounded_severity_demo", fetched_at: new Date().toISOString(), run, production_ready: false, automated_response_allowed: false, ...parseDemo(await search.json(), run), worker: parseWorker(await worker.json(), run) }, { headers });
  } catch {
    return NextResponse.json({ error: "Demo unavailable: backend, schema or incomplete search" }, { status: 503, headers });
  }
}
