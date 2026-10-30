# BERT v4 next handoff — 2026-10-31

Read `BERT-V4-DEV-DIAGNOSTICS-20261031.md` and
`BERT-V4-ORDER-ABLATION-20261031.md` with the original project handoff.
Base HEAD `a736f4da520fe80ee242e3012a0748bca4c3b7a7` on `work/nexus-exact-ai-v1`; check current HEAD/WIP again.

## Completed this round

- B checkpoint verified8/8; Windows backup verified8/8 earlier by operator.
- Windows private checkpoint backup:
  `C:/Users/fewxs/AppData/Local/EDRXDR-private-backups/bert-v4-expB-e4a1d31ba0cc40328a7d3344ae151c84`.
- Dev CPU counts, fixed train-count source-only baselines, source-span audit,
  CPU and GPU bf16 block-order sensitivity runs completed. No training rerun.
- Only saved B checkpoint evaluated. A reports preserved; A rerun not performed.
- GPU evaluation container checked exited0/noOOM, no longer running.
- Observed GPU process metadata captured privately in closure summary. Do not stop peers.
- No new GPU work started by closure. Prior GPU permission ends03:00 Oct31;
  it is not authorization for future work. Recheck reservation/guard before GPU.
- Final holdout family6 and metadata/labels-16695.json were not opened.
- Runtime status recorded read-only; no deploy/restart/offset or shared-state changes.

## Next work, no automatic training/final test

1. Review per-tactic/order errors privately; distinguish weak labels, missing content,
   source availability and serialized-position sensitivity without claiming causality.
2. Recover the original builder/source selection provenance for full reproducibility.
   Do not overwrite frozen data or silently remove possible-label-hint steps.
3. If proposing a stronger source-only/content ablation or data/model revision,
   write a separate protocol/version and obtain authorization before new training.
4. Freeze candidate, metrics, limitations and final-evaluation procedure before any
   one-time family6 evaluation. Current results do not approve that gate.
5. Keep v4 eleven-tactic attack-step model separate from binary NEXUS Severity.
6. Keep69 organization-review entries pending; no deletion approval was issued.

Preserve untracked history/uid_lookup/evidence/handoffs, A/v3/recovery and backups.
Never reset/clean, git add ., build over runtime .next, change drivers/network,
stop LuckyFive/shared stack, auto-consume offsets, enable response or BlueField/rshim.
No logs/datasets/weights/private predictions in Git or external prompts.

## Current read-only runtime snapshot

```json
{
  "nexus-all-events-prod-3006.service": {
    "MainPID": "1140935",
    "Result": "success",
    "WorkingDirectory": "/home/saiuser/nexus-uid-candidate-wgpajvXL",
    "Id": "nexus-all-events-prod-3006.service",
    "ActiveState": "active",
    "SubState": "running"
  },
  "nexus-live-indexer.service": {
    "MainPID": "1203399",
    "Result": "success",
    "WorkingDirectory": "!/home/saiuser",
    "Id": "nexus-live-indexer.service",
    "ActiveState": "active",
    "SubState": "running"
  },
  "nexus-history-sync.service": {
    "MainPID": "2908528",
    "Result": "success",
    "WorkingDirectory": "/home/saiuser/nexus-history-preview-20261020",
    "Id": "nexus-history-sync.service",
    "ActiveState": "activating",
    "SubState": "start"
  },
  "nexus-history-sync.timer": {
    "Result": "success",
    "Id": "nexus-history-sync.timer",
    "ActiveState": "active",
    "SubState": "running"
  },
  "edrxdr-bluefield.service": {
    "ActiveState": "inactive",
    "SubState": "dead",
    "UnitFileState": "disabled"
  },
  "rshim.service": {
    "ActiveState": "inactive",
    "SubState": "dead",
    "UnitFileState": "disabled"
  },
  "dashboard_root_http": 200
}
```

This snapshot is not an end-to-end live AI scoring or reboot recovery proof.
Closure summary: `/home/saiuser/EDRXDR-BERTv4-work/evidence/dev-diagnostics-close-5gt1oep0/closure-summary.json`.
