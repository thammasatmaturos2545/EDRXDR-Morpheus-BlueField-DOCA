# EDRXDR-Morpheus — NEXUS SOC Handoff

**วันที่ส่งมอบ:** 15 ตุลาคม 2026  
**สถานะ:** Dashboard Integration Complete / Research Prototype  
**Production Ready:** NO  
**Automated Response:** OFF

## 1. ภาพรวมงานที่ทำสำเร็จ

รวม Dashboard เดิมกับ NEXUS SOC Dashboard ให้ใช้งานผ่านหน้าตาเดียวกันสำเร็จแล้ว

**Dashboard หลัก:** `http://127.0.0.1:3001/nexus/index.html`

ระบบประกอบด้วย:

- Security Overview และ Threat Detection
- NEXUS Exact UID Correlation
- Research & Experiments
- AI Model Quality Details
- Shadow Analysis และ Shadow Details
- BlueField Historical Review และ BlueField Details
- Research Evidence

ทุกส่วนที่เกี่ยวข้องกับ Research เป็นข้อมูลทดลองย้อนหลัง ไม่ใช่ Live Detection

## 2. สถานะการทำงานล่าสุด

| รายการ | ผลตรวจล่าสุด |
|---|---|
| NEXUS Dashboard | HTTP 200 |
| SOC Events | 109 |
| SOC Alerts | 109 |
| UID Lookup Matched | 9 |
| Shadow Severity | 32 |
| Shadow Behavioral | 32 |
| Shadow Matched | 32 |
| BlueField Shadow | 6 Records |
| BlueField Historical | 6 Records |
| Research APIs | HTTP 200 ครบ |
| Production Ready | False |
| Automated Response | False |

หมายเหตุ: จำนวน Events 109 เป็นข้อมูล Snapshot ที่แสดงอยู่ ไม่ใช่ข้อมูลย้อนหลังทั้งหมด และห้ามนำจำนวน Records จากต่าง Index มาบวกเป็นเหตุการณ์ใหม่โดยไม่ตรวจสอบ

## 3. ผลประเมิน AI Model

**Run ID:** `morpheus-raw-offline-check-20261008T203523Z-1803526`

| Metric | ผลลัพธ์ |
|---|---|
| Evaluated Samples | 1,314 |
| Precision | 67.18% |
| Recall | 100.00% |
| F1 Score | 80.37% |
| False Positive Rate | 32.82% |
| Parity Verification | PASS |
| Raw-event Verification | PASS |
| Development Numeric Gate | FAIL |
| Shadow Authorized | NO |
| Production Ready | NO |

**ปัญหาที่ต้องแก้:** Rule 2901 มี Precision 0% และ False Positive Rate 100% ตามรายงานปัจจุบัน

โมเดลยังไม่ผ่านเกณฑ์สำหรับ Production ห้ามนำผลไปเปิด Automated Response

## 4. ตำแหน่ง Repository และ Dashboard

**VM:** `saiuser@172.16.30.147`  
**Repository:** `/home/saiuser/EDRXDR-Morpheus`

**Dashboard Runtime:**

`/home/saiuser/edrxdr-nexus-integrated-preview-20261015`

**Frontend Source:**

`frontend/public/nexus/app.js`

**NEXUS API:**

`frontend/src/app/api/nexus/v1/snapshot/route.ts`

**UID Lookup:**

- `frontend/src/lib/uid-lookup.ts`
- `frontend/src/lib/uid-lookup-server.ts`
- `frontend/src/lib/nexus-soc.ts`
- `frontend/tests/uid-lookup.cjs`
- `uid_lookup/`

**Backups:**

`/home/saiuser/edrxdr-nexus-backups/`

ห้ามลบโฟลเดอร์ Integrated Preview แม้ชื่อจะเป็น Preview เพราะ Dashboard หลักกำลังทำงานจากโฟลเดอร์นี้

## 5. APIs ที่ใช้งาน

- `/api/nexus/v1/snapshot` — SOC และ UID Correlation
- `/api/model-quality` — Model Evaluation
- `/api/shadow/events` — Shadow Severity / Behavioral
- `/api/shadow/bluefield` — BlueField Shadow
- `/api/bluefield/history` — BlueField Historical

ข้อมูล SOC ใช้ Live OpenSearch พอร์ต 9200 บน Host

ข้อมูล Shadow และ BlueField ใช้ Replay OpenSearch Container ชื่อ `edrxdr-replay-opensearch-1`

ตอนตั้งค่าล่าสุด Replay OpenSearch มี IP `172.18.0.3` แต่ IP ภายใน Docker อาจเปลี่ยนได้ ต้องตรวจสอบใหม่หาก API เชื่อมต่อไม่ได้

## 6. วิธีเปิด Dashboard จาก Windows

เปิด PowerShell และเชื่อม SSH Tunnel:

`ssh -N -L 3001:127.0.0.1:3001 saiuser@172.16.30.147`

จากนั้นเปิด:

`http://127.0.0.1:3001/nexus/index.html`

หน้า Research:

`http://127.0.0.1:3001/nexus/index.html#research`

หน้า Shadow Details:

`http://127.0.0.1:3001/nexus/index.html#shadowdetails`

หน้า BlueField Details:

`http://127.0.0.1:3001/nexus/index.html#bluefielddetails`

หน้า Model Quality Details:

`http://127.0.0.1:3001/nexus/index.html#modeldetails`

หน้า Research Evidence:

`http://127.0.0.1:3001/nexus/index.html#researchevidence`

## 7. การตรวจสุขภาพระบบ

หลัง SSH เข้า VM ให้ตรวจ:

- `git status --short`
- `git branch --show-current`
- `ss -H -ltnp 'sport = :3001'`
- `curl --noproxy '*' -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3001/nexus/index.html`
- `node --check frontend/public/nexus/app.js`
- `git diff --check`

หาก Dashboard หรือ API มีปัญหา ให้ตรวจ Process, Environment และการเชื่อมต่อ Replay OpenSearch ก่อน ห้ามรีสตาร์ทบริการส่วนกลางโดยไม่ประสานทีม

## 8. Git Working Tree

งาน NEXUS และ UID Lookup มีไฟล์ที่ยังไม่ได้ Commit:

- `frontend/public/nexus/app.js` — Modified
- `frontend/src/app/api/nexus/v1/snapshot/route.ts` — Modified
- `frontend/src/lib/nexus-soc.ts` — Modified
- `frontend/src/lib/uid-lookup-server.ts` — Untracked
- `frontend/src/lib/uid-lookup.ts` — Untracked
- `frontend/tests/uid-lookup.cjs` — Untracked
- `uid_lookup/` — Untracked

ให้ตรวจ Git Status ปัจจุบันอีกครั้งก่อนทำงาน

**ยังไม่มีการ Commit หรือ Push งานชุดนี้** ห้ามใช้ `git reset --hard` หรือ `git clean -fd` เพราะอาจลบงานที่ทีมทำค้างไว้

## 9. สิ่งที่ห้ามเปลี่ยนโดยไม่ได้รับอนุญาต

- ห้ามเปิด BlueField Live Service
- ห้ามเปิด Automated Response ใน Production
- ห้ามรัน H100/GPU โดยไม่มีรอบจองที่ได้รับอนุญาต
- ห้าม Reset Kafka Offsets
- ห้ามลบ OpenSearch Index หรือ Backlog
- ห้ามแก้ CUDA, GPU Driver หรือ Network ของ VM
- ห้าม Restart Shared Services โดยพลการ
- ห้าม Commit/Push งานของทีมโดยไม่ตรวจสอบ
- NEXUS Correlation ต้องใช้ Exact `event_uid` เท่านั้น ห้ามจับคู่ด้วย timestamp, rule หรือ host แบบ fallback

## 10. งานที่ควรทำต่อ

**Priority 1 — Dashboard Reliability**

ตรวจ Auto-start และ Recovery ของ Next.js พอร์ต 3001 เพื่อให้ระบบกลับมาทำงานได้หลังการ Restart โดยไม่กระทบบริการอื่น

**Priority 2 — Dashboard Security**

ตรวจ Authentication, Authorization, RBAC และ Credentials สำหรับการอ่านข้อมูลจาก Wazuh และ Replay OpenSearch

**Priority 3 — Historical Events**

พัฒนา Historical Event Search พร้อม Pagination, Filter และ Exact UID Matching เพราะ Dashboard ปัจจุบันแสดงเพียง Snapshot

**Priority 4 — AI Model Improvement**

ปรับปรุง Rule 2901 ลด False Positives ตรวจผลราย Rule และรักษาชุด Held-out Test แยกจาก Training รวมถึงไม่ใช้ชุด 479 Events สำรองเพื่อฝึกโดยไม่มีแผนประเมินที่ชัดเจน

**Priority 5 — Source Control & Documentation**

ตรวจสอบ Uncommitted Changes ร่วมกับทีม ก่อนตัดสินใจ Commit หรือ Push

## 11. สถานะก่อนส่งมอบ

การตรวจครั้งล่าสุดพบว่า:

- Dashboard หลักพอร์ต 3001 ทำงานปกติ
- Preview พอร์ต 3002–3005 ปิดเรียบร้อย
- API ที่ตรวจทั้งหมดตอบ HTTP 200
- ไม่มีไฟล์ Backup ถูกลบ
- CPU Next.js ประมาณ 0.2%
- RAM ของ VM Available ประมาณ 208 GiB
- Automated Response ยังคง OFF

**สรุป:** NEXUS SOC Dashboard พร้อมสำหรับการสาธิตและการตรวจผลย้อนหลัง แต่ยังไม่พร้อมใช้งาน Production

ผู้รับช่วงสามารถเริ่มจากไฟล์นี้ ร่วมกับ `training/HANDOFF.md` และ `training/LATEST_STATUS.md` แล้วตรวจสถานะจริงบน VM ก่อนพัฒนาต่อ
