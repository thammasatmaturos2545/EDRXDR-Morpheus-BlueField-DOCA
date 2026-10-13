# ส่งต่องาน EDR/XDR — checkpoint หลัง Dashboard และ supervisor

เอกสารนี้สรุปผลที่ผู้ปฏิบัติงานส่งจาก VM และภาพหน้าจอในวันที่ 14 ตุลาคม 2026 เวลาไทย ไม่ใช่การตรวจสถานะบริการแบบต่อเนื่อง เมื่อรับงานต้องตรวจ Git เวลา และสถานะจริงอีกครั้ง

## 1. เป้าหมายและตำแหน่งงาน

- เป้าหมายเดโมความคืบหน้า 16 ต.ค.: เหตุการณ์ใหม่จาก Wazuh → Kafka → Morpheus Severity บน GPU → Kafka output → OpenSearch → Dashboard อ่านอัตโนมัติ
- VM: `saiuser@172.16.30.147` ชื่อ `oa-hgx-h100-bu-02`
- Repo: `/home/saiuser/EDRXDR-Morpheus`
- Branch: `work/bluefield-shadow-quarantine`
- Code checkpoint ล่าสุดก่อนเอกสารฉบับนี้: `8f737f9`; commit เอกสารฉบับนี้จะเป็น HEAD ถัดไป ให้ดู `git log -1`
- มีผล bounded near-real-time microbatch แล้ว ไม่ใช่บริการ production ที่ทำงานตลอดเวลา ไม่ใช่ข้อพิสูจน์ความแม่นยำโมเดล
- Automated response OFF; `production_ready=false`; Behavioral/AE ไม่ได้ทำงานใน demo worker นี้

## 2. สิ่งที่เสร็จและระดับหลักฐาน

| Checkpoint | งาน | หลักฐานและขอบเขต |
|---|---|---|
| `5701979` | เปลี่ยน launcher เป็น detached container แล้วตรวจสถานะ | รอบใหม่ exit 0 ทั้ง container/launcher หลัง inference; ไม่ได้พิสูจน์ทุก failure path |
| `181b5f0` | เอกสารปิดรอบเดโมและ API/UI verification | บันทึกผล 2/2/2 และข้อจำกัด; bundle ของ checkpoint นี้ตรวจผ่านและดาวน์โหลดไป Windows แล้ว |
| `cfecdcf` | ตรวจ deadline ก่อน launch, ตรวจสถานะหลัง stop, ระบุ reconciliation_required และจัดการ KeyboardInterrupt | mocked offline tests 14 กรณีผ่านบน VM; ยังไม่มี live Docker/GPU validation ของแพตช์นี้ |
| `8f737f9` | Dashboard แยกผลย้อนหลัง/พักอ่าน/heartbeat และแก้ latency | regression ผ่านบน VM, ภาพหน้าจอแสดง UI ใหม่; ไม่มีผล build log แยกที่เก็บในหลักฐานชุดนี้ |

### รอบที่จบครบสายและปิดสำเร็จ

- Run: `d20261013t181858-e1bbae7e`, 14 ต.ค. ประมาณ 01:18–01:28 Asia/Bangkok
- Kafka source `wazuh-alerts`, partition 0, boundary 17230; เหตุการณ์ offsets 17230 และ 17231
- captured/scored/indexed = 2/2/2; API total/shown = 2/2; last reported lag = 0/0/0
- UID, raw SHA256, source coordinates และ document ID ตรงกันระหว่าง console audit กับ API
- Rule 61104: UID `6dafc75f172dae38179c93ec309153539cd926a7e0a2a18d1b3a4d63431c141b`; SHA256 `1ecc3db9e7cadcb1228eff173932c18e491879ebdf0a7ce64e025583932281b4`
- Rule 60642: UID `c65c36402bf3426d55af34e327010f9b815ef24189bfbdbffdf67b3296c44fde`; SHA256 `2d64922659008dbb6f05bea4999504a960adcf2994d30ab90c635afe9244dfd2`
- Model: `wazuh-severity-context-v2-balanced-20261008T190719Z-1398863`, threshold 0.5; ทั้งสองผลเป็น low_severity
- Engine SHA256: `64ef3bad1a0c4e60de34681697db8fec748a31de450dd9df1e8b9825e1afd9ca`
- consumer_close_done ครบ capture/score/index, consumer_cleanup_complete และ process_exit_requested=0
- Container exit=0, launcher exit=0, OOMKilled=false, runtime Error ว่าง
- การไม่พบ GPU compute process ค้างเป็นผลตรวจที่ผู้ปฏิบัติงานรายงานในช่วงปิดรอบ ไม่ใช่สถานะปัจจุบัน
- ผล live รอบนี้เกิดก่อนแพตช์ `cfecdcf`; ห้ามนำมาอ้างว่าแพตช์ failure handling ใหม่ผ่าน live test แล้ว

### รอบ Windows เดิม ต้องเก็บผล 124 ไว้

- Run `d20261013t164314-c1b4d787`: 3/3/3 ผ่าน API/UI; launcher exit 124
- Windows Agent 004 `windows-agent` เชื่อมต่อ Wazuh แล้ว; file-added event Rule 554 Level 5
- ไฟล์ `EDRXDR-demo-20261013-234421.txt` ใน `C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Startup`
- Alert ID `1791909861.2210586`, source offset 17193, UID `036d8161ba1ac286f7ebc96fc6629b2b7aa658e932b3080eec8d10a0b09cea71`
- ตรวจ raw JSON/hash ตรงกับ Wazuh Windows origin แล้ว จึงมีหลักฐาน endpoint → pipeline ของรอบนี้
- ต้องไม่เปลี่ยน 124 เป็น PASS และไม่อ้างว่าเหตุการณ์สองรายการของรอบใหม่คือ file event เดิม

## 3. Dashboard และการตีความ

- หน้า `/demo?run=RUN_ID`, พอร์ต 3001; API `/api/demo?run=RUN_ID`
- อ่านอัตโนมัติทุก 3 วินาทีหลัง request จบ, แสดงล่าสุดไม่เกิน 20 รายการและ total ของรอบ
- stopped แสดง “ผลย้อนหลัง — worker รายงานว่าหยุดแล้ว”; polling ไม่ได้เริ่ม inference ใหม่
- Heartbeat ล่าสุด ณ เวลา API ไม่ได้พิสูจน์ inference ต่อเนื่อง; worker stopped ไม่ได้พิสูจน์ container exit
- ค่า lag เป็นค่าที่ worker รายงานล่าสุด ไม่ใช่การถาม broker สดทุกครั้งที่เปิดเว็บ
- Capture → score = 9458 และ 2477 ms ในรอบ 2/2/2 รวมการรอ ไม่ใช่เวลา inference ล้วน
- Index request คือเวลาเริ่ม request; ACK ต้องดู audit
- เอาระยะเวลา Capture → browser ออกแล้ว เพราะการเปิดเว็บย้อนหลังทำให้ดูเหมือน pipeline ช้า เก็บเพียงเวลา browser พบรายการตามนาฬิกาผู้ดู
- AI score ไม่ใช่ probability ว่าเป็นการโจมตี และ low_severity ไม่ใช่คำรับรองว่าปลอดภัย
- ภาพหลังแพตช์มี API time 14/10/2569 02:13:51, 2/2/2, สองรายการ และกล่องผลย้อนหลัง ภาพอยู่ในบทสนทนา ไม่ได้ถูกบันทึกเป็นรูปใน Git โดยตัวติดตั้ง

## 4. หลักฐานและไฟล์สำคัญ

Paths ต่อไปนี้อ้างอิงจาก root repo:

- `training/evidence/demo-detached-d20261013t181858-e1bbae7e/`: console, container ID/state, launcher exit, supervisor report
- `training/evidence/demo-close-20261014/`: API snapshot, service state, verification summary
- `training/evidence/severity-flow-d20261013t164314-c1b4d787/`: หลักฐานรอบ Windows เดิมและ exit 124
- `training/evidence/supervisor-followup-20261013T190745844629Z/`: 14 offline tests, scope/ข้อจำกัด
- `training/evidence/demo-presentation-20261013T191242957316Z/`: regression และ scope ของหน้าใหม่
- `training/HANDOFF-DEMO-CLOSE-20261014.md`: ผลก่อนสองแพตช์ล่าสุด อ่านเป็นประวัติประกอบ
- `training/HANDOFF-SEVERITY-FLOW-20261013.md`, `training/HANDOFF-OPERATOR-20261013.md`: รายละเอียดเดิม
- `demo/run.sh`, `demo/supervise.py`, `demo/worker.py`, `demo/compose.yml`: launcher/supervisor/worker/config
- `demo/SHUTDOWN_DIAGNOSTICS.md`: marker การ cleanup และข้อจำกัด shutdown
- `frontend/src/app/demo/page.tsx`, `frontend/src/app/api/demo/route.ts`, `frontend/src/lib/demo.ts`: UI/API/parser
- หลักฐานต้นฉบับนอก Git: `/home/saiuser/edrxdr-demo-runs/RUN_ID/`

## 5. วิธีรับงานต่อแบบไม่ใช้ GPU

บน VM:

```bash
cd /home/saiuser/EDRXDR-Morpheus || exit 1
TZ=Asia/Bangkok date -Is
git branch --show-current
git log -5 --oneline
git status --short
cat training/HANDOFF-NEXT-20261014.md
systemctl show edrxdr-bluefield.service --no-pager -p ActiveState -p SubState -p UnitFileState
docker ps --format 'table {{.Names}}\t{{.Status}}'
```

ห้าม reset/clean ถ้าพบงานค้าง ให้ตรวจงานนั้นก่อน ห้ามเดาสถานะใหม่จากเอกสารนี้

เปิด UI บน VM ในแท็บเฉพาะ:

```bash
cd /home/saiuser/EDRXDR-Morpheus || exit 1
bash demo/start-ui.sh
```

สคริปต์ build frontend แยกและใช้ dependency ที่มีอยู่ รอ Ready; ถ้าพอร์ตถูกใช้ให้ตรวจเจ้าของก่อน ไม่หยุด process โดยเดา เปิด Windows PowerShell อีกแท็บ (ไม่ใช่ Bash บน VM):

```powershell
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -L 127.0.0.1:3001:127.0.0.1:3001 saiuser@172.16.30.147
```

หลังใส่รหัสหน้าจอนิ่งเป็นปกติของ tunnel เก็บสองแท็บไว้ แล้วเปิด:
`http://127.0.0.1:3001/demo?run=d20261013t181858-e1bbae7e`

ทดสอบ offline เมื่อแก้โค้ด โดยใช้ venv แยกและ dependency frontend ที่มีอยู่:

```bash
cd /home/saiuser/EDRXDR-Morpheus || exit 1
test_env=$(mktemp -d /tmp/edrxdr-offline-XXXXXXXX)
python3 -m venv --without-pip "$test_env/venv"
"$test_env/venv/bin/python" -B -m unittest discover -s demo -p 'test_supervise*.py' -v
cd frontend
node tests/demo.cjs
npm run typecheck
```

ไม่มีการติดตั้ง package ใหม่ในชุดนี้ และไม่เรียก `demo/run.sh`

## 6. งานถัดไปตามลำดับ

1. **เตรียมซ้อมวันที่ 16:** ยืนยันวัน/เวลาจอง GPU ใหม่, เตรียมเหตุการณ์ endpoint ที่ได้รับอนุญาต, เปิด UI/tunnel ก่อนเริ่ม worker, เก็บวิดีโอหรือภาพลำดับเวลาระหว่างเหตุการณ์ไหลจริง
2. **ตรวจ launcher ก่อนใช้แพตช์ใหม่กับ GPU:** อ่าน run.sh และ reservation, ยืนยัน UUID/ไม่มีงานทีมอื่นบน GPU; ถ้าต้องแก้หน้าต่างเวลาให้สำรองและบันทึกสิทธิ์ใหม่ ห้ามขยายเวลาเอง
3. **ซ้อม event ใหม่ครบสาย:** ใช้ run ใหม่ ให้ worker_ready ก่อนสร้าง event; source high offsets รับ arrivals หลัง boundary ไม่ย้อน backlog; ตรวจ UID/hash/source/document ID ผ่าน capture → score → index → API/UI
4. **เกณฑ์ผ่านรอบซ้อม:** มี event ต้นทางที่ยืนยันได้, audit/model result ตรงกัน, UI อัปเดตขณะรัน, ปิดครบและมี container/launcher exit จริง, ไม่มีงาน GPU ของรอบค้าง บันทึก error/124 ตามจริง ไม่แก้ผลย้อนหลัง
5. **Supervisor robustness ที่ยังเหลือ:** SIGTERM/SIGKILL, interruption ระหว่าง cleanup, evidence-write failure, launch timeout ที่ไม่ทราบ container ID, Docker outage/stop failure ต้องมีขั้นตอน reconcile; stop_confirmed=false ไม่ใช่หลักฐานว่าหยุดแล้ว ไม่มีการ retry อัตโนมัติหรือหยุดตาม prefix กว้าง
6. **การนำเสนอ:** เพิ่มความอ่านง่าย/การจัดวางตามต้องการ แต่ไม่ทำให้ retained result ดูเป็น live; เก็บข้อจำกัด Severity-only และ latency ให้ชัด
7. **Backup/reproducibility:** Git bundle ไม่รวม model volumes/ข้อมูล broker/ไฟล์นอก repo ต้องจัดทำแผนสำรองสิ่งเหล่านี้ก่อนคืนหรือย้าย VM โดยตรวจสิทธิ์และขนาดก่อน
8. **นอกขอบเขตเดโมที่ยังค้าง:** Behavioral/AE live integration, live BlueField, authoritative operator replay workflow, model-quality evaluation, throughput/recovery/security/retention และ production hardening

ตอนเริ่ม GPU ต้องตรวจเวลาจริง ไม่ควรคัดลอกคำสั่งรันเก่าทันที การ resume RUN_ID เก่าต้องตรวจ source retention/offset/ชื่อ container ที่คงอยู่ก่อน; เดโมรอบใหม่ควรใช้ run ใหม่

## 7. ข้อจำกัด VM และสถานะส่วนอื่น

- สิทธิ์ GPU ที่รายงานล่าสุด: 13 ต.ค. 23:00 ถึง 14 ต.ค. 03:00 ไทย; launcher cutoff 02:55 เป็นประวัติ ไม่ใช่สิทธิ์รันในวันถัดไป
- GPU UUID: `GPU-61a1dd9b-a3c2-86dc-15b9-1277b5b949bb`
- VM ใช้ร่วมกัน ห้ามแก้ driver/network interface หรือหยุด shared stack/process ของทีมอื่น
- BlueField publisher ต้อง inactive/dead/disabled; เดิม binary ที่ service อ้างถึงหายและเกิด restart loop การปิด service ไม่ใช่การซ่อม telemetry
- DOCA/BlueField review เดิม: 6 archived records, carrier null ทั้งหมด, first delta null 2, computed zero 4; Kafka/offline normalization/OpenSearch persistence ผ่านใน isolated review เท่านั้น ไม่ใช่ live sampling integration
- Operator sink step 8: 123 offline tests และ read-only preflight ผ่าน; ตอนตรวจไม่มี quarantine index, replay_authorized=false; authoritative replay/recovery end-to-end ยังไม่ยืนยัน
- ชุด shadow เดิม 32 matched, 13 weak-label FP candidates Rule 19008, AE scored 0 เป็น snapshot เก่า ไม่ใช่จำนวนปัจจุบันหรือผลยืนยัน false positive
- Morpheus service เก่าที่ exited ไม่ใช่ demo container ที่ผ่านรอบนี้; อย่า restart shared/เก่าเพื่อให้การ์ดเป็นสีเขียว

## 8. การจัดไฟล์และ backup

วันที่ 12 ต.ค. ย้าย 7 รายการเข้า `/home/saiuser/EDRXDR-Archive/20261012T135349958660Z/`:

- backups: `edrxdr-before-dashboard-20261009-190859.tar.gz`, `edrxdr-frontend-backup-20261009-063702.tar.gz`, `edrxdr-frontend-backup-20261009-063953.tar.gz`
- packages: `edrxdr-dashboard-updated.zip`
- dashboard-review: `edrxdr-dashboard-review-20261009-063702`, `edrxdr-dashboard-review-20261009-063953`
- handoff: `EDRXDR-HANDOFF`

มี manifest.json และสำเนา organize_edrxdr_20261012.py สำหรับ restore การย้ายไม่ได้ลบไฟล์/คืนพื้นที่/เปลี่ยน service หรือ Git ไม่ย้าย repo หลัก, personal worktree, experiment ที่ใช้งาน หรือ Docker volumes ไม่ต้อง restore เพื่อรับงานต่อ

Bundle เดิม `edrxdr-20261013T190227Z.bundle` ครอบคลุมถึง `181b5f0` ตรวจผ่านบน VM และ SHA256 สำเนาที่ดาวน์โหลดตรงกันในการตรวจ local ก่อนทำแพตช์ แต่ไม่รวม `cfecdcf`/`8f737f9`/เอกสารฉบับนี้

สคริปต์ปิดงานใหม่จะสร้าง bundle หลัง commit เอกสารนี้ใน `/home/saiuser/EDRXDR-Archive/git-bundles/` พร้อม SHA256 และ receipt ที่บันทึก HEAD/ผลตรวจ ให้ดูผลรันจริงก่อนอ้างว่าเสร็จ ไม่ push remote อัตโนมัติ

Bundle เก็บ committed history/refs ไม่รวม untracked/ignored files, external runs, screenshots ในแชท, secrets/config นอก Git, Python/Node environments, Docker images/volumes หรือโมเดล จึงใช้กู้ source ได้แต่ยังไม่ใช่ VM disaster-recovery backup

กู้ source เฉพาะกรณีจำเป็น ลงโฟลเดอร์ใหม่เท่านั้น:

```bash
git clone -b work/bluefield-shadow-quarantine /path/to/verified.bundle EDRXDR-restored
```

ห้าม clone ทับ repo ที่มีงานอยู่ การเปิด source จาก bundle ไม่ได้ทำให้ environment/โมเดลพร้อมรัน GPU

## 9. ข้อความส่งต่อแบบย่อ

รับช่วง repo `/home/saiuser/EDRXDR-Morpheus` บน `saiuser@172.16.30.147`, branch `work/bluefield-shadow-quarantine` เริ่มตรวจ HEAD/status และอ่าน `training/HANDOFF-NEXT-20261014.md` ก่อนเปลี่ยนไฟล์ มีผล bounded Severity flow 2/2/2 พร้อม API/UI และ clean exit ที่ checkpoint 5701979 แล้ว; cfecdcf เพิ่ม supervisor failure-state checks ผ่าน offline 14 tests; 8f737f9 ปรับ Dashboard ผลย้อนหลัง/latency ผ่าน regression และภาพ UI ห้ามอ้างสองแพตช์หลังว่าผ่าน live GPU test งานถัดไปคือซ้อม event ใหม่พร้อมบันทึก UI และตรวจ shutdown ภายใต้ reservation ใหม่ เก็บประวัติรอบ 124 ไว้ ห้าม reset/clean, เปิด BlueField, เปลี่ยน driver/interface, หยุด shared stack หรือเปิด automated response ตรวจ receipt ของ bundle ใหม่เพื่อทราบ final handoff HEAD; ยังไม่มี push ในชุดงานนี้
