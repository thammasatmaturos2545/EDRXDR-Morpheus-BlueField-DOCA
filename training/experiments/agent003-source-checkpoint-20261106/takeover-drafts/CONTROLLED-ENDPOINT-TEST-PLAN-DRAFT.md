# Controlled endpoint test plan — NOT APPLIED

Owner must choose controlled scratch testing or a protected data path; no real protected folder selected by AI. Agent003 only. No malware, GPU, new training or observer extension. Existing DFP round ends6Novabout04:00+07. This document does not authorize enabling FIM/whodata/logging or starting a service.

Purpose of next endpoint experiment, if approved: characterize measurable file-change behavior and benign bulk-workload confounders, not repeat12/12transport as detectionquality. Existing config was restored to scheduledFIM12h, no accepted realtime coverage or process attribution remains active.

Proposed isolated experiment controls: one freshly created private scratch directory with only helper-created textfiles, small file-count/byte bounds, explicit operation times and reference scenario labels, configuration backup/exact-change guard, independent restoration timer armed before configchange, only local wazuh-agent restart at activation/restoration. Never monitor the whole drive or overwrite/delete userfiles. Preserve source manifests and annotate experimental activity in the original DFP observation; no all-benign labels.

Reference scenarios to freeze before applying: quiet small edits; normal bulk copy/update; controlled rapid modifications/deletions/renames of owned synthetic textfiles. The last scenario is a synthetic behavior case, NOT actual ransomware or proof of maliciousness. Each scenario needs its own known interval/source membership; stable baseline scan verification and event delivery precede interpretation. Separate reference labels from input features; don't use scenario name, filename convention or test schedule as model inputs.

Critical capability limit: current file_behavior.py retains windowed action/path cardinality counts. Benign bulk updates and suspicious bulk changes can have the same feature vector. FIM delivery alone does not observe encryption or attribute a malicious process. Quantify nuisance behavior; do not choose a threshold to fit these few scenarios and call it a ransomware classifier. A process/who-data or content-derived feature proposal needs capability review and separate scoped authorization. Exam requirement for a trained classifier is still unknown.

Engineering acceptance: bounded owned-file operations/source membership/timestamps matchreceivedAgent003FIM events; retry/late-window accounting; missing/foreign events explicit; old config restored and agent ready; no source events/private paths exported. Detectionquality acceptance remains a separate frozen protocol with independentreferencecases, falsealert budget, coverage and labels; no tuning on independenttestcases.

No actual test started by preparing this draft. No protected-path choice or additional runtime permission inferred.
