# เริ่มรับช่วง EDRXDR–Morpheus–NEXUS — 3 พฤศจิกายน 2026

เอกสารนี้สรุปจาก output ที่ผู้ปฏิบัติงานส่งในแชท ไม่ใช่การตรวจ VM ณ เวลาที่เปิดไฟล์ ผู้รับต้องตรวจสถานะปัจจุบันแบบอ่านอย่างเดียวก่อน

## ข้อความส่งให้เพื่อน

รับช่วง EDRXDR–Morpheus–NEXUS ต่อได้ที่ VM `saiuser@172.16.30.147`
Repo: `/home/saiuser/EDRXDR-Morpheus`
Branch: `work/nexus-exact-ai-v1`
Commit ล่าสุดที่ยืนยัน: `b426351`

เริ่มอ่านไฟล์นี้ แล้วอ่าน `training/HANDOFF-DFP-APPSHIELD-PROGRESS-20261103.md` และ `training/experiments/archive-cpu-prototype-v1/README.md` ก่อนตรวจ Git/runtime แบบอ่านอย่างเดียว

Model Lab deploy แล้ว รองรับผลรวมที่ตรวจล่าสุด 773 observations: DFP Duo 666 และ Ransomware CPU 107 ซึ่งรวม AppShield sample ใหม่ 106 windows ส่วน Wazuh DFP CPU prototype ฝึก/save/reload/inference ผ่านบน 12 windows แล้ว แต่ยังเป็น in-sample diagnostics และยังไม่ได้ deploy เข้า live หรือแทน BERT

ขอบเขตต่อไป: DFP บน Linux Agent003; Ransomware คง sample replay ก่อน งาน Agent004 เครื่องเพื่อนพักไว้ และ Network telemetry อยู่นอก scope
ช่วงส่งต่องานให้หยุดการเริ่ม GPU/training/logging/collector รอบใหม่ไว้ก่อน จนเจ้าของงานยืนยันการรันรอบถัดไป รักษา WIP ข้อมูล โมเดล และหลักฐานทั้งหมด ห้าม reset/clean หรือใส่ raw logs/datasets/weights/keys ลง Git หรือแชท บริการ NEXUS/Agent/Manager เดิมไม่ต้องหยุด

## อ่านตามลำดับ

1. เอกสารนี้ — สถานะล่าสุดถึง b426351
2. `training/HANDOFF-DFP-APPSHIELD-PROGRESS-20261103.md` — อ่านส่วน Follow-up ท้ายไฟล์ด้วย ซึ่งอัปเดตข้อความเก่าที่บอกว่ายังไม่ฝึก prototype
3. `training/experiments/archive-cpu-prototype-v1/README.md`
4. `training/experiments/archive-cpu-prototype-v1/receipt.json`
5. `training/START-HERE-LIVE-20261103.md`, `training/HANDOFF-NEXUS-LIVE-NEXT-20261103.md`, `training/HANDOFF-NEXUS-MODEL-LAB-20261103.md` — เอกสารก่อนหน้า อาจอ้าง commit/runtime เก่า
6. `training/DFP-RANSOMWARE-LAB-TRANSPORT-20261103.md` หากมีบน VM (ล่าสุดยัง untracked)

## งานที่เสร็จและหลักฐาน

### Model Lab / Ransomware

- NVIDIA model: `ransomw-model-short-rf`, version 1, Triton CPU
- CPU container ที่ใช้: `edrxdr-ransom-cpu-YAHmi5uA` (ต้องตรวจว่ายังทำงานหรือไม่)
- Raw AppShield sample 15 files, snapshots 1/2/3 ของหนึ่ง source
- สร้าง 106 real process windows, input shape [106,297], skip insufficient snapshots 19, nonfinite 0, dummy scored 0
- Inference 4 requests สำเร็จ 4; ผลเป็น output_0/output_1 เพราะ class mapping ยังไม่ยืนยัน
- ส่ง 106 observations เข้า lab Kafka/OpenSearch แล้ว ตรวจเอกสารครบ 106
- Batch NDJSON SHA256: `37a60e580d0f662b478507bb07bc845cb620849e0ef0bafb20b87da45d1c53b0`
- Consumer group: `edrxdr-lab-ai-appshield-37a60e580d0f662b`
- Topic: `edrxdr-lab-ai-observations-v1`; index: `edrxdr-ai-lab-v1`
- API reader ตรวจครบ 773: DFP 666, Ransomware 107 ไม่ใช่ 773 live alerts
- API/UI offline tests, TypeScript และ build ผ่าน; unauthenticated lab endpoint ตอบ 401
- ยังไม่มีผล real browser acceptance หลัง release ใหม่นี้ยืนยันในแชท

### NEXUS release

- Service: `nexus-all-events-prod-3006.service`
- WorkingDirectory ที่ deploy ผ่าน: `/mnt/nexus-copilot-mQTssj/release-appshield-41Z1YA3K/frontend`
- Node: `/home/saiuser/.nvm/versions/node/v20.20.2/bin/node`
- Drop-in: `/home/saiuser/.config/systemd/user/nexus-all-events-prod-3006.service.d/zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz-appshield-release.conf`
- Previous release: `/mnt/nexus-copilot-mQTssj/release-70dc9a4-SbfiVZFl/frontend`
- Rollback ต้องตรวจ config ปัจจุบันก่อนเอาออกเฉพาะ drop-in นี้ แล้ว daemon-reload/restart; ไม่ลบ drop-ins อื่น
- Candidate dependencies ถูกคัดลอกด้วย cp -aL ทำให้ .bin symlinks เป็นไฟล์ จึง build ผ่านด้วย entrypoint จริง:
  `node node_modules/next/dist/bin/next build --turbopack`
- ไม่ถือว่า npm run build ผ่านใน release copy นี้; direct build เท่านั้นที่ยืนยันผ่าน

### Agent003 และ transport

- NEXUS source project คือ `wazuh`, Manager `wazuh-wazuh.manager-1`
- อีก stack `luckyfive_wazuh-wazuh.manager-1` ไม่ใช่เป้าหมาย ห้ามแตะ
- Agent003 Linux Active; Agent004 Windows11 Disconnected ณ ตอนตรวจ และเป็นเครื่องเพื่อน
- Manager และ forwarder `edrxdr-wazuh-forwarder` อ่าน volume `wazuh_wazuh_logs` เดียวกัน
- ทดลอง FIM benign text file หนึ่งไฟล์ ผ่าน Rule554:
  - wazuh-alerts partition0 offset39150
  - morpheus-input partition0 offset70510
  - UID `73bc7ea89dfc122ba78371664333356cd9e76b1a1fe0aba78e9073d49ca75873`
- คืน config Agent003 และ service active แล้ว:
  SHA256 `40bd85de742735646a8d3226662cba24269fb7f33693e30d3ff3d44c1919babc`
- ไฟล์ทดสอบยังเก็บอยู่ ไม่ใช่ training baseline:
  `/home/saiuser/edrxdr-nvidia-lab-znmqaTGL/agent003-fim-test/transport-probe-e4c46419f41443229aa7b5b9c2e1eb96.txt`
- Evidence: `/home/saiuser/edrxdr-nvidia-lab-znmqaTGL/agent003-fim-probe-DmgSHeY1`

### Archive pilot / DFP prototype

- Pilot 20 นาทีเดิมคืน config สำเร็จ; ตัวรอบใหม่ตามสิทธิ์ 1 ชั่วโมงเก็บจริง 3300 วินาที (55 นาที) แล้ว RESTORED
- Guard 200MiB เป็น soft guard ไม่ใช่ hard quota; minimum free disk 10GiB
- Archive logging เป็นระดับ Manager จึงมี records agent อื่นด้วย แต่ feature adapter เลือก Agent003
- รอบ 1h: 897 records, Agent003822, archive windows12, repeated-line occurrences2 เก็บไว้ ไม่ deduplicate ทิ้ง
- Archive alias รายวันกับ archives.json อาจเป็น inode เดียวกัน ห้ามนับซ้ำ; มีการตรวจ prefix capture เก่าก่อนแยกรอบใหม่แล้ว
- Window 10:40 UTC มี422 records; 352 เป็น syscollector ไม่ใช่หลักฐาน attack
- ทั้ง12 windows ยัง window_complete=false; normal activity, representative baseline และ pilot-time membership ยังไม่ยืนยัน
- Archive features7 ตัว แยกจาก alert features10 ตัว ห้ามรวมเงียบ ๆ
- CPU adaptation คัดลอก NVIDIA dfencoder แล้วตัดเฉพาะ cudf import ใน package initializer; ไม่แก้ image เดิม ไม่ใช่การรับรอง upstream CPU support
- Fit prototype5epochs บน12windows; numeric featuresครบ7; binary/categorical/cyclical ว่าง
- Fresh-process reload score parity ผ่าน; separate adapter score parity ผ่าน
- การ score ใช้12windowsเดียวกับฝึก ไม่มี independent evaluation, quality metrics หรือ threshold
- สถานะ prototype: development only, live_deployed=false, production_ready=false, automated_response_allowed=false, bert_replaced=false
- GPU เคยมี context failure; CPU path เป็นแนวทางที่ทดสอบล่าสุด ไม่ reset/reboot/เปิด GPU เอง

## Paths และ hashes สำคัญบน VM

Lab root: `/home/saiuser/edrxdr-nvidia-lab-znmqaTGL`

| Artifact | Path ใต้ lab root |
|---|---|
| AppShield CPU extraction/inference | ransom-appshield-cpu-hF0TEper |
| AppShield results | ransom-appshield-cpu-hF0TEper/inference-6r9rq55n |
| Lab integration candidate | appshield-contract-IAGtwhkn |
| CPU adaptation | dfp-cpu-adapter-RMNy70Z4 |
| DFP experiment/model/private outputs | dfp-archive-cpu-prototype-uy_2ita1 |
| 1h capture + archive features | agent003-archive-1h-yfjyqu3h |
| Previous pilot capture | agent003-archive-pilot-9dlus1zj |
| Original alert development data — review pending | wazuh-dfp-development-_nfbkveu |

- 1h probe state: `/mnt/nexus-copilot-mQTssj/archive-baseline-1h-prepared-4xwu7fbm/approved-probe-ip_g09k5/state.json`
- CPU model file `model-private.pkl` SHA256:
  `ecacecb3128f9ac6987315e2a1861fb02ac873f9fc42ddc11798a9fc0c25157e`
- CPU source-manifest SHA256:
  `a32c517170fbf364581d65277ed9dc13ce497d1a1bd06b6b5a91c90e21183cc0`
- Prototype input SHA256:
  `cfa27c706f1d33c85628329f79cb23a764d032d5149f91f9388ccbd07fbd4cff`
- Adapter observations SHA256:
  `d1c8688ba89f09e32ea708e3eed2328bc4e3d2e9e953ffc4a03df024550c840b`
- 1h new capture SHA256:
  `cc57e01cd22f3dd60099836ea3606ea8c61b6f322f31cdc5a5808016f5f7298f`
- Scripts มี hash/input binding และ open('x') ห้าม rerun ทับ directory ที่จบแล้ว
- Pickle ใช้เฉพาะ artifact ที่สร้างเองและตรวจ hash ไม่โหลดโมเดลที่ไม่ทราบที่มา

## Commits ล่าสุดที่ยืนยัน

- `b426351` feat(dfp): record CPU archive prototype and verified inference adapter
- `6e1181a` feat(model-lab): accept AppShield CPU replay and record DFP checkpoint
- `44e8bdb` handoff รุ่นก่อนหน้า
- `70dc9a4` original Model Lab implementation

## ยังไม่เสร็จ / งานต่อ

1. Live BERT ยังไม่ถูกแทน และไม่ให้เปลี่ยนชื่อคะแนนเดิมให้เหมือนผลจากโมเดลใหม่
2. Freeze โมเดล prototype ปัจจุบันไว้ ออกแบบ prospective development validation ด้วยข้อมูลใหม่ ไม่จูน threshold จากผลประเมิน
3. ก่อนเรียกผลว่า live-ready ต้องมี input completeness/collection coverage, source identity, nuisance/syscollector/restart policy, model/feature version และการประเมินที่เหมาะสม
4. ข้อมูล alert Agent003 เก่า237windows ยัง protected membership pending ไม่ยกสถานะเป็นผ่านเพียงเพราะอนุมัติ training
5. ห้ามใช้ Duo weights กับ Wazuh features หรือเอา Wazuh/FIM counters แทน297 AppShield features
6. Ransomware live รอ compatible endpoint telemetry; Agent004 deferred ไม่ติดตั้ง collector บนเครื่องใหม่เอง
7. Prototype12 observations ยังอยู่ private artifacts ไม่ได้เพิ่มเข้า Model Lab (lab773รายการไม่รวม prototypeนี้)
8. ไม่มีการเริ่ม collection เพิ่มภายใต้ checkpoint นี้ ให้ตรวจ service/timer ปัจจุบันก่อนยืนยัน
9. ไม่เปิด automated response หรือขยายงาน Network

## ตรวจรับช่วงแบบอ่านอย่างเดียว

รันใน SSH:

```bash
cd /home/saiuser/EDRXDR-Morpheus || exit 1
date -Is
GIT_OPTIONAL_LOCKS=0 git branch --show-current
git --no-pager log -3 --oneline
GIT_OPTIONAL_LOCKS=0 git status --short
git --no-pager diff --check

systemctl --user show nexus-all-events-prod-3006.service \
  --no-pager -p ActiveState -p SubState -p WorkingDirectory -p MainPID
systemctl --user list-units --all --no-pager 'nexus*' 'edrxdr-archive*'
systemctl show wazuh-agent --no-pager -p ActiveState -p SubState

docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
cat training/HANDOFF-DFP-APPSHIELD-PROGRESS-20261103.md
cat training/experiments/archive-cpu-prototype-v1/README.md
cat training/experiments/archive-cpu-prototype-v1/receipt.json
```

ห้าม cat private config, client.keys, HMAC key, raw captures, memberships, datasets หรือ weights ส่งเข้าแชท

## WIP ที่ต้องรักษา

ล่าสุดยัง untracked:
- history/
- uid_lookup/
- training/DFP-RANSOMWARE-LAB-TRANSPORT-20261103.md
- training/HANDOFF-NEXUS-20261015.md
- training/HANDOFF-NEXUS-LLM-20261020.md
- training/HANDOFF-NEXUS-SYSTEMD-20261020T012409921855Z.md
- training/START-HERE-TEAM-20261101.md
- training/evidence/nexus-reconciliation-20261020/
- training/evidence/nexus-systemd-20261020T012409921855Z/

รายการนี้เป็น snapshot ต้องตรวจใหม่ ห้าม git add . / reset / clean เพื่อให้ตรง handoff

## วิธีส่ง repo

ถ้าเพื่อนเข้า VM เดียวกันได้ ให้ส่งข้อความรับช่วงและไฟล์นี้ ใช้ repo เดิมโดยประสานกันไม่แก้พร้อมกัน

ถ้าต้องย้าย source ออกจาก VM สามารถสร้าง Git bundle บน VM:
```bash
cd /home/saiuser/EDRXDR-Morpheus || exit 1
BUNDLE=/home/saiuser/edrxdr-handoff-b426351-$(date +%Y%m%dT%H%M%S).bundle
git bundle create "$BUNDLE" work/nexus-exact-ai-v1
git bundle verify "$BUNDLE"
sha256sum "$BUNDLE"
printf 'BUNDLE=%s\n' "$BUNDLE"
```

Bundle รวม committed history ของ branch ไม่รวม untracked/WIP, Docker images/volumes, private data, model weights, CPU adaptation นอก repo, dependencies, secrets และ runtime config จึงไม่ใช่ backup ระบบครบชุด เอกสารฉบับนี้สร้างบน Windows ยังไม่ได้เพิ่มลง VM/Git; ถ้าต้องการเก็บใน repo ให้ copy เข้า training/ ด้วยชื่อใหม่ ตรวจแล้ว commit เฉพาะไฟล์ โดย final HEAD จะเปลี่ยนจาก b426351

