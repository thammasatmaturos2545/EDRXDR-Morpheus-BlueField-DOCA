/* eslint-disable @typescript-eslint/no-require-imports */

const assert =
  require("node:assert/strict");

const fs =
  require("node:fs");

const path =
  require("node:path");

const ts =
  require("typescript");

const vm =
  require("node:vm");

const src =
  fs.readFileSync(
    path.join(
      __dirname,
      "../src/lib/nexus-soc.ts"
    ),
    "utf8"
  );

const out =
  ts.transpileModule(
    src,
    {
      compilerOptions: {
        module:
          ts.ModuleKind.CommonJS,
        target:
          ts.ScriptTarget.ES2022,
      },
    }
  ).outputText;

const endpointExports = {};
vm.runInNewContext(ts.transpileModule(
  fs.readFileSync(path.join(__dirname, '../src/lib/nexus-endpoints.ts'), 'utf8'),
  {compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}
).outputText, {exports:endpointExports, Date, Map, Set});
const scope = {
  require: name => {
    if (name === '@/lib/nexus-endpoints') return endpointExports;
    throw new Error('Unexpected dependency: ' + name);
  },
  exports: {},
  Date,
  Set,
};

vm.runInNewContext(
  out,
  scope
);

const {
  correlateWazuhAi,
  buildNexusSnapshot,
} = scope.exports;

const UID1 =
  "a".repeat(64);

const UID2 =
  "b".repeat(64);

const ai = {
  schema_version:
    "live-severity-1",

  source_type:
    "wazuh",

  processing_mode:
    "live",

  analysis_engine:
    "nvidia-morpheus-context-severity-v1",

  model_name:
    "wazuh-severity-context-v2-balanced-20261008T190719Z-1398863",

  text_contract_version:
    "wazuh-context-v2-raw-1",

  event_uid:
    UID1,

  high_severity_score:
    0,

  predicted_label:
    "low_severity",

  threshold:
    0.5,

  wazuh_rule_id:
    "100",

  wazuh_rule_level:
    0,

  source_topic:
    "wazuh-alerts",

  source_partition:
    0,

  source_offset:
    7,

  input_topic:
    "morpheus-input",

  input_partition:
    0,

  input_offset:
    12,

  scored_at_utc:
    "2026-10-14T00:00:30Z",

  production_ready:
    false,

  automated_response_allowed:
    false,
};

/*
 * Exact event_uid match succeeds.
 */
assert.equal(
  correlateWazuhAi(
    {
      event_uid:
        UID1,
    },
    [ai],
    true
  ).method,
  "event_uid"
);

/*
 * Same timestamp / hash / source context
 * must NOT compensate for a different UID.
 */
assert.equal(
  correlateWazuhAi(
    {
      event_uid:
        UID2,

      raw_sha256:
        "same-hash",

      timestamp:
        "2026-10-14T00:00:00Z",

      source_topic:
        "wazuh-alerts",

      source_partition:
        0,

      source_offset:
        7,
    },
    [
      {
        ...ai,

        event_uid:
          UID1,

        raw_sha256:
          "same-hash",

        timestamp:
          "2026-10-14T00:00:00Z",
      },
    ],
    true
  ).status,
  "not_found"
);

/*
 * No UID means no match even with identical time.
 */
assert.equal(
  correlateWazuhAi(
    {
      timestamp:
        "2026-10-14T00:00:00Z",
    },
    [
      {
        ...ai,

        timestamp:
          "2026-10-14T00:00:00Z",
      },
    ],
    true
  ).status,
  "not_found"
);

/*
 * Duplicate AI results for one UID fail closed.
 */
assert.equal(
  correlateWazuhAi(
    {
      event_uid:
        UID1,
    },
    [
      ai,
      {
        ...ai,
      },
    ],
    true
  ).status,
  "conflict"
);

assert.equal(
  correlateWazuhAi(
    {
      event_uid:
        UID1,
    },
    [ai],
    false
  ).status,
  "unavailable"
);

const snapshot =
  buildNexusSnapshot(
    {
      alerts: [
        {
          rule_level:
            0,

          rule_id:
            "100",

          description:
            "Real zero",

          agent_name:
            "WIN-01",

          event_uid:
            UID1,

          timestamp:
            "2026-10-14T00:00:00Z",

          full_log:
            "PRIVATE",
        },

        {
          rule_level:
            null,

          rule_id:
            "101",

          description:
            "Unknown level",

          agent_name:
            "WIN-02",

          timestamp:
            "2026-10-14T00:01:00Z",
        },
      ],
    },

    {
      events: [
        ai,
      ],
    },

    {
      hours: 24,
      aiAvailable: true,
      generatedAt:
        "2026-10-14T01:00:00Z",
    }
  );

assert.equal(
  snapshot.alerts[0]
    .evidence
    .wazuh_level,
  0
);

assert.equal(
  snapshot.alerts[0]
    .evidence
    .ai_status,
  "matched"
);

assert.equal(
  snapshot.alerts[0]
    .evidence
    .ai_match_method,
  "event_uid"
);

/*
 * Real zero score survives.
 */
assert.equal(
  snapshot.alerts[0]
    .evidence
    .ai_score,
  0
);

assert.equal(
  snapshot.alerts[0]
    .evidence
    .ai_label,
  "low_severity"
);

assert.equal(
  snapshot.alerts[0]
    .evidence
    .ai_engine,
  "nvidia-morpheus-context-severity-v1"
);

assert.equal(
  snapshot.alerts[0]
    .evidence
    .ai_model,
  "wazuh-severity-context-v2-balanced-20261008T190719Z-1398863"
);

assert.equal(
  snapshot.alerts[1]
    .severity,
  "unknown"
);

assert.equal(
  snapshot.alerts[1]
    .evidence
    .ai_status,
  "not_found"
);

assert.equal(
  snapshot.alerts[1]
    .evidence
    .ai_score,
  null
);

assert.equal(
  JSON.stringify(
    snapshot
  ).includes(
    "PRIVATE"
  ),
  false
);

/*
 * Legacy/generic "real-engine" + threat_score
 * is no longer acceptable as live AI.
 */
assert.throws(
  () =>
    buildNexusSnapshot(
      {
        alerts: [
          {
            event_uid:
              UID1,
          },
        ],
      },

      {
        events: [
          {
            event_uid:
              UID1,

            processing_mode:
              "live",

            analysis_engine:
              "real-engine",

            threat_score:
              0,
          },
        ],
      },

      {
        aiAvailable:
          true,
      }
    )
);

/*
 * If the AI endpoint is unavailable,
 * no result is inferred.
 */
const unavailable =
  buildNexusSnapshot(
    {
      alerts: [
        {
          event_uid:
            UID1,
        },
      ],
    },

    {
      events: [],
    },

    {
      aiAvailable:
        false,

      generatedAt:
        "2026-10-14T01:00:00Z",
    }
  );

assert.equal(
  unavailable.alerts[0]
    .evidence
    .ai_status,
  "unavailable"
);

assert.equal(
  unavailable.alerts[0]
    .evidence
    .ai_score,
  null
);

const html =
  fs.readFileSync(
    path.join(
      __dirname,
      "../public/nexus/index.html"
    ),
    "utf8"
  );

const app =
  fs.readFileSync(
    path.join(
      __dirname,
      "../public/nexus/app.js"
    ),
    "utf8"
  );

const core =
  fs.readFileSync(
    path.join(
      __dirname,
      "../public/nexus/core.js"
    ),
    "utf8"
  );

assert(
  html.includes(
    "NEXUS"
  )
);

assert(
  html.includes(
    "SIEM PLATFORM"
  )
);

assert(
  html.includes(
    "EDR / XDR Lab"
  )
);

for (const label of [
  "Security overview",
  "Threat detection",
  "Endpoints",
  "Investigations",
  "Log explorer",
  "ATT&CK activity",
  "Data sources",
  "Settings",
]) {
  assert(
    app.includes(
      label
    )
  );
}

assert(
  app.includes(
    "connect('/api/v1','')"
  )
);

assert(
  app.includes(
    "AI severity analysis"
  )
);

assert(
  app.includes(
    "คะแนนความรุนแรงจาก AI"
  )
);

assert(
  app.includes(
    "ยังไม่มีผล AI"
  )
);

assert(
  app.includes(
    "Exact event_uid"
  )
);

assert(
  core.includes(
    "'unknown'"
  )
);

console.log(
  "PASS NEXUS: exact event_uid-only AI correlation, real zero score, no inferred match, and visible AI severity details"
);
