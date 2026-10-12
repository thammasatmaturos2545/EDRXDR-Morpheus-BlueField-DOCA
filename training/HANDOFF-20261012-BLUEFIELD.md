# ส่งต่องาน BlueField และจัดเก็บไฟล์ — 12 ตุลาคม 2026

ตรวจไฟล์รายงานจริงและสถานะระบบบน VM เมื่อ `2026-10-12T14:24:50.161605+00:00` (UTC)
Repo: `/home/saiuser/EDRXDR-Morpheus`; branch `work/shadow-mode-v1`; commit `6ba5bf95ba00ee1dcf4d47728090ae7eb1b251c8` ก่อนอัปเดตเอกสาร

## งานที่เสร็จและขอบเขต

1. จัดระเบียบไฟล์ 7 รายการ โดยย้ายเข้า archive และบันทึก manifest ไม่มีการลบหรือคืนพื้นที่ดิสก์
2. หยุดและ disable `edrxdr-bluefield.service` ที่เรียก binary หายและวน restart (ผู้ใช้พบ NRestarts=73095 ก่อนหยุด)
3. Kafka replay ผ่าน: ส่งข้อมูล BlueField ที่บันทึกไว้ 6 แถว อ่านกลับ bytes/hash ตรง และ normalize ตรงกับผลเดิม
4. OpenSearch ผ่าน: บันทึกผล normalize จากไฟล์ 6 แถว อ่านกลับ source ตรงครบ และ query แยก null จาก zero ได้

ข้อมูลเป็นสอง interface ที่ down, carrier อ่านไม่ได้จึง null และ counters เป็นศูนย์จริง ไม่ใช่หลักฐานว่า link ปกติหรือไม่มีภัยคุกคาม
DOCA ในงานทดลองใช้ค้นหาอุปกรณ์ ส่วน counters มาจาก Linux sysfs ไม่ใช่ DOCA Flow/packet capture
Kafka กับ OpenSearch รอบเดิมทดสอบแยกขั้นผ่านไฟล์ และยังไม่มี continuous consumer/indexer หรือ live sampling; BlueField Historical Dashboard integration ถูกเพิ่มและยืนยันภายหลัง โดยยังเป็นข้อมูลย้อนหลัง ไม่ใช่ระบบสด
ไม่ใช้ GPU ไม่เปลี่ยน driver/interface ไม่เปิด automated response และไม่มีผลประเมินคุณภาพโมเดลใหม่

## หลักฐานและปลายทาง

- Kafka report: `experiments/bluefield-kafka-runs/20261012T141233Z-beaccd98dc/report.json`
- Kafka received/normalized JSONL และสคริปต์ที่ผ่าน: อยู่ในโฟลเดอร์เดียวกับ report
- Kafka topic: `review-bluefield-20261012t141233z-beaccd98dc` บน `edrxdr-replay-kafka-1`; แยก topic แต่ใช้ broker/resource ร่วม
- ข้อความ topic ใหม่ตั้ง retention 1 วัน; topic ไม่ถูกลบอัตโนมัติ และการล้างข้อความไม่จำเป็นต้องตรงเวลา 24 ชั่วโมงพอดี
- รอบ Kafka แรก FAIL ก่อนสร้าง topic: `experiments/bluefield-kafka-runs/20261012T140620Z-f8769c8cdb/`; รอบที่ผ่านปรับ stdin และใช้ docker exec -i เฉพาะ producer
- OpenSearch report: `experiments/bluefield-opensearch-runs/20261012T141653Z-6396a0d3/report.json`
- OpenSearch index: `review-bluefield-20261012t141653z-6396a0d3` บน `edrxdr-replay-opensearch-1`; ไม่มีการตั้งลบ index อัตโนมัติ
- Index ทดลองใช้ 1 primary / 0 replicas เฉพาะ index นี้ ไม่แก้ cluster หรือ index เดิม
- Raw SHA256: `dae332d54ffc04bdccf9dbd0b21deefbda26edf3343e8098da9d820cb6861714`
- Normalized SHA256: `868fb94d8cbf982084b99a3794622d801af15dd92110dd2109782c158e14d3f1`
- ผล: records 6; carrier null 6; first delta null 2; computed zero 4
- Query counts: carrier_exists 0; rx_zero 6; delta_exists 4; delta_zero 4
- รายงานเป็นผลการรันทดสอบก่อนหน้านี้ที่ตรวจไฟล์/hash ในรอบส่งต่อ ไม่ได้รัน integration ซ้ำขณะอัปเดตเอกสาร

## การจัดเก็บไฟล์นอก repo

Archive: `/home/saiuser/EDRXDR-Archive/20261012T135349958660Z`

| ตำแหน่งเดิมใต้ home | ตำแหน่งใหม่ใต้ archive |
|---|---|
| `edrxdr-before-dashboard-20261009-190859.tar.gz` | `backups/edrxdr-before-dashboard-20261009-190859.tar.gz` |
| `edrxdr-frontend-backup-20261009-063702.tar.gz` | `backups/edrxdr-frontend-backup-20261009-063702.tar.gz` |
| `edrxdr-frontend-backup-20261009-063953.tar.gz` | `backups/edrxdr-frontend-backup-20261009-063953.tar.gz` |
| `edrxdr-dashboard-updated.zip` | `packages/edrxdr-dashboard-updated.zip` |
| `edrxdr-dashboard-review-20261009-063702` | `dashboard-review/edrxdr-dashboard-review-20261009-063702` |
| `edrxdr-dashboard-review-20261009-063953` | `dashboard-review/edrxdr-dashboard-review-20261009-063953` |
| `EDRXDR-HANDOFF` | `handoff/EDRXDR-HANDOFF` |

`manifest.json` บันทึก from/to/state ของแต่ละรายการ; ตรวจว่าปลายทางยังมีอยู่และต้นทางไม่มีแล้ว
`EDRXDR-HANDOFF` ว่างตอนย้ายตามเงื่อนไข organizer ส่วน dashboard-review เป็นโฟลเดอร์ตรวจรุ่นเก่า
ไฟล์ backups เก็บย้อนกลับ, packages เก็บ zip ที่เคยส่ง; การย้ายไม่ได้พิสูจน์ว่า backup ทุกชุดกู้ได้สมบูรณ์
คง `~/EDRXDR-Morpheus`, `~/EDRXDR-Morpheus-personal` (linked Git worktree), โฟลเดอร์ทดลอง BlueField, hidden config, venvs และ Docker volumes ไว้ตำแหน่งเดิม
บางโฟลเดอร์เก่าอาจอ้าง absolute path เดิม จึงควรกู้คืนก่อนนำ build เก่ากลับมารัน

คำสั่งนี้ใช้เฉพาะเมื่อต้องการย้ายกลับ ไม่ต้องรันเพื่อทำงานต่อ:

```bash
python3 /home/saiuser/EDRXDR-Archive/20261012T135349958660Z/organize_edrxdr_20261012.py --restore /home/saiuser/EDRXDR-Archive/20261012T135349958660Z/manifest.json
```

ต้นฉบับหลักฐาน BlueField ที่ยังเก็บไว้:
- `~/edrxdr-bluefield-nullcheck.Bn44DZ` — monitor run
- `~/edrxdr-bluefield-normalize.udX6v2` — offline normalization run
- `~/edrxdr-bluefield-review.9F1hBG` — experimental monitor source
สคริปต์ส่งผ่าน `/tmp` เป็นไฟล์ชั่วคราว; ใช้สำเนาใน archive/โฟลเดอร์ผลทดสอบเพื่อเก็บระยะยาว
งานนี้ไม่ได้ย้าย dataset/model Docker volumes; อ้างตำแหน่งจาก HANDOFF เดิมและตรวจ mounts จริงก่อนใช้

## ปัญหาคงเหลือและงานถัดไป

1. BlueField Historical Dashboard จาก index ทดลองนี้เสร็จและยืนยันแล้ว; งานถัดไปคือคง historical/non-live semantics, เก็บหลักฐาน และอย่าเปิด live service/continuous pipeline โดยอัตโนมัติ
2. ต้องแสดง archived batch, เวลาตัวอย่างจริง, interface down, carrier unknown และ first-sample delta N/A; ห้ามแปลง null เป็น zero/healthy
3. Live normalizer เดิมแปลง null เป็น zero จึงยังไม่ส่ง schema ทดลองไป `bluefield-events` หรือ `morpheus-input`
4. Publisher binary ที่ service เรียกยังหาย; service ถูก stop/disable เพื่อหยุด restart loop เท่านั้น ยังไม่ deploy binary ใหม่หรือ enable service
5. ยังไม่มี live traffic, GPU parity, outage/recovery หรือ production-readiness validation ของ BlueField
6. เก็บเอกสาร/สคริปต์/หลักฐานเข้า Git หลังตรวจรายการและข้อมูลที่ไม่ควรเผยแพร่; สคริปต์อัปเดตนี้ไม่ commit/push

เริ่มงานต่อด้วยคำสั่งอ่านสถานะ:

```bash
cd ~/EDRXDR-Morpheus || exit 1
git branch --show-current
git log -1 --oneline
git status --short
systemctl show edrxdr-bluefield.service --no-pager -p ActiveState -p SubState -p UnitFileState
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}'
cat experiments/bluefield-kafka-runs/20261012T141233Z-beaccd98dc/report.json
cat experiments/bluefield-opensearch-runs/20261012T141653Z-6396a0d3/report.json
docker exec edrxdr-replay-opensearch-1 curl -fsS --max-time 15 'http://localhost:9200/review-bluefield-20261012t141653z-6396a0d3/_count?pretty'
```

ก่อนแก้ Dashboard ให้อ่าน `frontend/package.json`, `frontend/src/app/api/shadow/`, `frontend/src/app/shadow/` และ `frontend/src/lib/shadow.ts` จาก checkout จริง
ใช้ index ระบุชื่อชัดเจน ไม่ใช้ wildcard รวม Live/Replay/Shadow; ตรวจ output contracts และรัน tests/typecheck/build ตาม package.json จริง

## Snapshot ส่งต่อ

`training/evidence/handoff-20261012/` เก็บรายงาน Kafka/OpenSearch สำเนา manifest, service-state.txt, containers.txt, worktrees.txt และ Git status ก่อน/หลังแก้เอกสาร
Snapshot เป็นสถานะขณะบันทึก ไม่รับรองว่าบริการยังอยู่สถานะเดียวกันเมื่อเพื่อนเริ่มงาน
ไม่รวม model weights, credentials หรือฐาน OpenSearch ทั้งชุด

<!-- bluefield-dashboard-verified:start -->
## BlueField Historical Dashboard verification — 2026-10-13T00:52:28+07:00

เพิ่มการแสดงผล BlueField แบบข้อมูลย้อนหลังจาก index
`review-bluefield-20261012t141653z-6396a0d3` โดยไม่เปิด live publisher หรือเปลี่ยน live pipeline

ผลที่ยืนยัน:
- Historical API: PASS
- Dashboard UI: PASS
- Historical records: 6
- Interfaces: 2
- carrier null/Unknown: 6
- first-sample delta null/N/A: 2
- computed delta zero: 4
- BlueField synthetic tests: 7 PASS
- TypeScript typecheck: PASS
- Frontend regression: 7 groups PASS
- Next.js production build: PASS
- `null` และ `0` รักษาความหมายแยกกัน
- API ระบุ `mode=historical_review`
- API ระบุ `live=false`
- API ระบุ `production_ready=false`

BlueField service หลังทดสอบ:
- ActiveState=inactive
- SubState=dead
- UnitFileState=disabled

Safety:
- ไม่ start/enable `edrxdr-bluefield.service`
- ไม่ส่ง schema ทดลองเข้า live Kafka topic
- ไม่เปลี่ยน driver/interface
- ไม่ใช้ GPU
- ไม่เปิด automated response
- ข้อมูลนี้เป็น historical review ไม่ใช่ live telemetry หรือ production-readiness evidence

หลักฐาน:
- `training/evidence/bluefield-dashboard-20261012/api-verification.json`
- `training/evidence/bluefield-dashboard-20261012/service-state.txt`
- `training/evidence/bluefield-dashboard-20261012/ui-verification.txt`
- `experiments/bluefield-opensearch-runs/20261012T141653Z-6396a0d3/report.json`
- `experiments/bluefield-kafka-runs/20261012T141233Z-beaccd98dc/report.json`

งานถัดไป:
- review/stage หลักฐานและ source แบบ explicit
- ห้ามใช้ `git add .`
- ยังไม่เปิด BlueField live service
- งาน live/continuous consumer และ production validation ยังไม่ทำ
<!-- bluefield-dashboard-verified:end -->

<!-- bluefield-shadow-v1:start -->
## BlueField Shadow v1 — bounded archived pilot

Last verified: `2026-10-13T01:46:35+07:00`

Git at verification:
- Branch: `work/bluefield-shadow-v1`
- Base HEAD before this checkpoint commit: `6940d49ba29c`

Status: **PASS for bounded/manual archived Shadow evaluation only.**
This is **not** live BlueField telemetry and is **not production-ready**.

Verified data flow:

```text
committed archived BlueField normalized evidence
  -> replay Kafka: shadow-bluefield-input-v1
  -> bounded/manual validator + indexer
  -> replay OpenSearch: shadow-bluefield-v1
  -> /api/shadow/bluefield
  -> /shadow : BlueField Shadow Evidence
```

Verified runtime state:
- Kafka input records: **6**
- Consumer group: `edrxdr-shadow-bluefield-index-v1`
- Consumer offset: **6 / 6**
- Consumer lag: **0**
- OpenSearch index: `shadow-bluefield-v1`
- Indexed documents: **6**
- API mode: `shadow_bluefield`
- `historical=true`
- `live=false`
- `production_ready=false`
- `automated_response_allowed=false`
- Interfaces: **2**
- Carrier null/Unknown: **6**
- RX counter zero preserved: **6**
- First-sample delta null/N/A: **2**
- Computed delta zero preserved: **4**

Verification completed in this work session:
- `python3 -B shadow/test_bluefield_shadow.py`: **8/8 PASS**
- `frontend/tests/bluefield-shadow.cjs`: **10 checks PASS**
- existing `frontend/tests/shadow.cjs`: **20 checks PASS**
- TypeScript `tsc --noEmit`: **PASS**
- frontend regression: **7 groups PASS**
- ESLint: **0 errors**; one pre-existing warning in `tests/bluefield-history.cjs`
- Next.js production build: **PASS**
- manual `/shadow` UI verification: **PASS**

Safety state after testing:
- `edrxdr-bluefield.service`: **inactive / dead / disabled**
- No live `bluefield-events` topic was used by this pilot.
- No network driver/interface changes.
- No GPU use.
- No automated response.
- `raw_event` and literal `capture_scope` are not exposed through the Shadow browser projection.

Evidence:
- `training/evidence/bluefield-shadow-20261012/api.json`
- `training/evidence/bluefield-shadow-20261012/service-state.txt`
- `training/evidence/bluefield-shadow-20261012/ui-verification.txt`
- `shadow/BLUEFIELD_SHADOW.md`

Important limitations / remaining work:
- The pilot uses committed archived normalized evidence, not live sampling.
- Workers are finite one-shot/manual jobs, not a continuous consumer service.
- Long-term retention, poison-message handling, restart/recovery policy, continuous sampling, production capacity and production security review remain pending.
- Do not enable `edrxdr-bluefield.service` or connect experimental BlueField schema to shared/live topics without a separate review.
<!-- bluefield-shadow-v1:end -->
