# DFP / Ransomware checkpoint — 2026-11-03

## Scope
- Continue DFP for Linux Agent003.
- Agent004 work deferred; Network telemetry excluded.
- Preserve WIP, protected datasets, models and evidence.

## Verified
- Model Lab deployed: release-appshield-41Z1YA3K/frontend.
- Lab reader verified 773 observations: DFP 666, Ransomware 107.
- AppShield sample: 106 real windows, 297 features, CPU inference passed.
- Ransomware outputs remain output_0/output_1; class mapping unverified.
- Agent003 FIM event reached wazuh-alerts:0:39150 and morpheus-input:0:70510.
- Agent003 original config restored; service active.
- NVIDIA dfencoder CPU adaptation initialized and synthetic fit/score passed.
- CPU adaptation only omits copied package initializer's cuDF import.
  It is not upstream CPU-support certification.
- Bounded archive pilot finished RESTORED; logall_json=no.
- New capture: 197 records; Agent003 164, preserved as 4 archive-feature windows.
- Exact repeated-line occurrences preserved: 2.

## Evidence on VM
- CPU adaptation: /home/saiuser/edrxdr-nvidia-lab-znmqaTGL/dfp-cpu-adapter-RMNy70Z4
- FIM probe: /home/saiuser/edrxdr-nvidia-lab-znmqaTGL/agent003-fim-probe-DmgSHeY1
- Probe state: /mnt/nexus-copilot-mQTssj/archive-probe-prepared-9w75klwg/approved-probe-j3326aq8
- Frozen capture: /home/saiuser/edrxdr-nvidia-lab-znmqaTGL/agent003-archive-pilot-9dlus1zj
- Archive features: /home/saiuser/edrxdr-nvidia-lab-znmqaTGL/agent003-archive-features-yk8lawlh
- Capture SHA256: 7218e0713795752507824f5470788442a4d6c770b2c20b5232976302bbcc6c37

## Remaining work
- Live BERT has NOT been replaced.
- Existing 237 Agent003 alert windows have pending protected-membership review.
- Archive features (7) and alert features (10) are separate contracts.
- Four new archive windows do not support a credible train/evaluation split.
- Pilot contains manager restart context; normal baseline and time membership unverified.
- No real Wazuh DFP model trained or live anomaly threshold established.
- Live Ransomware requires compatible endpoint telemetry; sample replay is complete.
- Next: define a versioned DFP feature/collection protocol and sufficient
  prospective baseline with source coverage, exclusions and chronological validation.
- No further logging/collection is running under this checkpoint.

## Data handling
Keep private logs, memberships, keys, datasets and weights on VM.
Do not stage private artifacts or overwrite prior evidence.
