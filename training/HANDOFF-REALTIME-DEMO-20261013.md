<!-- severity-flow-verified-20261013 -->
> อัปเดต13ต.ค.: ทดสอบ Windows Agent004 → Kafka → Morpheus Severity GPU → OpenSearch → Dashboard แล้วใน bounded microbatch run `d20261013t164314-c1b4d787`; counts3/3/3 ตรวจต้นทางWindowsหนึ่งรายการด้วยUID/hash ผ่าน และworker_stoppedแล้ว รายงานexitcodeดูเอกสารใหม่ ห้ามอ้างexit0โดยไม่มีหลักฐาน สถานะก่อนหน้านี้ที่ระบุว่ายังไม่ได้เดโมครบสายเป็นประวัติ อ่าน [ส่งต่อรอบล่าสุด](HANDOFF-SEVERITY-FLOW-20261013.md) ก่อนทำงานต่อ

# EDR/XDR — ส่งต่องานเตรียมเดโม pipeline ต่อเนื่อง

อัปเดตจากหลักฐานในแชทถึงวันที่ 13 ตุลาคม 2026 (เวลาไทย) สำหรับนำเสนอความคืบหน้าวันที่ 16 ตุลาคม 2026

## 1. เป้าหมายล่าสุดที่ตกลง

ต้องการเห็นเหตุการณ์ใหม่ไหลเข้า ผ่านโมเดลใน Morpheus จริง แล้วผลใหม่ขึ้น Dashboard อัตโนมัติ โดยตามรอยเหตุการณ์เดียวกันได้ตั้งแต่ต้นทางถึงผลลัพธ์ ไม่ใช่แค่เปิดผลเก่า ไม่ใช่แสดงว่าบริการ Online แล้วถือว่า pipeline ไหล

เส้นทางเป้าหมายรอบแรก:

Wazuh event ใหม่ → Kafka → Shadow capture → Morpheus GPU pipeline (preprocess + Severity inference) → Kafka output → Indexer → OpenSearch → Dashboard อัปเดตอัตโนมัติ

- ใช้โมเดลเดิม ไม่ต้องเริ่ม training ใหม่เพื่อทำเดโมนี้
- ให้ Severity เดินครบสายก่อน Behavioral แสดงตาม coverage จริง
- BlueField live เป็นอีกเส้นทาง ยังไม่ใช่เงื่อนไขของเดโม Endpoint รอบแรก
- หากทำเป็น batch สั้น ให้เรียก near real time พร้อม latency ที่วัดได้ ไม่อ้าง hard real time
- ไม่ต้องคืน container เก่า `edrxdr-morpheus` หากใช้ worker แยกที่รัน Morpheus pipeline จริงได้ แต่ต้องแสดงชื่อ/หลักฐานของ worker ที่ใช้งานจริง
- Automated response ยังคงปิด

สถานะ ณ ส่งต่อ: เพิ่งตกลงเป้าหมายนี้และอ่านโค้ดเส้นทาง inference แล้ว ยังไม่ได้เขียนหรือติดตั้ง worker ต่อเนื่อง ยังไม่ได้ทดสอบเดโมเหตุการณ์ใหม่ครบสาย และยังไม่ได้รับข้อมูลช่วงจอง GPU รอบถัดไป

## 2. เครื่องและ repo

- VM: `saiuser@172.16.30.147` / `oa-hgx-h100-bu-02`
- Repo: `/home/saiuser/EDRXDR-Morpheus`
- Frontend: `/home/saiuser/EDRXDR-Morpheus/frontend`
- Branch ที่ยืนยันล่าสุด: `work/bluefield-shadow-quarantine`
- Commit ที่ยืนยันล่าสุด: `cb514aa` — Bind fixture source verification to canonical operator approval and audit
- มีการติดตั้ง/แก้ไฟล์หลัง commit นี้หลายรายการ ห้ามถือว่า working tree สะอาดหรือเอกสารใหม่เข้า Git แล้ว ต้องอ่าน `git status` ปัจจุบันก่อนทำต่อ
- Local Windows workspace: `C:\Users\bagel\.codex\.chatgpt-projects\g-p-6aaba3627c608191b6e5927d3d4b4c43`
- `sources/` ใน Windows workspace เป็น reference ที่ sync มา ห้ามแก้ ย้าย หรือลบ
- การทำงานที่ผ่านมา: แก้/ทดสอบสำเนา local แล้วส่งแพ็กให้ผู้ใช้ scp และติดตั้งบน VM ไม่มีการเชื่อม VM โดยตรงจาก agent

## 3. งานที่เสร็จแล้วและหลักฐาน

### Endpoint Shadow

- Shadow contracts บน VM ผ่าน 23 tests ตาม output ที่ผู้ใช้ส่ง
- Behavioral ประมวลผล 32 records และ index เข้า `shadow-behavioral-v1` 32 records
- Severity ประมวลผล 32 records และ index เข้า `shadow-severity-v1` 32 records
- Join check PASS: occurrence ตรง 32, raw hash ตรง 32, conflicts 0, unmatched 0
- API `/api/shadow/events` ที่ผู้ใช้ตรวจรายงาน severity=32, behavioral=32, matched=32, candidates=13, ae_scored=0, novelty=1
- Candidates ทั้ง 13 เป็น rule `19008` และยังไม่ใช่ false positive ที่ตรวจยืนยันโดยผู้ประเมิน
- Behavioral: limited_history 31, novel_cohort 1; ไม่มี AE score ในชุดนี้ ไม่ใช่หลักฐานว่าปลอดภัย
- Consumer groups Shadow สี่กลุ่มเคยตรวจได้ offset 32/32, lag 0 และไม่มี active members หลังจบ batch นี่เป็นผลในเวลาที่ตรวจ ไม่ใช่สถานะปัจจุบัน
- รายงาน join ใน container: `/shadow-state/join-check-20261010T192035112516Z.json`
- joined_evidence_sha256: `41ea206d7f5c61df958634bfab041cc5bf1b15b51f4a0759c43f3b0cd21d9a2e`
- ขอบเขต PASS คือ correspondence/output contracts ไม่ใช่ model accuracy หรือการรับรองบริการต่อเนื่อง

### หลักฐานว่า Severity ใช้ Morpheus

อ่านจากสำเนา `operator-review-cb514aa/shadow/scoring.py` และ `handoff-audit-20261011/source/replay/morpheus_replay_engine.py` บน Windows:

- `severity()` เรียก `morpheus_replay_engine.score_texts()`
- Engine สร้าง `LinearPipeline` และกำหนด `ExecutionMode.GPU`
- Stages: InMemorySourceStage → DeserializeStage → PreprocessNLPStage → BertSpecialTokensStage → CheckTokensStage → ContextSeverityInferenceStage → InMemorySinkStage
- มี token/mask parity และ input/output alignment checks
- เป็น finite batch และสร้าง pipeline ภายใน `score_texts()` จึงยังไม่ใช่ long-running worker
- ต้องเทียบ source/hash กับ VM ล่าสุดก่อนดัดแปลง ไม่ถือว่าสำเนาเก่าเป็นโค้ดปัจจุบันทั้งหมด
- Behavioral ที่อ่านใน `scoring.py` เป็น CPU runtime แยก ห้ามกล่าวว่าทั้งสองโมเดลรันใน Morpheus GPU โดยยังไม่มีหลักฐาน

### BlueField ทดลองแยก

- Monitor: 9 synthetic C tests ผ่าน, DOCA 3.2.3005 build ผ่าน ตามหลักฐาน operator ที่บันทึกใน RESULTS
- Sampling เดิมได้ 6 records / 2 interfaces / 3 rounds; interfaces down, carrier เป็น null และอ่าน counters ได้ค่า 0
- Offline normalizer: 14 tests ผ่าน; carrier null ทั้ง 6, first-sample delta null 2, computed delta zero 4
- Kafka transport run PASS: archived 6 records ส่งผ่าน isolated topic แล้ว bytes/hash ตรง และ normalized output ตรง archived evidence
- Kafka report: `experiments/bluefield-kafka-runs/20261012T141233Z-beaccd98dc/report.json`
- Runner version: `20261012-stdin-fix-1`; ผู้ใช้ copy runner เข้า evidence directory แล้ว
- Kafka topic: `review-bluefield-20261012t141233z-beaccd98dc`; retention.ms=86400000 เฉพาะข้อมูล ไม่ได้ลบตัว topic อัตโนมัติ
- มี run ก่อนหน้าที่ FAIL: `experiments/bluefield-kafka-runs/20261012T140620Z-f8769c8cdb/` เก็บเป็นประวัติ ห้ามนำไปแทน run PASS
- OpenSearch persistence run PASS: 6 records, `_source` ตรง, carrier_exists=0, delta_exists=4, delta_zero=4, rx_zero=6
- OpenSearch report: `experiments/bluefield-opensearch-runs/20261012T141653Z-6396a0d3/report.json`
- Index: `review-bluefield-20261012t141653z-6396a0d3` คงไว้ตรวจ ไม่มีการลบอัตโนมัติ
- ทั้งสอง run นี้คือ archived data transport/persistence ไม่ใช่การทดสอบ live sampling หรือ continuous consumer

### Operator และ sink

- มีงาน operator binding/approval/audit ที่ branch ล่าสุด; อ่าน `training/HANDOFF-OPERATOR-20261013.md` และเอกสาร `shadow/BLUEFIELD_OPERATOR_*.md` ก่อนทำต่อ
- Step8 ติดตั้ง `shadow/bluefield_operator_sink.py`, tests และเอกสาร sink แล้ว
- VM validation ผ่าน 123 tests
- Evidence: `training/evidence/bluefield-operator-step8-20261013T072419032202Z/validation.txt`
- Preflight evidence: `training/evidence/bluefield-sink-preflight-mRy7AERJ/`
- ผล: status=deployment_checked, quarantine_indices=[], replay_authorized=false, production_ready=false, exit_code=0
- บันทึกผลลงเอกสารแล้ว แต่ไม่ได้หมายถึงได้รับอนุญาต replay หรือ sink production integration ผ่านแล้ว

## 4. Dashboard ล่าสุด

### โครงสร้างที่ทำแล้ว

- `/` หน้าภาพรวมข้อมูลจริงจาก API
- `/shadow` รายละเอียดผล Endpoint และ occurrence/hash
- `/bluefield` แยก BlueField Shadow กับ historical evidence
- `/replay` ผล replay เดิม
- `/details#quality` รายงานคุณภาพโมเดลเดิม
- `/details#live` สถานะบริการเดิม
- ตัวเลขที่อ่านไม่ได้แสดง unavailable/— ไม่เติมเลขแทน
- หน้า overview อ่านเมื่อเข้าและกด refresh ยังไม่มี auto polling
- Theme ล่าสุดแนว Splunk-inspired: เมนูซ้ายเข้ม แผงพื้นสว่าง ตารางกระชับ ตัวเลือก All / Endpoint / BlueField
- ตัวกรองนี้เลือกชนิดแหล่งข้อมูล ไม่ใช่ time range หรือการ query ประวัติทั้งหมด
- API เดิมมีขอบเขตจำนวนข้อมูล ต้องตรวจเงื่อนไข incomplete/limit ก่อนเพิ่มปริมาณ ไม่ควรแค่เพิ่ม limit เพื่อซ่อนปัญหา

### แพ็กและผลติดตั้ง

- แพ็กก่อนหน้า: `edrxdr-dashboard-demo-update-20261013.tar.gz`
- Theme ล่าสุด: `edrxdr-dashboard-console-20261013.tar.gz`
- ติดตั้ง console สำเร็จบน VM; backup: `/home/saiuser/EDRXDR-Archive/frontend-backups/dashboard-before-20261013T081231977457Z.tar.gz`
- Overview tests, TypeScript, production build ผ่านบน VM ตาม output ล่าสุด
- จากนั้น `git diff --check` พบ CR/trailing whitespace ใน `frontend/src/app/globals.css:48` ทำให้ shell หยุดก่อนคำสั่งเปิดเว็บ
- ส่งคำสั่งแก้ newline/whitespace แล้ว แต่ยังไม่มี output ยืนยันว่าผู้ใช้รันสำเร็จหรือเปิด console รุ่นล่าสุดแล้ว
- Full regression หลัง console update ยังไม่มีผลยืนยันในแชท; อย่าเขียนว่าทุกชุดผ่านล่าสุด
- ทดสอบ local: overview, Shadow 20, BlueField Shadow 10, history 7 เคยผ่านในรอบ demo update; build และ overview ผ่านอีกครั้งในรอบ theme
- Local ไม่ได้รัน full regression เพราะขาด real quality/parity reports ใน source archive
- คู่มือเดโม: `frontend/DEMO-20261016.md` มีลำดับพูด 4 นาที แต่ต้องปรับให้ตรงเป้าหมาย continuous pipeline ใหม่เมื่อทำเสร็จ
- `frontend/run_demo_dashboard.sh` ตั้ง SHADOW_OPENSEARCH_URL, REPLAY_OPENSEARCH_URL และ BLUEFIELD_HISTORY_OPENSEARCH_URL จาก IP ของ replay OpenSearch ปัจจุบัน แล้วเปิด Next.js port 3000
- ยังเป็น foreground process ไม่ใช่ service ที่จัดการการเปิด/ปิดอัตโนมัติ

## 5. สถานะบริการที่ยืนยันล่าสุด

### Morpheus เดิม

- `edrxdr-morpheus`: exited, exit=1
- started=2026-10-01T20:31:54.429665099Z
- finished=2026-10-01T20:32:56.599667608Z
- image=`nvcr.io/nvidia/morpheus/morpheus:25.06-runtime`
- runtime=runc; DeviceRequests ขอ GPU ทุกตัว (Count=-1, capabilities gpu)
- Log: cuDF/RMM `getDeviceCount()` ล้มด้วย `cudaErrorSystemNotReady: system not yet initialized`
- เป็นความล้มเหลวของรอบเก่า ไม่ใช่การพิสูจน์ว่าปัญหายังเกิดวันที่ 13 และ runtime=runc เพียงอย่างเดียวไม่ใช่หลักฐานว่าไม่ได้ส่ง GPU ให้ container
- ไม่ต้องรีสตาร์ต live pipeline เก่าเพื่อทำช่อง status ให้เขียว

### GPU และ Fabric

- nvidia-smi วันที่ 13 ตรวจพบ H100 80GB, driver 580.178.04, แสดง CUDA Version 13.0, VRAM used 0 MiB, util 0%, ไม่มี process ขณะตรวจ
- Fabric State/Status และ Health เป็น N/A
- อ่าน nvidia-smi ได้ไม่เท่ากับยืนยัน CUDA inference ปัจจุบันผ่าน
- Dashboard ช่อง H100 Fabric ตรวจ Fabric ไม่ใช่ GPU availability ทั้งหมด จึง Unknown ตามโค้ด
- DOCA Unknown ถ้าไม่ตั้ง DOCA_SYSTEMD_SERVICE; ไม่ใช่การพิสูจน์ว่า SDK ไม่ได้ติดตั้ง

### BlueField publisher

- `edrxdr-bluefield.service`: inactive/dead/disabled ยืนยันแล้ว
- หยุด/disable เพื่อควบคุม restart loop; NRestarts ก่อนหยุด 73095
- Unit: `/etc/systemd/system/edrxdr-bluefield.service`
- อ้าง binary `/home/saiuser/EDRXDR-Morpheus/build/bluefield-agent/bluefield_monitor` ที่รายงานว่าหาย
- ExecStart pipe ไป kafka-console-producer topic `bluefield-events` ใน `edrxdr-kafka`
- ยังไม่ได้ซ่อมหรือ deploy experimental binary ไปแทน ห้ามเปิด service เพียงเพื่อให้มีข้อมูลบน Dashboard

Container อื่นที่เคยทำงาน: replay OpenSearch/Kafka/normalizer, edrxdr normalizer/wazuh-forwarder/indexer/Kafka/OpenSearch และ Wazuh manager/indexer/dashboard ต้องตรวจ `docker ps -a` ใหม่ เพราะรายการนั้นไม่ใช่ snapshot ตอนส่งต่อ

## 6. Dataset/model/state ใน Docker volumes

- Shadow compose สำเนาที่ตรวจ mount volume `edrxdr-model-output` ไป `/models` แบบ read-only
- Severity checkpoint: `/models/wazuh-severity-context-v2-balanced-20261008T190719Z-1398863`
- Parity report: `/models/morpheus-raw-offline-check-20261008T203523Z-1803526/parity_report.json`
- Scripts: repo training → `/scripts`; repo replay → `/replay`; shadow → `/shadow`
- Shadow state ใช้ compose volume `shadow-state`; ชื่อที่เคยสำรวจคือ `edrxdr-shadow_shadow-state`
- Dataset volume ที่เคยสำรวจคือ `edrxdr-dataset` แต่ subdirectory/dataset ที่ใช้งานล่าสุดต้องอ่าน compose/training report และ `docker volume inspect` ก่อน ห้ามเดาชื่อหรือย้ายข้อมูล
- Model เคยมี permission issue กับ weights root:root mode600 และ cache path; รอบ Severity ภายหลังรันผ่านได้ โดยใช้ HOME/XDG/CUPY/CUDA cache ใต้ /tmp ขณะรัน
- อย่าใช้ Docker prune/ลบ volumes เป็นส่วนหนึ่งของงานเดโม

## 7. การจัดไฟล์และไฟล์นอก repo

จัดระเบียบเมื่อวันที่ 12 โดยย้าย 7 รายการ ไม่ลบ และไม่ได้คืนพื้นที่:

- backup tar 3 รายการ → backups
- `edrxdr-dashboard-updated.zip` → packages
- dashboard-review 2 directories → dashboard-review
- `EDRXDR-HANDOFF` → handoff

ตำแหน่ง: `/home/saiuser/EDRXDR-Archive/20261012T135349958660Z/`
มี `manifest.json` และ copy `organize_edrxdr_20261012.py` (8822 bytes) เก็บแล้ว

ไม่ต้อง restore เพื่อเริ่มงานต่อ Restore มีไว้เมื่อต้องย้อนการจัดโฟลเดอร์เท่านั้น:

```bash
python3 ~/EDRXDR-Archive/20261012T135349958660Z/organize_edrxdr_20261012.py \
  --restore ~/EDRXDR-Archive/20261012T135349958660Z/manifest.json
```

เอกสาร backup อื่นอยู่ `~/EDRXDR-Archive/documentation-backups/`; frontend backup อยู่ `~/EDRXDR-Archive/frontend-backups/`
`/tmp/` มี installers, patch archives, audit/test runners เป็นไฟล์ส่งผ่าน/ช่วยติดตั้ง ไม่ควรพึ่งว่าคงอยู่ถาวร เก็บ runner/evidence ที่ต้องทำซ้ำใน repo หรือ archive ที่เหมาะสม
BlueField evidence เดิมนอก repo เช่น `~/edrxdr-bluefield-nullcheck.Bn44DZ` และ `~/edrxdr-bluefield-normalize.udX6v2` ยังไม่ควรลบจนตรวจสำเนา evidence ครบ
ไม่ย้าย main repo, personal repo, build path, virtualenv หรือ Docker volumes โดยดูจากชื่อไฟล์อย่างเดียว

## 8. งานค้างลำดับเร่งด่วน — continuous demo

### A. ตรวจ snapshot ปัจจุบันก่อนแก้

เก็บ Git status/commit และ source ล่าสุดของ shadow, replay engine, inference/preprocess adapters, frontend และ compose ที่ใช้จริง เก็บเฉพาะ source ไม่ส่ง .env, credentials, raw datasets หรือ weights เข้าแชท
ตรวจเวลา/สิทธิ์การใช้ H100 รอบใหม่ก่อนรัน GPU

### B. ออกแบบและทำ worker ต่อเนื่อง

- ตรวจ loop/limit/timeout ใน `shadow/pilot.py`, runtime และ compose ไม่สมมุติว่าถอด --limit แล้วกลายเป็น daemon
- Shadow compose เดิมมี outer timeout 600s และ restart=no ต้องออกแบบ lifecycle/เวลาหยุดให้ชัด
- เลือก bounded microbatch ก่อนหากเหมาะสม; ระบุ latency จริงและค่าใช้จ่ายจาก model/pipeline initialization
- พิจารณาโหลดโมเดลค้างเมื่อปลอดภัยและจำเป็น ห้ามลัด parity/source hash validation
- รักษา ordering/occurrence/raw hash และ commit หลัง output acknowledgement; restart ต้องไม่ทำข้อมูลหาย
- ระบุ start boundary และ backlog จริง ไม่เริ่มอ่านย้อนหลังจำนวนมากโดยไม่ตั้งใจ และไม่ reset กลุ่มเดิมเพื่อทำเดโม
- ตรวจว่าการเปลี่ยน engine/adapter กระทบ source-lock/parity evidence ใดบ้าง ทดสอบใหม่ตาม contract ไม่แก้ hash ให้ผ่านเฉย ๆ
- ใช้ topic/group/index ที่แยกและ schema ที่รักษาขอบเขต Shadow
- เพิ่ม run/model/source identifiers และ timestamps ตามความหมายจริง พร้อม error/shutdown logs

### C. Dashboard แสดงการไหล

- เพิ่ม polling ที่ควบคุมได้ มี stop/cleanup และไม่ยิง request ซ้อน
- แสดงเวลาข้อมูลล่าสุด แยก source event time, receive/process/index/read time; หากขาด timestamp ให้ unknown ไม่สร้างย้อนหลัง
- แสดง per-stage counters / Kafka lag / failure และชื่อ worker จริง
- ตาม event เดียวด้วย occurrence/UID/hash ถึงผล model ได้
- รองรับขอบเขตค้นหา/pagination/window ของข้อมูลที่โตต่อเนื่อง โดยไม่ทำให้ incomplete search ถูกนับเป็นครบ
- แยก GPU detected, Fabric N/A, Morpheus live container และ demo worker; แก้ชื่อ BlueField เป็น publisher
- เมื่อ backend หาย ต้องแสดง stale/unavailable ไม่คงเลขเก่าเหมือนข้อมูลสด

### D. ทดสอบบน VM ในเวลาจอง

- GPU/CUDA smoke check ใน image/config ที่จะใช้ โดยไม่แตะ pipeline เก่าก่อนจำเป็น
- Inject/generate เหตุการณ์ทดสอบที่ได้รับอนุญาตและตามรอยได้จาก Wazuh
- ยืนยันเหตุการณ์เกิดใหม่หลังเริ่ม demo ผ่าน model ใน Morpheus แล้วขึ้นเว็บโดยไม่สั่ง score/index ทีละรอบ
- เก็บ model/stage logs, source/result identity, timestamps และ latency ที่คำนวณได้จริง
- ทดสอบ worker stop/restart, delivery/index failure และ resume ตามขอบเขต ไม่ทำ fault injection ใส่บริการร่วมโดยไม่แยก
- ตรวจว่าตัวเลขเว็บตรง API และไม่มีการกล่าวว่าไม่มี AE score = safe
- กำหนดคำสั่งหยุดเฉพาะ worker เดโมและเวลาหยุด GPU ให้ทัน reservation

เกณฑ์รับงาน: เห็น event ใหม่อย่างน้อยหนึ่งรายการเดินครบสายอัตโนมัติ มีหลักฐาน inference จริงและวัดเวลาถึงเว็บได้; ซ้อมหลายรายการเพื่อให้เห็นว่าทำซ้ำได้ ไม่อ้างว่ารองรับ production load

### E. ปิดงานนำเสนอ

- Full relevant regression + build บน VM เก็บ logs
- Update README/LATEST_STATUS/HANDOFF และ DEMO guide ให้ตรงกับสิ่งที่ทำจริง
- สไลด์ 3–5 นาที: problem/architecture → event ใหม่ → Morpheus score → dashboard → measured latency → limitations/next work
- บันทึกวิดีโอ/ภาพพร้อมวันที่ไว้เป็น fallback; ถ้าใช้ replay ให้ติดป้าย replay ไม่อ้าง live
- ตรวจ diff/ไฟล์ secrets ก่อนเลือก commit; remote push ยังไม่มีหลักฐานในรอบล่าสุด

## 9. งานที่ยังไม่ควรอ้างว่าเสร็จ

- Continuous end-to-end live pipeline และ continuous model inference
- CUDA ของ live container เดิมได้รับการแก้แล้ว
- BlueField live publisher / active traffic monitoring / packet inspection
- Operator replay authorization หรือ production sink readiness
- Behavioral AE coverage เพียงพอ หรือโมเดลยืนยันภัยได้แม่นยำจาก 32 events
- Accuracy ของ model จาก matched count; false positives 13 ยืนยันแล้ว
- การทดสอบ load/latency/soak/recovery ครบในระบบรวม
- ระบบ production access control, authentication, retention, backup restore และ alerting พร้อมใช้จริง
- เอกสารล่าสุด/patch ทั้งหมด commit หรือ push แล้ว

## 10. คำสั่งเริ่มรับช่วงต่อ (อ่านสถานะ ไม่เริ่ม GPU)

```bash
cd ~/EDRXDR-Morpheus || exit 1
date -Is
git branch --show-current
git log -5 --oneline
git status --short
git diff --stat
git diff --check
docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
systemctl show edrxdr-bluefield.service --no-pager \
  -p ActiveState -p SubState -p UnitFileState
nvidia-smi
ss -ltnp
```

อ่านเอกสาร:

```bash
cd ~/EDRXDR-Morpheus || exit 1
cat training/LATEST_STATUS.md
cat training/HANDOFF-OPERATOR-20261013.md
cat frontend/DEMO-20261016.md
cat shadow/compose.yml
sed -n '1,220p' replay/morpheus_replay_engine.py
```

ถ้า CSS ยังพบ ^M/trailing whitespace ให้แก้เฉพาะรูปแบบบรรทัด:

```bash
cd ~/EDRXDR-Morpheus || exit 1
python3 - <<'PY'
from pathlib import Path
p = Path('frontend/src/app/globals.css')
text = p.read_text(encoding='utf-8')
with p.open('w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(line.rstrip() for line in text.splitlines()) + '\n')
PY
git diff --check
```

เปิดหน้าแสดงผลเดิมเมื่อ port 3000 ว่างและ build ล่าสุดพร้อมแล้ว (ไม่เริ่ม model worker):

```bash
cd ~/EDRXDR-Morpheus/frontend
bash run_demo_dashboard.sh
```

ตรวจ API จาก terminal อีกอัน:

```bash
curl -fsS --max-time 20 http://127.0.0.1:3000/api/shadow/events | python3 -m json.tool
curl -fsS --max-time 20 http://127.0.0.1:3000/api/shadow/bluefield | python3 -m json.tool
```

ก่อนจบ reservation: จากหลักฐานล่าสุดไม่มี GPU process ตอนที่ตรวจ แต่ต้องรัน nvidia-smi ใหม่; หากมี worker เดโมของเราให้หยุดเฉพาะตัวนั้น ห้าม kill process ผู้อื่นหรือ docker compose down ทั้ง stack ร่วม การเปิด Dashboard อย่างเดียวไม่ใช่การรัน inference

## 11. ข้อความส่งให้คน/แชทที่รับช่วง

โปรดอ่านเอกสารนี้พร้อม Git status และ source ปัจจุบันก่อนแก้ งานเร่งคือทำ Endpoint Shadow ให้รับเหตุการณ์ใหม่ต่อเนื่อง ผ่าน Severity model ใน Morpheus GPU pipeline แล้วขึ้น Dashboard อัตโนมัติทันเดโมวันที่ 16 ต.ค. มี finite batch 32 records ที่ผ่านแล้ว แต่ continuous worker/polling ยังไม่ได้ทำ อย่าถือว่าการอ่านผลเก่าหรือ container Online เป็นหลักฐาน live flow อย่าเปิด BlueField publisher ที่ disabled หรือแก้ shared services เพื่อให้สถานะเขียว ตรวจ GPU reservation ก่อนรัน และรักษา output contracts/parity/offset acknowledgements เดิมไว้
