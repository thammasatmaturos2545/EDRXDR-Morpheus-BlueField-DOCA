"use client";

import { useEffect, useState } from "react";

type WazuhAlert = {
  id: string;
  timestamp?: string;
  rule_id: string;
  rule_level: number;
  description: string;
  agent_id: string;
  agent_name: string;
  agent_ip: string;
  location: string;
  mitre_id: string[];
  mitre_tactic: string[];
  mitre_technique: string[];
};

type SecurityEvent = {
  id: string;
  index: string;
  timestamp?: string;
  event_type?: string;
  source_type?: string;
  sensor?: string;
  ibdev?: string;
  interface?: string;
  threat_score?: number;
  threat_class?: string;
  analysis_engine?: string;
};

type SystemStatus = {
  bluefield: boolean;
  doca: boolean;
  kafka: boolean;
  normalizer: boolean;
  opensearch: boolean;
  indexer: boolean;
  morpheus: boolean;

  gpuFabric:
    | "ready"
    | "waiting"
    | "unknown"
    | "offline";

  wazuh: boolean;
  wazuhManager: boolean;
  wazuhIndexer: boolean;
  wazuhDashboard: boolean;
  wazuhForwarder: boolean;
  wazuhAgent: boolean;
};

const emptyStatus: SystemStatus = {
  bluefield: false,
  doca: false,
  kafka: false,
  normalizer: false,
  opensearch: false,
  indexer: false,
  morpheus: false,
  gpuFabric: "unknown",

  wazuh: false,
  wazuhManager: false,
  wazuhIndexer: false,
  wazuhDashboard: false,
  wazuhForwarder: false,
  wazuhAgent: false,
};

export default function Home() {
  const [status, setStatus] =
    useState<SystemStatus>(emptyStatus);

  const [wazuhAlerts, setWazuhAlerts] =
    useState<WazuhAlert[]>([]);

  const [events, setEvents] =
    useState<SecurityEvent[]>([]);

  const [updated, setUpdated] =
    useState("-");

  async function loadStatus() {
    try {
      const response = await fetch(
        "/api/status",
        { cache: "no-store" }
      );

      if (!response.ok) {
        return;
      }

      const data =
        await response.json();

      setStatus(data);
    } catch (error) {
      console.error(
        "Status API error:",
        error
      );
    }
  }

  async function loadWazuh() {
    try {
      const response = await fetch(
        "/api/wazuh",
        { cache: "no-store" }
      );

      if (!response.ok) {
        return;
      }

      const data =
        await response.json();

      setWazuhAlerts(
        data.alerts || []
      );
    } catch (error) {
      console.error(
        "Wazuh API error:",
        error
      );
    }
  }

  async function loadEvents() {
    try {
      const response = await fetch(
        "/api/events",
        { cache: "no-store" }
      );

      if (!response.ok) {
        return;
      }

      const data =
        await response.json();

      setEvents(
        data.events || []
      );
    } catch (error) {
      console.error(
        "Events API error:",
        error
      );
    }
  }

  async function refresh() {
    await Promise.all([
      loadStatus(),
      loadWazuh(),
      loadEvents(),
    ]);

    setUpdated(
      new Date().toLocaleTimeString()
    );
  }

  useEffect(() => {
    refresh();

    const timer =
      setInterval(
        refresh,
        5000
      );

    return () =>
      clearInterval(timer);
  }, []);

  /*
   * Do not display simulated Morpheus output.
   * Only real Morpheus results are accepted here.
   */
  const morpheusEvents =
    events.filter(
      (event) =>
        event.analysis_engine !==
          "morpheus-simulator" &&
        event.analysis_engine
    );

  const latestWazuh =
    wazuhAlerts[0];

  const highAlerts =
    wazuhAlerts.filter(
      (alert) =>
        alert.rule_level >= 7
    );

  const criticalAlerts =
    wazuhAlerts.filter(
      (alert) =>
        alert.rule_level >= 12
    );

  const maxThreatScore =
    morpheusEvents.length > 0
      ? Math.max(
          ...morpheusEvents.map(
            (event) =>
              event.threat_score ?? 0
          )
        )
      : null;

  const coreOnline =
    status.bluefield &&
    status.doca &&
    status.wazuhManager &&
    status.wazuhForwarder &&
    status.kafka &&
    status.normalizer &&
    status.opensearch &&
    status.indexer;

  return (
    <main className="min-h-screen bg-[#05070a] text-white">

      {/* HEADER */}
      <header className="border-b border-white/10 bg-[#080b10]">
        <div className="mx-auto flex max-w-[1500px] items-center justify-between px-6 py-5">

          <div className="flex items-center gap-4">
            <div className="flex h-11 w-11 items-center justify-center rounded-lg border border-green-500/30 bg-green-500/10 font-bold text-green-400">
              X
            </div>

            <div>
              <h1 className="text-2xl font-bold tracking-wide">
                EDRXDR
              </h1>

              <p className="text-sm text-gray-400">
                Wazuh + NVIDIA BlueField-3 + DOCA + Morpheus
              </p>
            </div>
          </div>

          <div className="text-right">
            <div
              className={
                coreOnline
                  ? "text-sm text-green-400"
                  : "text-sm text-red-400"
              }
            >
              {coreOnline
                ? "● Core System Online"
                : "● System Degraded"}
            </div>

            <div className="mt-1 text-xs text-gray-500">
              Updated: {updated}
            </div>
          </div>

        </div>
      </header>

      <div className="mx-auto max-w-[1500px] px-6 py-8">

        {/* PIPELINE STATUS */}
        <section className="mb-8">
          <h2 className="text-xl font-semibold">
            Pipeline Status
          </h2>

          <p className="mb-4 mt-1 text-sm text-gray-500">
            Real-time infrastructure health
          </p>

          <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-4 xl:grid-cols-6">

            <StatusCard
              name="Wazuh Agent"
              state={
                status.wazuhAgent
                  ? "online"
                  : "offline"
              }
            />

            <StatusCard
              name="Wazuh Manager"
              state={
                status.wazuhManager
                  ? "online"
                  : "offline"
              }
            />

            <StatusCard
              name="Wazuh Forwarder"
              state={
                status.wazuhForwarder
                  ? "online"
                  : "offline"
              }
            />

            <StatusCard
              name="BlueField-3"
              state={
                status.bluefield
                  ? "online"
                  : "offline"
              }
            />

            <StatusCard
              name="DOCA"
              state={
                status.doca
                  ? "online"
                  : "offline"
              }
            />

            <StatusCard
              name="Kafka"
              state={
                status.kafka
                  ? "online"
                  : "offline"
              }
            />

            <StatusCard
              name="Normalizer"
              state={
                status.normalizer
                  ? "online"
                  : "offline"
              }
            />

            <StatusCard
              name="Morpheus"
              state={
                status.morpheus
                  ? "online"
                  : status.gpuFabric ===
                      "waiting"
                    ? "waiting"
                    : "offline"
              }
            />

            <StatusCard
              name="H100 Fabric"
              state={
                status.gpuFabric ===
                "ready"
                  ? "online"
                  : status.gpuFabric ===
                      "waiting"
                    ? "waiting"
                    : "offline"
              }
            />

            <StatusCard
              name="Indexer"
              state={
                status.indexer
                  ? "online"
                  : "offline"
              }
            />

            <StatusCard
              name="OpenSearch"
              state={
                status.opensearch
                  ? "online"
                  : "offline"
              }
            />

            <StatusCard
              name="Wazuh Dashboard"
              state={
                status.wazuhDashboard
                  ? "online"
                  : "offline"
              }
            />

          </div>

          {!status.morpheus && (
            <div className="mt-4 rounded-lg border border-yellow-500/20 bg-yellow-500/5 px-4 py-3 text-sm text-yellow-300">
              NVIDIA Morpheus is waiting for H100 GPU Fabric.
              Wazuh and BlueField events are already streaming
              through Kafka → Normalizer → morpheus-input.
              No simulated Morpheus result is displayed.
            </div>
          )}
        </section>

        {/* METRICS */}
        <section className="mb-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">

          <MetricCard
            title="Wazuh Alerts"
            value={wazuhAlerts.length}
            subtitle="Recent endpoint alerts"
          />

          <MetricCard
            title="High-Level Alerts"
            value={highAlerts.length}
            subtitle="Wazuh rule level ≥ 7"
          />

          <MetricCard
            title="Critical Alerts"
            value={criticalAlerts.length}
            subtitle="Wazuh rule level ≥ 12"
          />

          <MetricCard
            title="Morpheus Threat Score"
            value={
              maxThreatScore === null
                ? "Waiting"
                : maxThreatScore.toFixed(2)
            }
            subtitle={
              status.morpheus
                ? "Real GPU analysis"
                : "No fallback / simulator"
            }
          />

        </section>

        {/* WAZUH + BLUEFIELD */}
        <section className="mb-8 grid gap-6 lg:grid-cols-2">

          {/* WAZUH */}
          <div className="rounded-xl border border-white/10 bg-[#0c1016] p-6">

            <div className="mb-6">
              <h2 className="text-xl font-semibold">
                Wazuh Endpoint Security
              </h2>

              <p className="mt-1 text-sm text-gray-500">
                Endpoint / Host detection
              </p>
            </div>

            {latestWazuh ? (
              <div className="space-y-5">

                <div className="flex items-start justify-between gap-4">

                  <div>
                    <div className="text-xs text-gray-500">
                      Latest Alert
                    </div>

                    <div className="mt-1 font-medium">
                      {latestWazuh.description}
                    </div>
                  </div>

                  <LevelBadge
                    level={
                      latestWazuh.rule_level
                    }
                  />

                </div>

                <div className="grid grid-cols-2 gap-4">

                  <InfoCard
                    label="Agent"
                    value={
                      latestWazuh.agent_name
                    }
                  />

                  <InfoCard
                    label="Rule ID"
                    value={
                      latestWazuh.rule_id
                    }
                  />

                  <InfoCard
                    label="Rule Level"
                    value={
                      latestWazuh.rule_level
                    }
                  />

                  <InfoCard
                    label="Location"
                    value={
                      latestWazuh.location ||
                      "-"
                    }
                  />

                </div>

                <div>
                  <div className="mb-2 text-xs text-gray-500">
                    MITRE ATT&CK
                  </div>

                  <div className="flex flex-wrap gap-2">

                    {latestWazuh.mitre_id.length > 0
                      ? latestWazuh.mitre_id.map(
                          (id) => (
                            <span
                              key={id}
                              className="rounded-md bg-purple-500/10 px-2 py-1 text-xs text-purple-300"
                            >
                              {id}
                            </span>
                          )
                        )
                      : (
                        <span className="text-sm text-gray-500">
                          No MITRE mapping
                        </span>
                      )}

                  </div>
                </div>

                <div>
                  <div className="mb-1 text-xs text-gray-500">
                    MITRE Tactics
                  </div>

                  <div className="text-sm text-gray-300">
                    {latestWazuh.mitre_tactic.join(", ") || "-"}
                  </div>
                </div>

              </div>
            ) : (
              <div className="text-gray-500">
                Waiting for Wazuh alerts...
              </div>
            )}

          </div>

          {/* BLUEFIELD */}
          <div className="rounded-xl border border-white/10 bg-[#0c1016] p-6">

            <div className="mb-6">
              <h2 className="text-xl font-semibold">
                BlueField Network Security
              </h2>

              <p className="mt-1 text-sm text-gray-500">
                NVIDIA BlueField-3 + DOCA telemetry
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">

              <InfoCard
                label="BlueField"
                value={
                  status.bluefield
                    ? "Online"
                    : "Offline"
                }
              />

              <InfoCard
                label="DOCA"
                value={
                  status.doca
                    ? "Online"
                    : "Offline"
                }
              />

              <InfoCard
                label="Kafka Topic"
                value="bluefield-events"
              />

              <InfoCard
                label="Destination"
                value="morpheus-input"
              />

            </div>

            <div className="mt-6 rounded-lg border border-blue-500/20 bg-blue-500/5 p-4">

              <div className="text-sm font-medium text-blue-300">
                Network Telemetry Pipeline
              </div>

              <div className="mt-2 text-sm leading-7 text-gray-400">
                BlueField-3 → DOCA → bluefield_monitor
                → Kafka bluefield-events → Normalizer
                → morpheus-input
              </div>

            </div>

          </div>

        </section>

        {/* RECENT WAZUH */}
        <section className="mb-8 overflow-hidden rounded-xl border border-white/10 bg-[#0c1016]">

          <div className="border-b border-white/10 px-6 py-5">
            <h2 className="text-xl font-semibold">
              Recent Wazuh Alerts
            </h2>

            <p className="mt-1 text-sm text-gray-500">
              Real endpoint alerts from Wazuh Manager
            </p>
          </div>

          <div className="overflow-x-auto">

            <table className="w-full text-left text-sm">

              <thead className="bg-black/30 text-xs uppercase text-gray-500">
                <tr>
                  <th className="px-5 py-3">
                    Time
                  </th>

                  <th className="px-5 py-3">
                    Agent
                  </th>

                  <th className="px-5 py-3">
                    Rule
                  </th>

                  <th className="px-5 py-3">
                    Level
                  </th>

                  <th className="px-5 py-3">
                    Description
                  </th>

                  <th className="px-5 py-3">
                    MITRE
                  </th>
                </tr>
              </thead>

              <tbody>

                {wazuhAlerts
                  .slice(0, 20)
                  .map(
                    (alert) => (
                      <tr
                        key={alert.id}
                        className="border-t border-white/5 hover:bg-white/5"
                      >

                        <td className="whitespace-nowrap px-5 py-4 text-xs text-gray-400">
                          {alert.timestamp
                            ? new Date(
                                alert.timestamp
                              ).toLocaleString()
                            : "-"}
                        </td>

                        <td className="px-5 py-4">
                          {alert.agent_name}
                        </td>

                        <td className="px-5 py-4 font-mono">
                          {alert.rule_id}
                        </td>

                        <td className="px-5 py-4">
                          <LevelBadge
                            level={
                              alert.rule_level
                            }
                          />
                        </td>

                        <td className="max-w-md px-5 py-4">
                          {alert.description}
                        </td>

                        <td className="px-5 py-4 text-xs text-purple-300">
                          {alert.mitre_id.join(", ") || "-"}
                        </td>

                      </tr>
                    )
                  )}

              </tbody>

            </table>

          </div>

        </section>

        {/* UNIFIED PIPELINE */}
        <section className="rounded-xl border border-white/10 bg-[#0c1016] p-6">

          <h2 className="text-xl font-semibold">
            EDRXDR Unified Pipeline
          </h2>

          <p className="mb-6 mt-1 text-sm text-gray-500">
            Wazuh Endpoint Security + NVIDIA BlueField Network Security
          </p>

          <div className="grid gap-6 lg:grid-cols-2">

            <div className="space-y-3">
              <div className="text-sm font-medium text-gray-400">
                Endpoint / EDR
              </div>

              <PipelineBox
                text="Wazuh Agent"
                online={status.wazuhAgent}
              />

              <div className="text-center text-gray-600">
                ↓
              </div>

              <PipelineBox
                text="Wazuh Manager"
                online={status.wazuhManager}
              />

              <div className="text-center text-gray-600">
                ↓
              </div>

              <PipelineBox
                text="Kafka: wazuh-alerts"
                online={status.wazuhForwarder}
              />
            </div>

            <div className="space-y-3">
              <div className="text-sm font-medium text-gray-400">
                Network / DPU
              </div>

              <PipelineBox
                text="NVIDIA BlueField-3"
                online={status.bluefield}
              />

              <div className="text-center text-gray-600">
                ↓
              </div>

              <PipelineBox
                text="NVIDIA DOCA"
                online={status.doca}
              />

              <div className="text-center text-gray-600">
                ↓
              </div>

              <PipelineBox
                text="Kafka: bluefield-events"
                online={status.kafka}
              />
            </div>

          </div>

          <div className="my-6 text-center text-2xl text-gray-600">
            ↓
          </div>

          <div className="flex flex-wrap items-center justify-center gap-3">

            <PipelineBox
              text="Normalizer"
              online={status.normalizer}
            />

            <Arrow />

            <PipelineBox
              text="morpheus-input"
              online={status.kafka}
            />

            <Arrow />

            <StateBox
              text="NVIDIA Morpheus"
              state={
                status.morpheus
                  ? "online"
                  : "waiting"
              }
            />

            <Arrow />

            <StateBox
              text="morpheus-output"
              state={
                status.morpheus
                  ? "online"
                  : "waiting"
              }
            />

            <Arrow />

            <PipelineBox
              text="Indexer"
              online={status.indexer}
            />

            <Arrow />

            <PipelineBox
              text="OpenSearch"
              online={status.opensearch}
            />

            <Arrow />

            <StateBox
              text="EDRXDR Dashboard"
              state="online"
            />

          </div>

        </section>

      </div>

    </main>
  );
}

function StatusCard({
  name,
  state,
}: {
  name: string;
  state:
    | "online"
    | "waiting"
    | "offline";
}) {
  const config = {
    online: {
      text: "● Online",
      style:
        "border-green-500/25 text-green-400",
    },

    waiting: {
      text: "● Waiting",
      style:
        "border-yellow-500/25 text-yellow-400",
    },

    offline: {
      text: "● Offline",
      style:
        "border-red-500/25 text-red-400",
    },
  };

  return (
    <div
      className={`rounded-lg border bg-[#0c1016] p-4 ${config[state].style}`}
    >
      <div className="font-medium text-white">
        {name}
      </div>

      <div className="mt-2 text-xs">
        {config[state].text}
      </div>
    </div>
  );
}

function MetricCard({
  title,
  value,
  subtitle,
}: {
  title: string;
  value: string | number;
  subtitle: string;
}) {
  return (
    <div className="rounded-xl border border-white/10 bg-[#0c1016] p-5">

      <div className="text-sm text-gray-400">
        {title}
      </div>

      <div className="mt-2 text-3xl font-bold">
        {value}
      </div>

      <div className="mt-1 text-xs text-gray-500">
        {subtitle}
      </div>

    </div>
  );
}

function InfoCard({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="rounded-lg bg-black/30 p-4">

      <div className="text-xs text-gray-500">
        {label}
      </div>

      <div className="mt-1 break-all text-sm font-medium">
        {value}
      </div>

    </div>
  );
}

function LevelBadge({
  level,
}: {
  level: number;
}) {
  let style =
    "bg-green-500/10 text-green-400";

  if (level >= 12) {
    style =
      "bg-red-500/20 text-red-300";
  } else if (level >= 7) {
    style =
      "bg-orange-500/10 text-orange-300";
  } else if (level >= 4) {
    style =
      "bg-yellow-500/10 text-yellow-300";
  }

  return (
    <span
      className={`whitespace-nowrap rounded-full px-3 py-1 text-xs font-medium ${style}`}
    >
      Level {level}
    </span>
  );
}

function PipelineBox({
  text,
  online,
}: {
  text: string;
  online: boolean;
}) {
  return (
    <div
      className={
        online
          ? "rounded-lg border border-green-500/30 bg-green-500/5 px-4 py-2 text-center text-sm text-green-300"
          : "rounded-lg border border-red-500/30 bg-red-500/5 px-4 py-2 text-center text-sm text-red-300"
      }
    >
      {text}
    </div>
  );
}

function StateBox({
  text,
  state,
}: {
  text: string;
  state:
    | "online"
    | "waiting";
}) {
  return (
    <div
      className={
        state === "online"
          ? "rounded-lg border border-green-500/30 bg-green-500/5 px-4 py-2 text-center text-sm text-green-300"
          : "rounded-lg border border-yellow-500/30 bg-yellow-500/5 px-4 py-2 text-center text-sm text-yellow-300"
      }
    >
      {text}
    </div>
  );
}

function Arrow() {
  return (
    <span className="text-gray-600">
      →
    </span>
  );
}
