import { NextResponse } from "next/server";
export const dynamic = "force-dynamic";
export async function GET(){
  return NextResponse.json({ok:true,mode:"edrxdr-nexus-adapter",production_ready:false,automated_response_allowed:false,write_enabled:false},{headers:{"Cache-Control":"no-store"}});
}
