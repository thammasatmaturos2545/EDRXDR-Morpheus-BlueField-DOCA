# Controlled endpoint comparison — PREPARED NOT APPLIED

Agent003 scratch testing only, not selection of owner real protected files. Baseline12helper-created plain text files in a fresh root-private probe directory. No ransomware/encryption, filedeletion or whole-drive monitoring. Three reference scenarios:4quiet modifications spaced2sec;8normal bulk modifications;8controlled fast modifications.20writes total, each<1KiB. Case labels describe helper actions/intent, NOT attack/benign groundtruth or accepted training labels.

Runtime scope needing explicit approval: add one realtime FIM directory/check_all=yes/report_changes=no; restart only local wazuh-agent for activation and restoration. No whodata/audit installation. Root-owned independent restoration timer armed beforeconfigwrite, attempts restoration after10min; normal workflow restores earlier. Existing oldmode/owner/config bytes backed up, no-overwrite/concurrent-change guards and previous incomplete probes block another run. Retain all private evidence. No guarantee if host/systemd itself fails.

After120sec baseline wait (not automatic fullscan acceptance), scenarios run in separate minute slots, write only known owned files, then read <=8MiB of current Manager alert tail in memory. Verify group project=wazuh/service=wazuh.manager, activeAgent003 registry name matching local context (notphysicalattestation), filter only fresh target paths. Match each modification by exact syntheticfile path and expected sha256_after. Dedup identical alertIDs, reject conflicts/foreign/missing identities/modes. Partial/rotated missingalerts stay incomplete; no retry. No raw logs or identity/hash references exported, only aggregatecounts; private case timestamps and summaries saved under newroot.

Case signatures are measured aggregate action/cardinality counts, NOT full time-window featurevectors, classifier scores or independent malware detection quality. Matching bulk/fast signatures show ambiguity of those counts; different signatures do not prove a ransomware classifier. No threshold selected or model fitted/loaded. No new GPU/training/observer or productionNEXUS changes. Original observer continues untouched; sudo/testactivity must retain experimentalcontext, notbe labelled allbenign. Existing Wazuh forwarding/legacy pipeline may process these testevents; helper does not directly publishKafka/OpenSearch or start model/GPU services.

Before activation: python3 -B probe.py --describe-plan
Synthetic tests only: python3 -B -m unittest discover -p 'test_*.py' -v
Approved activation only: sudo python3 -B probe.py --apply-approved-controlled-comparison
Rollback callback: root-owned copied probe.py --restore exact privateprobe path. No source data/backups/deletion or disablecommands authorized by thisfile.

References for FIM modified-event checksum fields: https://documentation.wazuh.com/current/user-manual/capabilities/file-integrity/creating-custom-fim-rules.html
