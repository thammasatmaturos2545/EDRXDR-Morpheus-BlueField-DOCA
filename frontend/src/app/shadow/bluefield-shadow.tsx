"use client";

import { useEffect, useState } from "react";

type Row = {
  id: string;
  timestamp: string;
  ingested_at_utc: string;
  ibdev: string;
  interface: string | null;
  operstate: string | null;
  carrier: 0 | 1 | null;
  rx_bytes: number | null;
  tx_bytes: number | null;
  delta_rx_bytes: number | null;
  delta_tx_bytes: number | null;
  sample_interval_seconds: number | null;
  delta_status: {
    rx_bytes: string;
    tx_bytes: string;
  };
  source: {
    topic: "shadow-bluefield-input-v1";
    partition: number;
    offset: number;
  };
};

type Payload = {
  mode: "shadow_bluefield";
  historical: true;
  live: false;
  production_ready: false;
  automated_response_allowed: false;
  source_index: string;
  fetched_at: string;
  counts: {
    records: number;
    interfaces: number;
    carrier_unknown: number;
    rx_zero: number;
    first_sample: number;
    computed: number;
  };
  records: Row[];
};

function payload(value: unknown): value is Payload {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    return false;
  }
  const row = value as Partial<Payload>;
  return (
    row.mode === "shadow_bluefield" &&
    row.historical === true &&
    row.live === false &&
    row.production_ready === false &&
    row.automated_response_allowed === false &&
    typeof row.source_index === "string" &&
    typeof row.fetched_at === "string" &&
    row.counts !== null &&
    typeof row.counts === "object" &&
    Array.isArray(row.records)
  );
}

function when(value: string) {
  return Number.isFinite(Date.parse(value))
    ? new Date(value).toLocaleString("th-TH", { timeZone: "Asia/Bangkok" })
    : "N/A";
}

function nullable(value: number | null) {
  return value === null ? "N/A" : String(value);
}

function carrier(value: 0 | 1 | null) {
  if (value === null) return "Unknown";
  return value === 1 ? "Up" : "Down";
}

export default function BluefieldShadow() {
  const [data, setData] = useState<Payload | null>(null);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      setError("");
      try {
        const response = await fetch("/api/shadow/bluefield", {
          cache: "no-store",
          signal: AbortSignal.any([
            controller.signal,
            AbortSignal.timeout(15000),
          ]),
        });
        const body: unknown = await response.json();

        if (!response.ok || !payload(body)) {
          const message =
            body &&
            typeof body === "object" &&
            !Array.isArray(body) &&
            typeof (body as { error?: unknown }).error === "string"
              ? String((body as { error: string }).error)
              : `API failed (${response.status})`;
          throw new Error(message);
        }

        if (!controller.signal.aborted) setData(body);
      } catch (e) {
        if (!controller.signal.aborted) {
          setError(
            e instanceof Error
              ? e.message
              : "อ่าน BlueField Shadow ไม่สำเร็จ",
          );
        }
      }
    }

    void load();
    return () => controller.abort();
  }, [refresh]);

  return (
    <section id="bluefield-shadow">
      <div className="eyebrow">BLUEFIELD / SHADOW EVIDENCE</div>
      <h2>
        BlueField Shadow Evidence{" "}
        <span className="tag amber">BOUNDED / HISTORICAL / NOT LIVE</span>
      </h2>

      <p>
        ผลจาก archived normalized evidence ที่ผ่าน replay Kafka และ bounded
        indexer เข้า Shadow index เท่านั้น ไม่ใช่ live BlueField telemetry
        และไม่ยืนยัน production readiness
      </p>

      <button onClick={() => setRefresh((value) => value + 1)}>
        อ่าน BlueField Shadow ล่าสุด
      </button>

      {error ? (
        <p className="feed-note">
          <span role="alert" className="error">
            {error}
          </span>
          {data ? " · ตารางด้านล่างเป็นข้อมูลที่อ่านได้ก่อนหน้า" : ""}
        </p>
      ) : data ? (
        <p className="feed-note">
          อ่าน Shadow index เมื่อ {when(data.fetched_at)} · ไม่ใช่เวลา sample
        </p>
      ) : (
        <p className="feed-note">กำลังอ่าน BlueField Shadow…</p>
      )}

      <div className="metrics">
        <div className="metric">
          <span>BlueField Shadow records</span>
          <strong>{data ? data.counts.records : "—"}</strong>
          <small>bounded archived pilot</small>
        </div>
        <div className="metric">
          <span>Interfaces</span>
          <strong>{data ? data.counts.interfaces : "—"}</strong>
          <small>interfaces ใน batch นี้</small>
        </div>
        <div className="metric">
          <span>Carrier unknown</span>
          <strong>{data ? data.counts.carrier_unknown : "—"}</strong>
          <small>null = Unknown ไม่ใช่ 0</small>
        </div>
        <div className="metric">
          <span>First sample / computed</span>
          <strong>
            {data
              ? `${data.counts.first_sample} / ${data.counts.computed}`
              : "—"}
          </strong>
          <small>delta null / delta ที่คำนวณแล้ว</small>
        </div>
      </div>

      {data && (
        <>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  {[
                    "Sample time",
                    "Interface",
                    "IB device",
                    "Operstate",
                    "Carrier",
                    "RX bytes",
                    "TX bytes",
                    "Δ RX bytes",
                    "Δ TX bytes",
                    "Interval",
                    "Shadow source",
                  ].map((value) => (
                    <th key={value}>{value}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.records.map((row) => (
                  <tr key={row.id}>
                    <td>{when(row.timestamp)}</td>
                    <td>{row.interface ?? "N/A"}</td>
                    <td>{row.ibdev}</td>
                    <td>{row.operstate ?? "Unknown"}</td>
                    <td>{carrier(row.carrier)}</td>
                    <td>{nullable(row.rx_bytes)}</td>
                    <td>{nullable(row.tx_bytes)}</td>
                    <td>
                      {nullable(row.delta_rx_bytes)}
                      <small>{row.delta_status.rx_bytes}</small>
                    </td>
                    <td>
                      {nullable(row.delta_tx_bytes)}
                      <small>{row.delta_status.tx_bytes}</small>
                    </td>
                    <td>
                      {row.sample_interval_seconds === null
                        ? "N/A"
                        : `${row.sample_interval_seconds}s`}
                    </td>
                    <td>
                      {row.source.topic}
                      <small>
                        p{row.source.partition} / offset {row.source.offset}
                      </small>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="footnote">
            Source index: {data.source_index} · historical=true · live=false ·
            Automated response OFF · `null` = Unknown/N/A · `0` = ค่าศูนย์จริง
          </p>
        </>
      )}
    </section>
  );
}
