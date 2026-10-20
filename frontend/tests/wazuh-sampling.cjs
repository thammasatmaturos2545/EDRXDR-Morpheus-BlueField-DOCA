const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ts = require("typescript");
const vm = require("node:vm");

const source = fs.readFileSync(
  path.join(__dirname, "../src/lib/wazuh-sampling.ts"),
  "utf8"
);

const js = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2022
  }
}).outputText;

const context = { exports: {}, Map, Set };
vm.runInNewContext(js, context);

const sample = context.exports.selectBalancedWazuhAlerts;
assert.equal(typeof sample, "function");

const uid = "a".repeat(64);
const alerts = [];

for (let i = 0; i < 800; i++) {
  alerts.push({ id: `win-old-${i}`, agent_id: "004" });
}

for (const kind of ["added", "modified", "deleted",
                    "added", "modified", "deleted"]) {
  alerts.push({
    id: `kali-${alerts.length}`,
    agent_id: "005",
    event_uid: uid,
    kind
  });
}

for (let i = 0; i < 800; i++) {
  alerts.push({ id: `win-new-${i}`, agent_id: "004" });
}

for (let i = 0; i < 40; i++) {
  alerts.push({ id: `server-${i}`, agent_id: "003" });
}

assert.equal(
  alerts.slice(-100).some(a => a.agent_id === "005"),
  false
);

const result = sample(alerts);
const count = id => result.filter(a => a.agent_id === id).length;

assert.equal(result.length, 100);
assert.equal(count("005"), 6);
assert.equal(count("003"), 40);
assert.equal(count("004"), 54);
assert.equal(result.every((a, i) =>
  i === 0 || alerts.indexOf(result[i - 1]) > alerts.indexOf(a)
), true);
assert.equal(
  result.filter(a => a.agent_id === "005")
    .every(a => a.event_uid === uid),
  true
);
assert.equal(new Set(result.map(a => a.id)).size, 100);
assert.equal(sample([]).length, 0);

console.log("PASS: Maximum 100 alerts");
console.log("PASS: Kali retained under noisy Windows traffic");
console.log("PASS: Per-agent sampling");
console.log("PASS: Event order and UID preserved");
console.log("PASS: No duplicates and empty input");
console.log("AGENTS:", JSON.stringify({
  "004": count("004"),
  "003": count("003"),
  "005": count("005")
}));
