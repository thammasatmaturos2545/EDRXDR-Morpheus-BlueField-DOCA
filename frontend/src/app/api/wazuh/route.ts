import { resolveWazuhSource } from "@/lib/wazuh-source";
import { NextResponse } from "next/server";
import { selectBalancedWazuhAlerts } from "@/lib/wazuh-sampling";
import { createHash } from "crypto";
import { execFile } from "child_process";
import { promisify } from "util";

export const dynamic = "force-dynamic";

const execFileAsync =
  promisify(execFile);

function identityPart(
  value: unknown
): string | null {
  if (
    typeof value !== "string" &&
    typeof value !== "number"
  ) {
    return null;
  }

  if (
    typeof value === "number" &&
    !Number.isFinite(value)
  ) {
    return null;
  }

  const text =
    String(value).trim();

  return text || null;
}

function wazuhEventUid(event: {
  manager?: { name?: unknown };
  agent?: { id?: unknown };
  id?: unknown;
}): string | null {
  const values = [
    identityPart(event.manager?.name),
    identityPart(event.agent?.id),
    identityPart(event.id),
  ];

  if (
    values.some(
      (value) => value === null
    )
  ) {
    return null;
  }

  const valid =
    values as string[];

  const canonical =
    "wazuh-v1|" +
    valid
      .map(
        (value) =>
          `${Buffer.byteLength(
            value,
            "utf8"
          )}:${value}`
      )
      .join("|");

  return createHash("sha256")
    .update(canonical, "utf8")
    .digest("hex");
}


export async function GET() {
  try {
    const source = await resolveWazuhSource("wazuh.manager");
    const container = source.id;

    if (!source.running || source.status !== "running") {
      return NextResponse.json(
        {
          total: null,
          alerts: [],
          error:
            "Wazuh Manager is not running",
        },
        {
          status: 503,
        }
      );
    }

    const { stdout } =
      await execFileAsync(
        "docker",
        [
          "exec",
          container,
          "tail",
          "-c",
          "4194304",
          "/var/ossec/logs/alerts/alerts.json",
        ],
        {
          maxBuffer:
            5 * 1024 * 1024,
          timeout: 10000,
        }
      );

    const lines =
      stdout
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter(Boolean);

    const alerts = [];

    for (const line of lines) {
      try {
        const event =
          JSON.parse(line);

        const rule =
          event.rule || {};

        const agent =
          event.agent || {};

        const manager =
          event.manager || {};

        const mitre =
          rule.mitre || {};

        const data =
          event.data || {};

        const eventUid =
          wazuhEventUid(event);

        alerts.push({
          id:
            event.id ||
            crypto.randomUUID(),

          event_id:
            event.id || null,

          event_uid:
            eventUid,

          timestamp:
            event.timestamp,

          rule_id:
            rule.id ||
            "unknown",

          rule_level:
            typeof rule.level === "number" && Number.isInteger(rule.level) && rule.level >= 0 && rule.level <= 15 ? rule.level : null,

          description:
            rule.description ||
            "",

          groups:
            rule.groups || [],

          firedtimes:
            typeof rule.firedtimes === "number" && Number.isFinite(rule.firedtimes) ? rule.firedtimes : null,

          agent_id:
            agent.id ||
            "unknown",

          agent_name:
            agent.name ||
            "unknown",

          agent_ip:
            agent.ip || "",

          manager_name:
            manager.name || "",

          location:
            event.location || "",

          full_log:
            event.full_log || "",

          mitre_id:
            mitre.id || [],

          mitre_tactic:
            mitre.tactic || [],

          mitre_technique:
            mitre.technique || [],

          src_user:
            data.srcuser || "",

          dst_user:
            data.dstuser || "",

          src_ip:
            data.srcip || "",

          dst_ip:
            data.dstip || "",
        });
      } catch {
        // Skip malformed line
      }
    }

    const sampledAlerts = selectBalancedWazuhAlerts(alerts);

    sampledAlerts.sort(
      (a, b) =>
        new Date(
          b.timestamp || 0
        ).getTime() -
        new Date(
          a.timestamp || 0
        ).getTime()
    );

    return NextResponse.json({
      source: { ...source, checked_at: new Date().toISOString() },
      total: sampledAlerts.length,
      alerts: sampledAlerts,
    });
  } catch (error) {
    console.error(
      "Wazuh API error:",
      error
    );

    return NextResponse.json(
      {
        total: null,
        alerts: [],
        error:
          "Wazuh source unavailable or unverified; check configured project and container identity",
      },
      {
        status: 503,
      }
    );
  }
}
