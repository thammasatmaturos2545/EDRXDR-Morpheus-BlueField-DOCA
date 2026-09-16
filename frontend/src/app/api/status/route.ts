import { NextResponse } from "next/server";
import { execFile } from "child_process";
import { promisify } from "util";

export const dynamic = "force-dynamic";

const execFileAsync = promisify(execFile);

async function dockerRunning(name: string) {
  try {
    const { stdout } = await execFileAsync(
      "docker",
      [
        "inspect",
        "-f",
        "{{.State.Running}}",
        name,
      ]
    );

    return stdout.trim() === "true";
  } catch {
    return false;
  }
}

async function serviceRunning(name: string) {
  try {
    const { stdout } = await execFileAsync(
      "systemctl",
      [
        "is-active",
        name,
      ]
    );

    return stdout.trim() === "active";
  } catch {
    return false;
  }
}

async function getGPUFabric() {
  try {
    const { stdout } = await execFileAsync(
      "nvidia-smi",
      [
        "-q",
        "-i",
        "0",
      ]
    );

    const completed =
      stdout.includes("State                             : Completed");

    const success =
      stdout.includes("Status                            : Success");

    if (completed && success) {
      return "ready";
    }

    if (stdout.includes("In Progress")) {
      return "waiting";
    }

    return "unknown";

  } catch {
    return "offline";
  }
}

export async function GET() {

  const [
    bluefield,
    kafka,
    normalizer,
    opensearch,
    indexer,
    morpheus,
    gpuFabric,
  ] = await Promise.all([
    serviceRunning("edrxdr-bluefield"),
    dockerRunning("edrxdr-kafka"),
    dockerRunning("edrxdr-normalizer"),
    dockerRunning("edrxdr-opensearch"),
    dockerRunning("edrxdr-indexer"),
    dockerRunning("edrxdr-morpheus"),
    getGPUFabric(),
  ]);

  return NextResponse.json({
    bluefield,
    doca: bluefield,
    kafka,
    normalizer,
    opensearch,
    indexer,
    morpheus,
    gpuFabric,
  });
}
