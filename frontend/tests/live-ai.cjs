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

const source =
  fs.readFileSync(
    path.join(
      __dirname,
      "../src/lib/live-ai.ts"
    ),
    "utf8"
  );

const output =
  ts.transpileModule(
    source,
    {
      compilerOptions: {
        module:
          ts.ModuleKind.CommonJS,
        target:
          ts.ScriptTarget.ES2020,
      },
    }
  ).outputText;

const scope = {
  exports: {},
  require,
  console,
  Date,
  Set,
};

vm.runInNewContext(
  output,
  scope
);

const {
  validateLiveAi,
  parseLiveAiSearch,
} = scope.exports;

function event(
  score = 0.75
) {
  return {
    schema_version:
      "live-severity-1",

    event_uid:
      "a".repeat(64),

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

    high_severity_score:
      score,

    predicted_label:
      score >= 0.5
        ? "high_severity"
        : "low_severity",

    threshold:
      0.5,

    wazuh_rule_id:
      "60137",

    wazuh_rule_level:
      5,

    source_topic:
      "wazuh-alerts",

    source_partition:
      0,

    source_offset:
      123,

    input_topic:
      "morpheus-input",

    input_partition:
      0,

    input_offset:
      456,

    scored_at_utc:
      "2026-10-14T15:30:00+00:00",

    production_ready:
      false,

    automated_response_allowed:
      false,

    artifact_hashes: {
      private: "must not leak",
    },

    raw_event: {
      private: true,
    },
  };
}

{
  const d =
    validateLiveAi(
      event(0)
    );

  assert.equal(
    d.high_severity_score,
    0
  );

  assert.equal(
    d.predicted_label,
    "low_severity"
  );

  assert.equal(
    "artifact_hashes" in d,
    false
  );

  assert.equal(
    "raw_event" in d,
    false
  );
}

for (const [
  field,
  value,
] of [
  [
    "schema_version",
    "other",
  ],
  [
    "processing_mode",
    "replay",
  ],
  [
    "analysis_engine",
    "morpheus-simulator",
  ],
  [
    "model_name",
    "other-model",
  ],
  [
    "production_ready",
    true,
  ],
  [
    "automated_response_allowed",
    true,
  ],
]) {
  const d = event();
  d[field] = value;

  assert.throws(
    () =>
      validateLiveAi(d)
  );
}

for (const bad of [
  -0.1,
  1.1,
  NaN,
  Infinity,
  true,
]) {
  const d = event();
  d.high_severity_score =
    bad;

  assert.throws(
    () =>
      validateLiveAi(d)
  );
}

{
  const d = event();
  d.predicted_label =
    "low_severity";

  assert.throws(
    () =>
      validateLiveAi(d)
  );
}

{
  const d = event();
  d.source_offset = -1;

  assert.throws(
    () =>
      validateLiveAi(d)
  );
}

{
  const d = event();

  const result =
    parseLiveAiSearch({
      timed_out: false,

      _shards: {
        failed: 0,
      },

      hits: {
        total: {
          value: 1,
          relation: "eq",
        },

        hits: [
          {
            _source: d,
          },
        ],
      },
    });

  assert.equal(
    result.total,
    1
  );

  assert.equal(
    result.events.length,
    1
  );
}

{
  const d = event();

  assert.throws(
    () =>
      parseLiveAiSearch({
        timed_out: false,

        _shards: {
          failed: 0,
        },

        hits: {
          total: {
            value: 2,
            relation: "eq",
          },

          hits: [
            {
              _source: d,
            },
            {
              _source: {
                ...d,
              },
            },
          ],
        },
      })
  );
}

for (const body of [
  {
    timed_out: true,
    _shards: {
      failed: 0,
    },
    hits: {
      total: {
        value: 0,
        relation: "eq",
      },
      hits: [],
    },
  },

  {
    timed_out: false,
    _shards: {
      failed: 1,
    },
    hits: {
      total: {
        value: 0,
        relation: "eq",
      },
      hits: [],
    },
  },

  {
    timed_out: false,
    _shards: {
      failed: 0,
    },
    hits: {
      total: {
        value: 0,
        relation: "gte",
      },
      hits: [],
    },
  },
]) {
  assert.throws(
    () =>
      parseLiveAiSearch(
        body
      )
  );
}

console.log(
  "PASS: live AI API validates exact Morpheus contract, preserves zero score, rejects unsafe/incomplete results, and removes internal/raw fields"
);
