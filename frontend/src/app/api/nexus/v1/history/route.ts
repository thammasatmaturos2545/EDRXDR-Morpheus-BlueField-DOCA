import { NextResponse } from "next/server";
import { requireHistoryAuth } from "@/lib/history-auth";
import { enrichHistoryPage } from "@/lib/history-ai";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const execFileAsync = promisify(execFile);

const HISTORY_SCRIPT =
  "/home/saiuser/nexus-history-preview-20261020/query_history.py";

export async function GET(request: Request) {
  const auth = await requireHistoryAuth(request);
  if (auth) return auth;

  const url = new URL(request.url);
  const params = url.searchParams;

  const allowed = new Set(["page", "hours", "search"]);

  for (const key of params.keys()) {
    if (!allowed.has(key) || params.getAll(key).length !== 1) {
      return NextResponse.json(
        { error: "Invalid parameter" },
        { status: 400, headers: { "Cache-Control": "no-store" } }
      );
    }
  }

  const page = params.get("page") ?? "1";
  const hours = params.get("hours") ?? "all";
  const search = params.get("search") ?? "";

  if (
    !/^[1-9][0-9]{0,4}$/.test(page) ||
    Number(page) > 10000 ||
    !["all", "24", "168", "720"].includes(hours) ||
    search.length > 128
  ) {
    return NextResponse.json(
      { error: "Invalid history query" },
      { status: 400, headers: { "Cache-Control": "no-store" } }
    );
  }

  try {
    const { stdout } = await execFileAsync(
      "python3",
      [
        "-B",
        HISTORY_SCRIPT,
        "--page", page,
        "--limit", "100",
        "--hours", hours,
        "--search", search
      ],
      {
        timeout: 10000,
        maxBuffer: 1024 * 1024,
        encoding: "utf8"
      }
    );

    const data = JSON.parse(stdout);

    if (
      !data ||
      !Number.isSafeInteger(data.total) || data.total < 0 ||
      !Array.isArray(data.events) ||
      data.events.length > 100 || data.events.some((r: unknown) => !r || typeof r !== "object" || Array.isArray(r))
    ) {
      throw new Error("Invalid history response");
    }

    const ai = await enrichHistoryPage(data.events);

    return NextResponse.json(
      {
        ...data,
        source: "wazuh-history-sqlite",
        snapshot_only: true,
        events: ai.events,
        ai_lookup_status: ai.ai_lookup_status
      },
      {
        headers: {
          "Cache-Control": "no-store"
        }
      }
    );
  } catch {
    return NextResponse.json(
      { error: "History data unavailable" },
      { status: 503, headers: { "Cache-Control": "no-store" } }
    );
  }
}
