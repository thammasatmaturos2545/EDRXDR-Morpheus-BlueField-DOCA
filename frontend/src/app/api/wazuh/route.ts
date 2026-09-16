import { NextResponse } from "next/server";
import { execFile } from "child_process";
import { promisify } from "util";

export const dynamic = "force-dynamic";

const execFileAsync =
  promisify(execFile);

async function getManagerContainer() {
  const { stdout } =
    await execFileAsync(
      "docker",
      [
        "ps",
        "--filter",
        "label=com.docker.compose.service=wazuh.manager",
        "--filter",
        "status=running",
        "--format",
        "{{.Names}}",
      ]
    );

  return (
    stdout
      .trim()
      .split("\n")
      .filter(Boolean)[0] || ""
  );
}

export async function GET() {
  try {
    const container =
      await getManagerContainer();

    if (!container) {
      return NextResponse.json(
        {
          total: 0,
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
          "-n",
          "100",
          "/var/ossec/logs/alerts/alerts.json",
        ],
        {
          maxBuffer:
            5 * 1024 * 1024,
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

        alerts.push({
          id:
            event.id ||
            crypto.randomUUID(),

          timestamp:
            event.timestamp,

          rule_id:
            rule.id ||
            "unknown",

          rule_level:
            Number(
              rule.level || 0
            ),

          description:
            rule.description ||
            "",

          groups:
            rule.groups || [],

          firedtimes:
            Number(
              rule.firedtimes || 0
            ),

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

    alerts.sort(
      (a, b) =>
        new Date(
          b.timestamp || 0
        ).getTime() -
        new Date(
          a.timestamp || 0
        ).getTime()
    );

    return NextResponse.json({
      total: alerts.length,
      alerts,
    });
  } catch (error) {
    console.error(
      "Wazuh API error:",
      error
    );

    return NextResponse.json(
      {
        total: 0,
        alerts: [],
        error:
          "Cannot read Wazuh alerts",
      },
      {
        status: 500,
      }
    );
  }
}
