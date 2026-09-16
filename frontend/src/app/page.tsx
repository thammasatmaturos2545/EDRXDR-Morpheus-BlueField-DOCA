"use client";

import { useEffect, useState } from "react";

/* =========================================================
   TYPES
========================================================= */

type SecurityEvent = {
  id: string;
  index: string;

  timestamp?: string;

  event_type?: string;
  source_type?: string;

  sensor?: string;

  ibdev?: string;
  interface?: string;

  rx_packets?: number;
  tx_packets?: number;

  rx_bytes?: number;
  tx_bytes?: number;

  delta_rx_packets?: number;
  delta_tx_packets?: number;

  delta_rx_bytes?: number;
  delta_tx_bytes?: number;

  rx_errors?: number;
  tx_errors?: number;

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
};

/* =========================================================
   MAIN PAGE
========================================================= */

export default function Home() {
  const [events, setEvents] = useState<SecurityEvent[]>([]);

  const [status, setStatus] = useState<SystemStatus>({
    bluefield: false,
    doca: false,

    kafka: false,
    normalizer: false,

    opensearch: false,
    indexer: false,

    morpheus: false,

    gpuFabric: "unknown",
  });

  const [loading, setLoading] = useState(true);

  const [lastUpdated, setLastUpdated] =
    useState<string>("");

  /* =======================================================
     LOAD EVENTS
  ======================================================= */

  async function loadEvents() {
    try {
      const response = await fetch("/api/events", {
        cache: "no-store",
      });

      if (!response.ok) {
        throw new Error(
          `Events API returned ${response.status}`
        );
      }

      const data = await response.json();

      setEvents(data.events || []);

      setLastUpdated(
        new Date().toLocaleTimeString()
      );
    } catch (error) {
      console.error(
        "Failed to load security events:",
        error
      );
    } finally {
      setLoading(false);
    }
  }

  /* =======================================================
     LOAD PIPELINE STATUS
  ======================================================= */

  async function loadStatus() {
    try {
      const response = await fetch("/api/status", {
        cache: "no-store",
      });

      if (!response.ok) {
        throw new Error(
          `Status API returned ${response.status}`
        );
      }

      const data = await response.json();

      setStatus(data);
    } catch (error) {
      console.error(
        "Failed to load system status:",
        error
      );
    }
  }

  /* =======================================================
     AUTO REFRESH
  ======================================================= */

  useEffect(() => {
    loadEvents();
    loadStatus();

    const timer = setInterval(() => {
      loadEvents();
      loadStatus();
    }, 5000);

    return () => clearInterval(timer);
  }, []);

  /* =======================================================
     METRICS
  ======================================================= */

  const suspiciousEvents = events.filter(
    (event) =>
      event.threat_class === "suspicious" ||
      event.threat_class === "malicious" ||
      (event.threat_score ?? 0) >= 0.7
  );

  const maxThreatScore =
    events.length > 0
      ? Math.max(
          ...events.map(
            (event) => event.threat_score ?? 0
          )
        )
      : 0;

  const totalRxPackets = events.reduce(
    (total, event) =>
      total + (event.rx_packets ?? 0),
    0
  );

  const totalTxPackets = events.reduce(
    (total, event) =>
      total + (event.tx_packets ?? 0),
    0
  );

  const totalRxBytes = events.reduce(
    (total, event) =>
      total + (event.rx_bytes ?? 0),
    0
  );

  const totalTxBytes = events.reduce(
    (total, event) =>
      total + (event.tx_bytes ?? 0),
    0
  );

  const latestEvent = events[0];

  const coreSystemOnline =
    status.bluefield &&
    status.doca &&
    status.kafka &&
    status.normalizer &&
    status.opensearch &&
    status.indexer;

  /* =======================================================
     UI
  ======================================================= */

  return (
    <main className="min-h-screen bg-[#05070a] text-white">
      {/* HEADER */}

      <header className="border-b border-white/10 bg-[#090c11]">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
          <div>
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-green-500/30 bg-green-500/10 font-bold text-green-400">
                X
              </div>

              <div>
                <h1 className="text-2xl font-bold tracking-wide">
                  EDRXDR
                </h1>

                <p className="text-sm text-gray-400">
                  Intelligent Threat Detection Pipeline
                </p>
              </div>
            </div>
          </div>

          <div className="text-right">
            <div
              className={`text-sm ${
                coreSystemOnline
                  ? "text-green-400"
                  : "text-red-400"
              }`}
            >
              {coreSystemOnline
                ? "● Core System Online"
                : "● System Degraded"}
            </div>

            <div className="mt-1 text-xs text-gray-500">
              Updated: {lastUpdated || "-"}
            </div>
          </div>
        </div>
      </header>

      {/* CONTENT */}

      <div className="mx-auto max-w-7xl px-6 py-8">
        {/* =================================================
            PIPELINE STATUS
        ================================================= */}

        <section className="mb-8">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">
                Pipeline Status
              </h2>

              <p className="mt-1 text-xs text-gray-500">
                Real-time infrastructure health
              </p>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-4 xl:grid-cols-8">
            <StatusCard
              name="BlueField-3"
              status={
                status.bluefield
                  ? "online"
                  : "offline"
              }
            />

            <StatusCard
              name="DOCA"
              status={
                status.doca
                  ? "online"
                  : "offline"
              }
            />

            <StatusCard
              name="Kafka"
              status={
                status.kafka
                  ? "online"
                  : "offline"
              }
            />

            <StatusCard
              name="Normalizer"
              status={
                status.normalizer
                  ? "online"
                  : "offline"
              }
            />

            <StatusCard
              name="Morpheus"
              status={
                status.morpheus
                  ? "online"
                  : status.gpuFabric === "waiting"
                    ? "waiting"
                    : "offline"
              }
            />

            <StatusCard
              name="OpenSearch"
              status={
                status.opensearch
                  ? "online"
                  : "offline"
              }
            />

            <StatusCard
              name="Indexer"
              status={
                status.indexer
                  ? "online"
                  : "offline"
              }
            />

            <StatusCard
              name="H100 Fabric"
              status={
                status.gpuFabric === "ready"
                  ? "online"
                  : status.gpuFabric === "waiting"
                    ? "waiting"
                    : "offline"
              }
            />
          </div>

          {/* GPU STATUS MESSAGE */}

          {status.gpuFabric === "waiting" && (
            <div className="mt-3 rounded-lg border border-yellow-500/20 bg-yellow-500/5 px-4 py-3 text-sm text-yellow-300">
              NVIDIA Morpheus is waiting for H100 GPU
              Fabric initialization. Current threat
              results are using simulated Morpheus
              output.
            </div>
          )}

          {status.gpuFabric === "ready" &&
            status.morpheus && (
              <div className="mt-3 rounded-lg border border-green-500/20 bg-green-500/5 px-4 py-3 text-sm text-green-300">
                NVIDIA H100 Fabric is ready and
                Morpheus is online.
              </div>
            )}
        </section>

        {/* =================================================
            METRICS
        ================================================= */}

        <section className="mb-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            title="Security Events"
            value={events.length}
            subtitle="Indexed events"
          />

          <MetricCard
            title="Suspicious"
            value={suspiciousEvents.length}
            subtitle="Threat detections"
          />

          <MetricCard
            title="Highest Threat Score"
            value={maxThreatScore.toFixed(2)}
            subtitle="Threat probability 0.00 - 1.00"
          />

          <MetricCard
            title="BlueField Packets"
            value={totalRxPackets + totalTxPackets}
            subtitle={`RX ${totalRxPackets} / TX ${totalTxPackets}`}
          />
        </section>

        {/* =================================================
            THREAT + NETWORK
        ================================================= */}

        <section className="mb-8 grid gap-6 lg:grid-cols-2">
          {/* Threat */}

          <div className="rounded-xl border border-white/10 bg-[#0c1016] p-6">
            <div className="mb-6 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold">
                  Threat Analysis
                </h2>

                <p className="mt-1 text-xs text-gray-500">
                  Morpheus threat classification
                </p>
              </div>

              <ThreatBadge
                value={
                  latestEvent?.threat_class ||
                  "unknown"
                }
              />
            </div>

            <div className="flex flex-col items-center gap-8 sm:flex-row">
              <ThreatScore score={maxThreatScore} />

              <div className="w-full space-y-4 text-sm">
                <InfoRow
                  label="Detection"
                  value={
                    suspiciousEvents.length > 0
                      ? "Suspicious Activity"
                      : "Normal Activity"
                  }
                />

                <InfoRow
                  label="Analysis Engine"
                  value={
                    latestEvent?.analysis_engine ||
                    (status.morpheus
                      ? "NVIDIA Morpheus"
                      : "Waiting for Morpheus")
                  }
                />

                <InfoRow
                  label="Sensor"
                  value={
                    latestEvent?.sensor ||
                    "NVIDIA BlueField-3"
                  }
                />

                <InfoRow
                  label="Event Type"
                  value={
                    latestEvent?.event_type ||
                    "network_telemetry"
                  }
                />
              </div>
            </div>
          </div>

          {/* BlueField */}

          <div className="rounded-xl border border-white/10 bg-[#0c1016] p-6">
            <div className="mb-6">
              <h2 className="text-lg font-semibold">
                BlueField Network Telemetry
              </h2>

              <p className="mt-1 text-xs text-gray-500">
                NVIDIA BlueField-3 + DOCA monitoring
              </p>
            </div>

            <div className="space-y-5">
              <TrafficBar
                label="RX Packets"
                value={totalRxPackets}
                max={Math.max(
                  totalRxPackets,
                  totalTxPackets,
                  1
                )}
              />

              <TrafficBar
                label="TX Packets"
                value={totalTxPackets}
                max={Math.max(
                  totalRxPackets,
                  totalTxPackets,
                  1
                )}
              />
            </div>

            <div className="mt-8 grid grid-cols-2 gap-4">
              <SmallMetric
                title="RX Bytes"
                value={formatBytes(totalRxBytes)}
              />

              <SmallMetric
                title="TX Bytes"
                value={formatBytes(totalTxBytes)}
              />

              <SmallMetric
                title="Interface"
                value={
                  latestEvent?.interface || "-"
                }
                mono
              />

              <SmallMetric
                title="DOCA Device"
                value={latestEvent?.ibdev || "-"}
                mono
              />
            </div>
          </div>
        </section>

        {/* =================================================
            RECENT EVENTS
        ================================================= */}

        <section className="overflow-hidden rounded-xl border border-white/10 bg-[#0c1016]">
          <div className="flex items-center justify-between border-b border-white/10 px-6 py-4">
            <div>
              <h2 className="text-lg font-semibold">
                Recent Security Events
              </h2>

              <p className="mt-1 text-xs text-gray-500">
                OpenSearch indexed security telemetry
              </p>
            </div>

            <div className="text-xs text-gray-500">
              {events.length} events
            </div>
          </div>

          {loading ? (
            <div className="p-8 text-center text-gray-400">
              Loading security events...
            </div>
          ) : events.length === 0 ? (
            <div className="p-8 text-center text-gray-400">
              No security events found
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-black/30 text-xs uppercase text-gray-500">
                  <tr>
                    <th className="px-6 py-3">
                      Time
                    </th>

                    <th className="px-6 py-3">
                      Source
                    </th>

                    <th className="px-6 py-3">
                      Interface
                    </th>

                    <th className="px-6 py-3">
                      Class
                    </th>

                    <th className="px-6 py-3">
                      Score
                    </th>

                    <th className="px-6 py-3">
                      Engine
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {events.map((event) => (
                    <tr
                      key={event.id}
                      className="border-t border-white/5 transition hover:bg-white/5"
                    >
                      <td className="whitespace-nowrap px-6 py-4 text-gray-400">
                        {event.timestamp
                          ? new Date(
                              event.timestamp
                            ).toLocaleString()
                          : "-"}
                      </td>

                      <td className="px-6 py-4">
                        {event.sensor ||
                          event.source_type ||
                          "-"}
                      </td>

                      <td className="px-6 py-4 font-mono text-xs">
                        {event.interface || "-"}
                      </td>

                      <td className="px-6 py-4">
                        <ThreatBadge
                          value={
                            event.threat_class ||
                            "unknown"
                          }
                        />
                      </td>

                      <td className="px-6 py-4 font-semibold">
                        {(
                          event.threat_score ?? 0
                        ).toFixed(2)}
                      </td>

                      <td className="px-6 py-4 text-gray-400">
                        {event.analysis_engine || "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* =================================================
            PIPELINE
        ================================================= */}

        <section className="mt-8 rounded-xl border border-white/10 bg-[#0c1016] p-6">
          <div className="mb-5">
            <h2 className="text-lg font-semibold">
              EDRXDR Pipeline
            </h2>

            <p className="mt-1 text-xs text-gray-500">
              Real-time security processing architecture
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 text-sm">
            <PipelineBox
              text="BlueField-3"
              state={
                status.bluefield
                  ? "online"
                  : "offline"
              }
            />

            <Arrow />

            <PipelineBox
              text="DOCA"
              state={
                status.doca
                  ? "online"
                  : "offline"
              }
            />

            <Arrow />

            <PipelineBox
              text="Kafka"
              state={
                status.kafka
                  ? "online"
                  : "offline"
              }
            />

            <Arrow />

            <PipelineBox
              text="Normalizer"
              state={
                status.normalizer
                  ? "online"
                  : "offline"
              }
            />

            <Arrow />

            <PipelineBox
              text="NVIDIA Morpheus"
              state={
                status.morpheus
                  ? "online"
                  : status.gpuFabric === "waiting"
                    ? "waiting"
                    : "offline"
              }
            />

            <Arrow />

            <PipelineBox
              text="Indexer"
              state={
                status.indexer
                  ? "online"
                  : "offline"
              }
            />

            <Arrow />

            <PipelineBox
              text="OpenSearch"
              state={
                status.opensearch
                  ? "online"
                  : "offline"
              }
            />

            <Arrow />

            <PipelineBox
              text="Dashboard"
              state="online"
            />
          </div>
        </section>
      </div>
    </main>
  );
}

/* =========================================================
   COMPONENTS
========================================================= */

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

function StatusCard({
  name,
  status,
}: {
  name: string;
  status: "online" | "waiting" | "offline";
}) {
  const config = {
    online: {
      text: "● Online",
      color: "text-green-400",
      border: "border-green-500/20",
    },

    waiting: {
      text: "● Waiting",
      color: "text-yellow-400",
      border: "border-yellow-500/20",
    },

    offline: {
      text: "● Offline",
      color: "text-red-400",
      border: "border-red-500/20",
    },
  };

  return (
    <div
      className={`rounded-lg border bg-[#0c1016] p-4 ${config[status].border}`}
    >
      <div className="text-sm font-medium">
        {name}
      </div>

      <div
        className={`mt-2 text-xs ${config[status].color}`}
      >
        {config[status].text}
      </div>
    </div>
  );
}

function ThreatScore({
  score,
}: {
  score: number;
}) {
  const percentage = Math.round(score * 100);

  const border =
    score >= 0.7
      ? "border-red-500"
      : score >= 0.4
        ? "border-yellow-500"
        : "border-green-500";

  return (
    <div
      className={`flex h-36 w-36 shrink-0 items-center justify-center rounded-full border-8 ${border}`}
    >
      <div className="text-center">
        <div className="text-3xl font-bold">
          {percentage}%
        </div>

        <div className="text-xs text-gray-400">
          Threat Score
        </div>
      </div>
    </div>
  );
}

function ThreatBadge({
  value,
}: {
  value: string;
}) {
  const normalized = value.toLowerCase();

  let style =
    "bg-gray-500/10 text-gray-400";

  if (
    normalized === "suspicious" ||
    normalized === "malicious"
  ) {
    style =
      "bg-red-500/10 text-red-400";
  } else if (
    normalized === "normal" ||
    normalized === "benign"
  ) {
    style =
      "bg-green-500/10 text-green-400";
  } else if (
    normalized === "warning"
  ) {
    style =
      "bg-yellow-500/10 text-yellow-400";
  }

  return (
    <span
      className={`rounded-full px-3 py-1 text-xs font-medium ${style}`}
    >
      {value}
    </span>
  );
}

function InfoRow({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div>
      <div className="text-xs text-gray-500">
        {label}
      </div>

      <div className="mt-1 font-medium">
        {value}
      </div>
    </div>
  );
}

function SmallMetric({
  title,
  value,
  mono = false,
}: {
  title: string;
  value: string | number;
  mono?: boolean;
}) {
  return (
    <div className="rounded-lg bg-black/30 p-4">
      <div className="text-xs text-gray-500">
        {title}
      </div>

      <div
        className={`mt-1 text-sm font-medium ${
          mono ? "font-mono" : ""
        }`}
      >
        {value}
      </div>
    </div>
  );
}

function TrafficBar({
  label,
  value,
  max,
}: {
  label: string;
  value: number;
  max: number;
}) {
  const width =
    max > 0
      ? Math.min(
          100,
          (value / max) * 100
        )
      : 0;

  return (
    <div>
      <div className="mb-2 flex justify-between text-sm">
        <span className="text-gray-400">
          {label}
        </span>

        <span>{value}</span>
      </div>

      <div className="h-2 overflow-hidden rounded bg-white/10">
        <div
          className="h-full bg-blue-500 transition-all duration-500"
          style={{
            width: `${width}%`,
          }}
        />
      </div>
    </div>
  );
}

function PipelineBox({
  text,
  state,
}: {
  text: string;
  state: "online" | "waiting" | "offline";
}) {
  const config = {
    online:
      "border-green-500/30 bg-green-500/5 text-green-300",

    waiting:
      "border-yellow-500/40 bg-yellow-500/10 text-yellow-300",

    offline:
      "border-red-500/30 bg-red-500/10 text-red-300",
  };

  return (
    <div
      className={`rounded-lg border px-4 py-2 ${config[state]}`}
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

/* =========================================================
   HELPERS
========================================================= */

function formatBytes(bytes: number) {
  if (bytes === 0) {
    return "0 B";
  }

  const units = [
    "B",
    "KB",
    "MB",
    "GB",
    "TB",
  ];

  const index = Math.floor(
    Math.log(bytes) / Math.log(1024)
  );

  const value =
    bytes / Math.pow(1024, index);

  return `${value.toFixed(2)} ${units[index]}`;
}
