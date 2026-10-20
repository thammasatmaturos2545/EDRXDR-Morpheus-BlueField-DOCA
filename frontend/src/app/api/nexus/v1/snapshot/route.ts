import { NextResponse } from "next/server";
import { buildNexusSnapshot } from "@/lib/nexus-soc";
import { augmentWithUidLookup } from "@/lib/uid-lookup";
import { searchUidLookup, readUidSources } from "@/lib/uid-lookup-server";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

async function readJson(url:string){
  const r=await fetch(url,{cache:"no-store",headers:{Accept:"application/json"},redirect:"error",signal:AbortSignal.timeout(15000)});
  if(!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export async function GET(request:Request){
  const url=new URL(request.url);
  const requested=Number(url.searchParams.get("hours") ?? "24");
  const hours=[1,24,168].includes(requested)?requested:24;
  let wazuh:unknown;
  try { wazuh=await readJson(`${url.origin}/api/wazuh`); }
  catch { return NextResponse.json({error:"Cannot read Wazuh alerts for NEXUS dashboard"},{status:503,headers:{"Cache-Control":"no-store"}}); }

  let ai:unknown={events:[]}; let aiAvailable=true;
  try { ai=await readJson(`${url.origin}/api/events`); } catch { aiAvailable=false; }

  try {
    const lookup = aiAvailable ? await augmentWithUidLookup(wazuh, ai, {search: searchUidLookup, sources: readUidSources}) : null;
    const snapshot = buildNexusSnapshot(lookup?.wazuh ?? wazuh, ai, {hours, aiAvailable, lookupStatuses: lookup?.statuses, generatedAt:new Date().toISOString()});
    return NextResponse.json({...snapshot, meta: {...snapshot.meta, uid_lookup: {
      scope: "latest AI window; captured lookup coverage only",
      results: lookup?.evidence ?? [], requested: lookup?.evidence.length ?? 0,
      matched: lookup?.evidence.filter(r => r.status === "matched").length ?? 0,
      ai_available: aiAvailable, production_ready: false, automated_response_allowed: false
    }}}, {headers:{"Cache-Control":"no-store"}});
  } catch {
    return NextResponse.json({error:"Invalid EDR/XDR payload for NEXUS dashboard"},{status:502,headers:{"Cache-Control":"no-store"}});
  }
}
