# EDRXDR–Morpheus–NEXUS: เริ่มตรงนี้ — 2026-11-03

สถานะ: ผู้ใช้พักงาน ไม่มีคำสั่งให้เปิด collection/training/GPU อัตโนมัติจากเอกสารนี้
หลักฐาน: ผลคำสั่งที่ผู้ใช้ส่งจาก VM และ browser ที่ผู้จัดทำตรวจผ่าน SSH tunnel
ผู้จัดทำไม่ได้ SSH เข้ารันคำสั่งบน VM โดยตรง ต้องตรวจสถานะปัจจุบันใหม่ก่อนทำงาน

## 1. เพื่อนรับช่วง: อ่านส่วนนี้ก่อน

- VM: `saiuser@172.16.30.147`
- Repo: `/home/saiuser/EDRXDR-Morpheus`
- Branch ล่าสุดที่มีผลยืนยัน: `work/nexus-exact-ai-v1`
- HEAD ล่าสุดที่มีผลยืนยัน: `70dc9a4bcc5163425de9abe1789ab1aa2c8b66b3`
- หลัง commit เอกสารส่งต่อนี้ HEAD จะใหม่กว่า `70dc9a4` ซึ่งเป็น code baseline;
  ใช้ `git log` ตรวจ documentation commit ปัจจุบัน ไม่ย้อน checkout ไปทับงาน
- เป้าหมายผู้ใช้: ทำ DFP/Ransomware ตรวจจับสดและแทน BERT ในอนาคต
- **ยังไม่ได้แทน BERT และยังไม่มี DFP/Ransomware live detector ที่ผ่านการตรวจรับ**
- Model Lab ใช้งานบน NEXUS 3006 แล้ว แต่แสดงผล sample/replay เดิม ไม่ใช่ scoring สด
- งาน CPU ตอนหลังเป็น source/identity/feature/checkpoint candidates อยู่แยกนอก repo
- ห้ามเริ่ม GPU/training: ผู้ใช้อนุญาตเฉพาะ CPU ในรอบล่าสุดและพักงานไว้แล้ว

ไม่ต้องฝึก sample DFP ซ้ำ ไม่ใช้ Duo weights กับ Wazuh โดยเปลี่ยนชื่อฟีเจอร์
ไม่ใช้ FIM alerts แทน AppShield feature vectors และไม่แปลง output_0/1 เป็นชื่อ class เอง

## 2. สิ่งที่ deploy จริงแล้ว

Commit `70dc9a4` เพิ่ม read-only Model Lab 9 ไฟล์ (tests และ handoff รวมอยู่ด้วย)
API `/api/nexus/v1/lab` ใช้ History authentication และเปิดด้วย
`NEXUS_MODEL_LAB_ENABLED=1` อ่านเฉพาะ `edrxdr-ai-lab-v1` บน loopback OpenSearch
ไม่เปลี่ยน severity snapshot / legacy event_uid / การจับคู่ AI ของเดิม

| รายการ | หลักฐานล่าสุด |
|---|---|
| Service | `nexus-all-events-prod-3006.service` |
| Runtime หลังสลับ | `/mnt/nexus-copilot-mQTssj/release-70dc9a4-SbfiVZFl/frontend` |
| Runtime ก่อนสลับ (เก็บไว้) | `/home/saiuser/nexus-uid-candidate-wgpajvXL` |
| Override ที่เพิ่ม | `~/.config/systemd/user/nexus-all-events-prod-3006.service.d/zzzzzzzzzzzzzzzz-model-lab-70dc9a4.conf` |
| รายงานสลับ/rollback ส่วนตัว | `/mnt/nexus-copilot-mQTssj/release-70dc9a4-SbfiVZFl/switch-attempt-2b1a7tr_` |
| แผนสลับส่วนตัว | release root เดียวกัน: `switch-plan-private.json` |

Release build จาก commit ตรงผ่านด้วย Webpack; Turbopack เคยปฏิเสธ symlink node_modules
นอก filesystem root อย่าแก้ด้วยการ build ทับ runtime เดิม
Release node_modules ยังเชื่อมกับ dependencies ที่มีอยู่ ต้องรักษา symlink target ไว้

ผลสลับ 3006: `/api/wazuh`, `/api/events`, `/api/nexus/v1/snapshot` ผ่าน
History authentication/authorized History และ Lab authentication ผ่านใน switch helper
Lab all/DFP/Ransomware = 667/666/1; candidate browser ตรวจ pagination/filter/badge ผ่าน
**browser ของพอร์ตจริง 3006 หลังสลับยังไม่ได้ตรวจยืนยันโดย agent**
ผู้ใช้เปิด tunnel 13006 แล้ว แต่ผล API หลังสลับไม่เท่ากับ browser acceptance ครบทุกหน้า

Preview 3013 เคยเป็น transient unit หนึ่งชั่วโมงและเปลี่ยนเป็น
`nexus-model-lab-release-preview-3013.service` โดยคง deadline เดิม
ยังไม่มีผลยืนยันล่าสุดว่า preview หยุดแล้วหรือไม่ อย่าอ้างว่ายังทำงาน/หยุดแน่นอน

Rollback: ตรวจ original runtime, unit และ hash ของ override ก่อน ถอนเฉพาะ override
ที่เพิ่มในรอบนี้ แล้ว daemon-reload/restart เฉพาะ NEXUS 3006 และตรวจ API/auth อีกครั้ง
ห้ามลบ overrides อื่นหรือใช้คำสั่ง rollback โดยไม่ตรวจสถานะ/การเปลี่ยนแปลงภายหลัง
Rollback artifacts เก็บไว้ แต่ **ยังไม่ทดสอบ production rollback หลังสลับจริง**

## 3. Lab transport ที่ผ่านแล้ว (ไม่ใช่ live inference)

- Schema: `morpheus-lab-observation-1`; mode: `dataset_replay`
- Topic: `edrxdr-lab-ai-observations-v1` (1 partition, retention 7 วัน)
- Index: `edrxdr-ai-lab-v1` (1 shard, 0 replicas)
- Group: `edrxdr-lab-ai-lab-transport-YCoTV3ug`
- Offline import: DFP666 + Ransomware CPU summary1 = 667 observations
- NDJSON SHA256: `c72e369a699e48344c1f884bd618ac1e5f898bf23e8d318b6f837117a69fe0f4`
- ส่ง batch เดิมซ้ำหนึ่งรอบ: Kafka end/committed1334, lag0; indexยัง667 documents
- Retry ถูกขัดจังหวะที่1074 แล้ว resume260 จนครบ ไม่ reset offsets หรือ publish เพิ่ม
- หลัง retry IDs และ projected document contents ตรง667/667
- ไม่ใช้ผลนี้อ้าง model accuracy, real-world ransomware detection หรือ production readiness
- Topic retention อาจทำให้ offsets/ข้อมูลเก่าไม่อยู่แล้ว ต้องตรวจใหม่ก่อน resume/retry

Lab root: `/home/saiuser/edrxdr-nvidia-lab-znmqaTGL`
Integration root ใต้ lab: `integration-package-73C9gztG`
ผล import: `offline-import-VBMrTLYP/lab-observations.ndjson`
ไฟล์ repo ที่ผู้ใช้บันทึก: `training/DFP-RANSOMWARE-LAB-TRANSPORT-20261103.md`
ไฟล์นี้ยัง untracked ตามผลล่าสุด อย่า stage รวมโดยไม่ตรวจ

## 4. สถานะโมเดลและปัญหาที่ยังไม่ปิด

- DFP sample: `EDRXDR-LAB-DUO-generic_user:1`; sample inference666 rows
  ไม่ใช่โมเดล Wazuh-specific และยังไม่มีคุณภาพที่ยืนยันกับข้อมูลโครงการ
- Ransomware CPU: `ransomw-model-short-rf` เคย READY/ผ่านหนึ่ง training-CSV window
  99 features ×3 snapshots; ยังไม่ยืนยัน class mapping ของ artifact
- CPU Triton `edrxdr-ransom-cpu-YAHmi5uA` running ใน inventory ล่าสุด ไม่ได้ยืนยันว่าหยุด
- GPU Triton `edrxdr-ransom-copy-rebVrTzs-triton` exited ใน inventory ล่าสุด
- Host CUDA error999 ยังไม่ปิด root cause ห้าม reset GPU/reload driver/reboot เครื่องร่วมเอง
- Current inventory พบ Wazuh topic แต่ไม่พบชื่อ Duo/Azure/AppShield topics/collectors
  เป็นเพียงขอบเขต inventory ที่ตรวจ ไม่ใช่ข้อพิสูจน์ว่าไม่มี source ที่อื่นทั้งหมด
- BERT v4 experiments/validation/final holdout เดิมไม่ได้ audit ใหม่และห้ามใช้/เปลี่ยนเอง

## 5. ผลตรวจข้อมูล Wazuh (CPU-only)

เส้นทางเดิม: Wazuh → forwarder → `wazuh-alerts` → normalizer → `morpheus-input`
→ legacy BERT severity worker เมื่อได้รับสิทธิ์รัน → `morpheus-output` → indexer
การมี indexer/normalizer running ไม่ใช่หลักฐานว่า BERT worker กำลัง inference อยู่

ผล tail audit: 4911 records, 4902 canonical unique events ตาม contract alerts,
9 duplicates, 761 observed windows, 3 manager+agent entities, spanประมาณ281.66ชั่วโมง
เป็น bounded retained tail ไม่ใช่ประวัติครบหรือ representative normal baseline

| Agent | Observed windows | สถานะล่าสุดที่ตรวจ | ข้อจำกัด |
|---|---:|---|---|
| 000 | 5 | active/local | Manager-local; แยกจาก endpoint baseline |
| 003 | 237 | active; Linux; v4.14.1 | ชื่อตรงทะเบียน แต่ไม่พิสูจน์ physical-device continuity |
| 004 | 519 | disconnected; Windows; v4.14.8 | ประวัติมากกว่า แต่ยังไม่ตรวจ endpoint service จริง |

กติกาปริมาณ draft288windows/3calendar days ผ่านเพียง004 ไม่ใช่อนุมัติฝึก
ทุก cohort ยัง pending_review; identity reuse/exposure/template/protected-membership ยังไม่ปิด
Last keepalive003 ขยับจาก `2026-11-02T19:27:10Z` เป็น `19:37:10Z` ระหว่างสังเกต
004 คงที่ `2026-11-02T18:56:18Z` ในผลล่าสุด ไม่ได้ restart agent ใด
เครื่อง Windows ที่ agentเข้าถึงไม่พบ WazuhSvc; จึงยังไม่เชื่อมโยงว่าเป็น004

ตัวเก็บ offset ใหม่003 จำกัด600วินาที/1000records: ไม่พบ records ใหม่ ไม่สร้างแถวปลอม
Manager alerts.json mtime `2026-11-02T19:27:09Z` สอดคล้องกับไม่มี alertsเพิ่มช่วงนั้น
forwarderแชร์ log volume แบบRO และไม่พบ error markers ที่ตรวจใน100บรรทัด/20นาที
ข้อสรุปนี้ไม่ใช่การพิสูจน์ forwarding E2E ครบทุกกรณี; ไม่พบเหตุให้ restart โดยเดา
normalizer Wazuh lag0 และ source/normalized offsetsไม่เพิ่มใน120วินาทีที่ตรวจ

## 6. Archive probe: จบและคืนค่าแล้ว ห้ามเปิดต่อเอง

เดิม `logall=no`, `logall_json=no`, `jsonout_output=yes`; archives.jsonไม่พบ/อ่านไม่ได้
ผู้ใช้อธิบายและอนุญาต probeไม่เกิน20นาที โดยทราบว่าเก็บทุกagentของManager
เปิด/คืนค่าด้วย restartเฉพาะManager มี timerคืนค่าอิสระและstorage soft guard
ผลจริง: สังเกต1076วินาที; archive growth93916bytes; จบ `RESTORED`
`logall_json=no`, startup config original bytes restored, effective active config restored,
required manager processes ready; raw archive retained only onVM ไม่ลบหลักฐาน

| รายการ | ตำแหน่ง |
|---|---|
| Private preparation | `/mnt/nexus-copilot-mQTssj/archive-probe-prepared-qbbe917t` |
| Actual attempt/state | `approved-probe-_ywvwrji/state.json` ใต้ preparation |
| Config backups | `*-before.private.conf` ใต้ preparation ห้ามส่งเข้าchat/Git |
| Archive source | `/var/ossec/logs/archives/archives.json` ภายในManager |
| Source capture SHA256 | `11eb0e011721aa5267759bbaf88863f37ddf1e448e0b967d7c2bbf6e5cb420b1` |

ไฟล์หลังจบมี96145bytes/204lines: Agent000=33, Agent003=171
ช่วงเวลาAgent003ประมาณ984.076วินาที; field coverage: full_log171, data6,
source_user3,destination_user6,source_ip0,destination_ip0,FIMpath0,ruleobject2
ruleไม่มีไม่ใช่ benign label; ช่วงนี้มีManager restarts ไม่ใช่ baselineปกติที่รับรองแล้ว

### Identity ของ archives ต่างจาก alerts — สำคัญมาก

171recordsของ003มีเพียง17legacy canonical UID groups
13groupsมีpayloadต่างกัน; exact repeated line occurrencesมี3
**ห้าม dedup archives ด้วย legacy alert UID ห้ามลด171เหลือ17 และห้ามแก้ UID ของNEXUSเดิม**
Frozen-capture adapter ใช้ captureSHA + original line reference + raw-lineSHA + version
เก็บครบ171records/171recordIDs รวม repeated linesทั้ง3; ได้5feature windows
แยกschema/datasetจากalert-derived windows เดิม ไม่มีevent_uidหรือscoreปลอม
Identityนี้รับรองเฉพาะfrozen capture เดิม ไม่ใช่ global/live stream deduplication

## 7. Stream cursor candidate: ผ่านอะไร และยังไม่ผ่านอะไร

- Code: `/mnt/nexus-copilot-mQTssj/incoming/archive-stream-XG7u4bIr/nexus-archive-stream-candidate`
- 21 testsบนLinux/VM ผ่าน: append, explicit tail/no-backfill, restart, partial line,
  validation/transaction rollback, rotation/truncation detection และprivacy
- SQLite WAL/FULL บันทึกrecord ledger+cursorในtransactionเดียว ไม่เก็บraw text/user/IP
- ใช้durable stream/generation +byteoffset+raw-lineSHA ไม่ใช่legacy event_uid
- rotation/truncation/ตรวจพบprefix-anchor rewriteจะหยุด ไม่auto-resetหรือข้ามไฟล์
- prefix/anchor checksไม่พิสูจน์immutabilityทุกbyteย้อนหลัง ต้องออกแบบretentionต่อ
- Actual frozen capture integrationผ่าน:204recordsทั้งหมด,003=171,นอกเป้าหมาย33
  มีสถานะnot_scoredชัดเจน; restartเพิ่ม0records,IDsคงเดิม,transaction rollbackผ่าน
- sourcehashไม่เปลี่ยน ไม่chmod/restart/เปิดloggingจากintegration test
- **ยังไม่ได้ deploy live collector, ยังไม่ทดสอบ rotation จริง, ยังไม่เชื่อม feature
  extractor แบบdurable ACK และยังไม่มี model invocation**

## 8. หลักฐานส่วนตัวบนVM (ไม่ส่งข้อมูลออก)

ตำแหน่งต่อไปนี้อยู่ใต้ `/home/saiuser/edrxdr-nvidia-lab-znmqaTGL/`:

| โฟลเดอร์ | เนื้อหา/สถานะ |
|---|---|
| `wazuh-dfp-development-_nfbkveu` | alert-tail features/membership/protocol; private HMAC key |
| `wazuh-dfp-cohort-review-g81u5dmy` | cohort/distributions/ingestion metadata; pending training |
| `wazuh-dfp-identity-review-z1qvytxb` | mapping manager-local/003/004 แบบprivate |
| `agent003-baseline-observation-x5va4i5y` | 10-minute new-offset observation; zero new records |
| `archive-source-profile-z0kgh9jz` | schema/coverage summary of restored archive |
| `archive-identity-audit-6b4lc2_9` | payload-vs-UID collision audit |
| `archive-adapter-development-dot_t7b4` | preserved171 records/5windows; draft only |
| `archive-stream-integration-mcimwf1w` | actual capture SQLite checkpoints + rollback test |

แต่ละรอบมีsummary/hash sidecars เก็บไฟล์ต้นฉบับไว้ ห้ามย้าย/ลบเพื่อเริ่มใหม่
HMAC keys, private logs/configs,raw events,datasets,weights,secretsไม่เข้าchat/Git
มีcandidate/scriptsอื่นใน `/mnt/nexus-copilot-mQTssj/incoming/` ยังไม่ได้commitเป็น
backend production code อย่าถือว่าติดตั้งแล้วเพราะมีแพ็กเกจหรือtestsผ่าน

## 9. งานต่อไปตามลำดับ — หลังผู้ใช้กลับมาให้ทำต่อ

1. เริ่มตรวจสถานะจริงแบบread-onlyตามส่วน10; ไม่auto-runจากhandoff
2. ตรวจbrowserของproduction3006ให้ครบOverview/History/Model Lab และบันทึกผลdeploy
   ตรวจpreview3013/timersว่าเหลืออะไรโดยไม่หยุดunitที่ยังไม่ยืนยันownership
3. เชื่อมstream cursorกับarchive-specific feature extractorและdurable ACK boundary
   ในcandidateแยกก่อน ทดสอบfailure/retryและgeneration transition/retentionจริง
   ห้ามเอาreplay/capture IDไปอ้างเป็นstream identityที่พร้อมใช้โดยไม่ตรวจ
4. freeze source/feature protocolสำหรับWazuh-specific DFP: entity policy, event time,
   missingness, alert-only vs archives bias, template/source/time/endpoint leakage,
   protected membershipและtrain/dev split; ไม่อ่านfinal holdoutเดิม
5. เสนอช่วงเก็บbaselineที่เป็นตัวแทนกิจกรรมจริง ระยะเวลา/disk/privacy/rollbackชัดเจน
   **ขออนุญาตใหม่ก่อนเปิดarchivesหรือcollectorระยะยาว** รอบ20นาทีก่อนจบแล้ว
6. ขอเข้าถึงปลายทางWindowsของ004ก่อนตรวจservice/config/network ห้ามเดาว่าเป็นเครื่องผู้ใช้
7. Ransomware: ยืนยันclass mappingและtelemetry/feature orderจริง; FIMไม่ใช่AppShield
8. พิจารณาฝึก/ทดสอบโมเดลใหม่เฉพาะเมื่อข้อมูล/protocol/validationผ่านและได้รับอนุญาต
   GPUต้องมีช่วงจองใหม่ ตรวจguard/LuckyFive และแก้CUDA999ผ่านผู้ดูแลก่อน
9. ทดสอบshadow/end-to-end/qualityกับข้อมูลสดก่อนเสนอแทนBERT พร้อมrollback
   ไม่ปิดlegacyworkerเพียงเพราะintake/testsผ่าน

## 10. คำสั่งรับช่วงเริ่มต้น — VM Ubuntu เท่านั้น

```bash
cd /home/saiuser/EDRXDR-Morpheus || exit 1
date -Is
git branch --show-current
git log -3 --oneline
git status --short
git --no-pager diff --check
systemctl --user show nexus-all-events-prod-3006.service \
  --no-pager -p ActiveState -p SubState -p WorkingDirectory -p MainPID
systemctl --user list-units --all --no-pager 'nexus*' 'edrxdr-archive*'
docker ps --format 'table {{.Names}}\t{{.Status}}'
```

อย่ารันคำสั่งPowerShellในUbuntuหรือคัดลอกprompt/outputกลับเข้าshell
ไม่แสดงenvironment values,unit-private files,raw logsหรือcredentialsในchat
ถ้าSSHจากAIไม่ได้ ให้ผู้ใช้รันคำสั่งสั้นๆและส่งเฉพาะmetadata/aggregate

## 11. ข้อห้ามที่ต้องรักษา

- ไม่reset/clean/checkoutทับ ไม่git add . และไม่stage untrackedทั้งหมด
- ไม่buildทับactive .next ไม่ใช้sourcecheckoutแทนruntimeโดยเดา
- ไม่แตะLuckyFive/shared stack/driver/network/BlueField/rshimหรือautomated response
- ไม่เปิดGPU/trainingจากข้อความส่งต่อ ไม่ถือว่าbookingเก่ายังใช้ได้
- ไม่เปิดlogall_jsonต่อเพราะมีแผนเก่า; flagล่าสุดคืนnoแล้ว
- ไม่ยกsample/modelREADY/mockACK/21testsเป็นlive detectorหรือquality acceptance
- รักษาBERT/datasets/validation/quarantine/reserve/holdoutและหลักฐานทั้งหมด

## 12. Prompt สั้นให้เพื่อนส่ง AI

รับช่วงEDRXDR–Morpheus–NEXUSบนVM saiuser@172.16.30.147 repo
/home/saiuser/EDRXDR-Morpheus อ่าน training/HANDOFF-NEXUS-LIVE-NEXT-20261103.md
ก่อน เริ่มGit/runtime read-only HEADล่าสุดที่ยืนยัน70dc9a4 ต้องตรวจใหม่
Model Lab deploy3006แล้ว แต่เป็นsample/replay ไม่ใช่DFP/Ransomwareสดและยังไม่แทนBERT
Archive probeจบและคืนlogall_json=noแล้ว;003Active/004Disconnectedตามsnapshotล่าสุด
archives171recordsของ003มีlegacyUIDเพียง17groups ห้ามdedupด้วยUIDเดิม
adapterเก็บ171recordsครบ;streamcursorผ่าน21testsและactual frozen capture204records
แต่ยังไม่deploycollector/ไม่ทดสอบrotationจริง/ไม่เชื่อมfeatureextractorแบบdurableACK
ผู้ใช้พักงาน ไม่มีGPU/trainingหรือเปิดloggingอัตโนมัติจากhandoff ต้องรับขอบเขตใหม่ก่อน
รักษาWIP/ข้อมูล/โมเดล/หลักฐานและprotectedholdoutทั้งหมด ไม่reset/clean

## 13. เอกสารประกอบ

- `training/HANDOFF-EDRXDR-DFP-RANSOMWARE-20261103.md` อาจยังอยู่เฉพาะไฟล์แนบเดิม
  ต้องเช็กว่ามีในrepoก่อนอ่าน ไม่ถือว่าcommitแล้ว
- `training/HANDOFF-NEXUS-MODEL-LAB-20261103.md` เป็นหลักฐานก่อนdeploy
  ข้อความNOT_DEPLOYEDในเอกสารนั้นเป็นhistorical state ไม่ใช่สถานะหลังสลับ
- `training/DFP-RANSOMWARE-LAB-TRANSPORT-20261103.md` ตามผู้ใช้สร้าง;ยังuntrackedล่าสุด
- Wazuh/NVIDIA referencesอธิบายproduct contract ไม่ใช่หลักฐานสถานะVMปัจจุบัน:
  https://documentation.wazuh.com/current/user-manual/reference/tools/agent-control.html
  https://documentation.wazuh.com/current/user-manual/capabilities/command-monitoring/command-output-analysis.html
  https://docs.nvidia.com/morpheus/developer_guide/guides/5_digital_fingerprinting.html
  https://docs.nvidia.com/morpheus/examples/ransomware_detection/README.html
