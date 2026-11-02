import { NextResponse } from "next/server";
import { requireHistoryAuth } from "@/lib/history-auth";
import { parseLabQuery, readModelLab } from "@/lib/model-lab";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
let busy = false;
const headers = { "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" };
export async function GET(request: Request) {
  const auth = await requireHistoryAuth(request);
  if (auth) return auth;
  if (process.env.NEXUS_MODEL_LAB_ENABLED !== "1")
    return NextResponse.json({ error: "Model Lab disabled" }, { status: 503, headers });
  let query;
  try { query = parseLabQuery(request.url); }
  catch { return NextResponse.json({ error: "Invalid Lab query" }, { status: 400, headers }); }
  if (busy) return NextResponse.json({ error: "Model Lab busy" }, { status: 503, headers });
  busy = true;
  try { return NextResponse.json(await readModelLab(query), { headers }); }
  catch { return NextResponse.json({ error: "Model Lab unavailable" }, { status: 503, headers }); }
  finally { busy = false; }
}
