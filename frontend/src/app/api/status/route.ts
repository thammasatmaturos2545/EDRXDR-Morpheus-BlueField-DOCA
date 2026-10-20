import { resolveWazuhSource } from "@/lib/wazuh-source";
import { NextResponse } from "next/server";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
export const dynamic = "force-dynamic";
export const runtime = "nodejs";
const run = promisify(execFile);
type State = "online" | "offline" | "unknown" | "waiting";
const options = { timeout: 5000, maxBuffer: 1024 * 1024 };
async function docker(name: string): Promise<State> {
 try { const { stdout } = await run("docker", ["inspect", "-f", "{{.State.Running}}", name], options); return stdout.trim() === "true" ? "online" : stdout.trim() === "false" ? "offline" : "unknown"; }
 catch { return "unknown"; }
}
async function compose(service: string): Promise<State> {
 try {
  const source = await resolveWazuhSource(service);
  if (source.running && source.status === "running") return "online";
  if (!source.running && ["exited", "dead", "created", "paused"].includes(source.status)) return "offline";
  return "unknown";
 } catch { return "unknown"; }
}
async function systemd(name: string): Promise<State> {
 // Show permits distinguishing a missing unit from an explicitly stopped unit.
 try {
  const { stdout } = await run("systemctl", ["show", name, "--property=LoadState", "--property=ActiveState"], options);
  if (!/^LoadState=loaded$/m.test(stdout)) return "unknown";
  if (/^ActiveState=active$/m.test(stdout)) return "online";
  if (/^ActiveState=(inactive|failed)$/m.test(stdout)) return "offline";
  if (/^ActiveState=(activating|deactivating)$/m.test(stdout)) return "waiting";
  return "unknown";
 } catch { return "unknown"; }
}
async function fabric(): Promise<State> {
 try {
  const { stdout } = await run("nvidia-smi", ["-q", "-i", "0"], options);
  const section = stdout.match(/\bFabric\s*\r?\n([\s\S]*?)(?=\r?\n\s{4}\S|$)/)?.[1];
  if (!section) return "unknown";
  if (/State\s*:\s*Completed/.test(section) && /Status\s*:\s*Success/.test(section)) return "online";
  if (/State\s*:\s*In Progress/.test(section)) return "waiting";
  if (/Status\s*:\s*(Failed|Failure)/.test(section)) return "offline";
  return "unknown";
 } catch { return "unknown"; }
}
export async function GET() {
 const checks: Record<string, Promise<State>> = {
  bluefield: systemd("edrxdr-bluefield"),
  // Only probe a separately configured DOCA service; BlueField is not a DOCA health check.
  doca: process.env.DOCA_SYSTEMD_SERVICE ? systemd(process.env.DOCA_SYSTEMD_SERVICE) : Promise.resolve("unknown"),
  kafka: docker("edrxdr-kafka"), normalizer: docker("edrxdr-normalizer"),
  opensearch: docker("edrxdr-opensearch"), indexer: docker("edrxdr-indexer"), morpheus: docker("edrxdr-morpheus"),
  wazuhManager: compose("wazuh.manager"), wazuhIndexer: compose("wazuh.indexer"),
  wazuhDashboard: compose("wazuh.dashboard"), wazuhForwarder: compose("wazuh.forwarder"),
  wazuhAgent: systemd("wazuh-agent"), gpuFabric: fabric(),
 };
 const entries = await Promise.all(Object.entries(checks).map(async ([key, check]) => [key, await check]));
 return NextResponse.json({ ...Object.fromEntries(entries), checked_at: new Date().toISOString(), evidence: "Local process/container state only; does not establish event flow" }, { headers: { "Cache-Control": "no-store" } });
}
