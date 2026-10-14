import { NextResponse } from "next/server";
import { buildNexusSnapshot } from "@/lib/nexus-soc";
export const dynamic = "force-dynamic";

async function readJson(url:string){
  const r=await fetch(url,{cache:"no-store",headers:{Accept:"application/json"}});
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
    return NextResponse.json(buildNexusSnapshot(wazuh,ai,{hours,aiAvailable,generatedAt:new Date().toISOString()}),{headers:{"Cache-Control":"no-store"}});
  } catch {
    return NextResponse.json({error:"Invalid EDR/XDR payload for NEXUS dashboard"},{status:502,headers:{"Cache-Control":"no-store"}});
  }
}
