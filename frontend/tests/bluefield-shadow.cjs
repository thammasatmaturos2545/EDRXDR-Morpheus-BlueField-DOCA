/* eslint-disable @typescript-eslint/no-require-imports */
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const ts = require("typescript");

function load(name, overrides = {}, globals = {}) {
  const exports = {};
  const file = path.join(__dirname, "..", name);
  const js = ts.transpileModule(fs.readFileSync(file, "utf8"), {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      jsx: ts.JsxEmit.ReactJSX,
      esModuleInterop: true,
      target: ts.ScriptTarget.ES2022,
    },
  }).outputText;
  vm.runInNewContext(js, {
    exports,
    require: (n) => overrides[n] ?? require(n),
    Map,
    Set,
    Date,
    URL,
    AbortSignal,
    console,
    ...globals,
  });
  return exports;
}

const lib = load("src/lib/bluefield-shadow.ts");

const base = {
  schema_version: "shadow-bluefield-1",
  processing_mode: "shadow",
  evidence_mode: "archived_normalized_replay",
  historical: true,
  production_ready: false,
  automated_response_allowed: false,
  source_type: "bluefield",
  measurement_scope: "host_interface_counters",
  sample_uid: "a".repeat(64),
  input_sha256: "b".repeat(64),
  capture_scope_sha256: "c".repeat(64),
  timestamp: "2026-10-11T18:45:32Z",
  ingested_at_utc: "2026-10-12T18:21:31Z",
  source: {
    cluster_id: "cluster",
    topic: "shadow-bluefield-input-v1",
    partition: 0,
    offset: 0,
  },
  ibdev: "mlx5_0",
  interface: "enp6s17f0np0",
  operstate: "down",
  carrier: null,
  rx_packets: 0,
  tx_packets: 0,
  rx_bytes: 0,
  tx_bytes: 0,
  rx_errors: 0,
  tx_errors: 0,
  delta_rx_packets: null,
  delta_tx_packets: null,
  delta_rx_bytes: null,
  delta_tx_bytes: null,
  delta_rx_errors: null,
  delta_tx_errors: null,
  delta_status: {
    rx_packets: "first_sample",
    tx_packets: "first_sample",
    rx_bytes: "first_sample",
    tx_bytes: "first_sample",
    rx_errors: "first_sample",
    tx_errors: "first_sample",
  },
  sample_interval_seconds: null,
};

const computed = {
  ...base,
  sample_uid: "d".repeat(64),
  input_sha256: "e".repeat(64),
  timestamp: "2026-10-11T18:45:34Z",
  source: { ...base.source, offset: 1 },
  delta_rx_packets: 0,
  delta_tx_packets: 0,
  delta_rx_bytes: 0,
  delta_tx_bytes: 0,
  delta_rx_errors: 0,
  delta_tx_errors: 0,
  delta_status: {
    rx_packets: "computed",
    tx_packets: "computed",
    rx_bytes: "computed",
    tx_bytes: "computed",
    rx_errors: "computed",
    tx_errors: "computed",
  },
  sample_interval_seconds: 2,
};

const response = (rows) => ({
  timed_out: false,
  _shards: { failed: 0 },
  hits: {
    total: { value: rows.length, relation: "eq" },
    hits: rows.map((row, i) => ({
      _id: `doc-${i}`,
      _source: row,
    })),
  },
});

let count = 0;
function test(name, fn) {
  fn();
  count++;
  console.log("PASS", name);
}

test("null carrier and first-sample delta remain null while zero counter remains zero", () => {
  const [row] = lib.bluefieldShadowDocuments(response([base]));
  assert.equal(row.carrier, null);
  assert.equal(row.rx_bytes, 0);
  assert.equal(row.delta_rx_bytes, null);
  assert.equal(row.sample_interval_seconds, null);
});

test("computed zero remains numeric zero", () => {
  const [row] = lib.bluefieldShadowDocuments(response([computed]));
  assert.equal(row.delta_rx_bytes, 0);
  assert.equal(row.delta_tx_bytes, 0);
  assert.equal(row.sample_interval_seconds, 2);
});

test("wrong safety flags or evidence mode fail closed", () => {
  for (const patch of [
    { processing_mode: "live" },
    { historical: false },
    { production_ready: true },
    { automated_response_allowed: true },
    { evidence_mode: "live" },
  ]) {
    assert.throws(() =>
      lib.bluefieldShadowDocuments(response([{ ...base, ...patch }])),
    );
  }
});

test("live BlueField topic is rejected", () => {
  assert.throws(() =>
    lib.bluefieldShadowDocuments(
      response([
        {
          ...base,
          source: { ...base.source, topic: "bluefield-events" },
        },
      ]),
    ),
  );
});

test("delta status cannot rewrite null/zero meaning", () => {
  assert.throws(() =>
    lib.bluefieldShadowDocuments(
      response([{ ...base, delta_rx_bytes: 0 }]),
    ),
  );
  assert.throws(() =>
    lib.bluefieldShadowDocuments(
      response([{ ...computed, delta_rx_bytes: null }]),
    ),
  );
});

test("unknown/raw fields are not projected to the browser", () => {
  const [row] = lib.bluefieldShadowDocuments(
    response([
      {
        ...base,
        raw_event: { secret: "PRIVATE" },
        capture_scope: "/home/private",
        unknown_nested: { secret: "PRIVATE" },
      },
    ]),
  );
  const text = JSON.stringify(row);
  assert.equal(text.includes("PRIVATE"), false);
  assert.equal(text.includes("/home/private"), false);
});

test("partial/unbounded/duplicate results fail closed", () => {
  const partial = response([base]);
  partial._shards.failed = 1;
  assert.throws(() => lib.bluefieldShadowDocuments(partial));

  const lower = response([base]);
  lower.hits.total.relation = "gte";
  assert.throws(() => lib.bluefieldShadowDocuments(lower));

  const duplicate = response([base, computed]);
  duplicate.hits.hits[1]._id = duplicate.hits.hits[0]._id;
  assert.throws(() => lib.bluefieldShadowDocuments(duplicate));
});

async function routeTests() {
  const env = {};
  let calls = 0;

  const route = load(
    "src/app/api/shadow/bluefield/route.ts",
    {
      "@/lib/bluefield-shadow": lib,
      "next/server": {
        NextResponse: {
          json: (body, init = {}) => ({
            body,
            status: init.status ?? 200,
          }),
        },
      },
    },
    {
      process: { env },
      fetch: async (url, options) => {
        calls++;
        assert.ok(url.endsWith("/shadow-bluefield-v1/_search"));
        assert.equal(options.method, "POST");
        assert.equal(options.redirect, "error");
        return {
          ok: true,
          json: async () => response([base, computed]),
        };
      },
    },
  );

  assert.equal((await route.GET()).status, 503);
  assert.equal(calls, 0);

  env.SHADOW_OPENSEARCH_URL = "http://127.0.0.1:19200";
  const good = await route.GET();
  assert.equal(good.status, 200);
  assert.equal(good.body.mode, "shadow_bluefield");
  assert.equal(good.body.historical, true);
  assert.equal(good.body.live, false);
  assert.equal(good.body.production_ready, false);
  assert.equal(good.body.automated_response_allowed, false);
  assert.equal(good.body.counts.records, 2);
  assert.equal(good.body.counts.carrier_unknown, 2);
  assert.equal(good.body.counts.first_sample, 1);
  assert.equal(good.body.counts.computed, 1);
  assert.equal(good.body.records[0].carrier, null);
  assert.equal(good.body.records[1].delta_rx_bytes, 0);

  env.SHADOW_OPENSEARCH_URL = "http://user:secret@localhost:9200";
  assert.equal((await route.GET()).status, 502);
  assert.equal(calls, 1);

  console.log(
    `PASS: ${count + 3} BlueField Shadow frontend/API checks ` +
      "(synthetic fixtures; no live/service claim)",
  );
}

routeTests().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
