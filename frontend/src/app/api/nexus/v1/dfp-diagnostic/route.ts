import { NextResponse } from "next/server";
import { requireHistoryAuth } from "@/lib/history-auth";
import { readDfpDiagnostic } from "@/lib/dfp-diagnostic";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
let busy = false;
const headers = { "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" };
export async function GET(request: Request) {
  const denied = await requireHistoryAuth(request);
  if (denied) return denied;
  if (process.env.NEXUS_DFP_DIAGNOSTIC_ENABLED !== "1")
    return NextResponse.json({ error: "DFP diagnostic disabled" }, { status: 503, headers });
  const hash = process.env.NEXUS_DFP_DIAGNOSTIC_SHA256 || "";
  if (!/^[0-9a-f]{64}$/.test(hash))
    return NextResponse.json({ error: "DFP diagnostic unavailable" }, { status: 503, headers });
  if (new URL(request.url).search)
    return NextResponse.json({ error: "Query not supported" }, { status: 400, headers });
  if (busy) return NextResponse.json({ error: "DFP diagnostic busy" }, { status: 503, headers });
  busy = true;
  try { return NextResponse.json(await readDfpDiagnostic(hash), { headers }); }
  catch { return NextResponse.json({ error: "DFP diagnostic unavailable" }, { status: 503, headers }); }
  finally { busy = false; }
}
