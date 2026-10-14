> Latest scope and takeover guide: [Company scope handoff](HANDOFF-COMPANY-SCOPE-20261014.md). Verified rehearsal results remain unchanged; earlier sections retain historical context.

# ผลซ้อม Windows → Morpheus Severity — 14 ต.ค. 2026

## ผลที่ยืนยัน

- Run `d20261014t055117-9fd3415a`; source checkpoint `506fbea432e7a208b7de5997e75b067dc929312f` พร้อมการแก้ reservation ใน demo/run.sh เท่านั้น
- เริ่ม 12:51:17 ไทย, worker_stopped 13:00:37; captured/scored/indexed = **5/5/5**
- Kafka wazuh-alerts partition 0 offsets 25727–25731; UID/raw hash/source ตรงทุกขั้นและ API document ID ตรง audit
- Windows Agent 004 สร้าง `EDRXDR-demo-20261014-125326-f559452b.txt` เวลา 12:53:26; alert 1791957206.906202, Rule 554; raw hash ตรวจซ้ำจาก Kafka envelope ตรงรายการ offset 25729
- UI ที่ผู้ปฏิบัติงานส่งแสดงจำนวน 2 → 3 → 5 ระหว่างรอบ และเปลี่ยนเป็นผลย้อนหลังหลังหยุด ภาพเหล่านี้ยังอยู่ในบทสนทนา ไม่ได้อ้างว่าเก็บวิดีโอหรือไฟล์ภาพใน Git
- Container/launcher exit 0, OOMKilled=false, stop_confirmed=true, reconciliation_required=false; consumer close ครบ 3 ตัว
- ผล nvidia-smi ที่ส่งเวลา 13:02:49 แสดง 0 MiB และไม่มี compute process ค้าง ส่วน gpu-snapshot.txt เป็นการอ่านใหม่ ณ ตอนเก็บหลักฐาน

## ความหมายและข้อจำกัด

รอบนี้เพิ่มหลักฐาน live normal-completion หลังแพตช์ supervisor cfecdcf และ UI 8f737f9 แล้ว ข้อความเอกสารเก่าที่ระบุว่ายังไม่มี live test ของแพตช์นี้เป็นสถานะก่อนรอบนี้เท่านั้น ยังไม่ผ่าน failure injection เช่น SIGTERM/SIGKILL, Docker outage, launch identity uncertainty หรือ evidence-write failure

เป็น bounded near-real-time microbatch เฉพาะ Severity ไม่ใช่บริการต่อเนื่องหรือหลักฐาน model accuracy; automated response OFF, production_ready=false; Behavioral/AE ไม่ได้รัน ผล low_severity ไม่ใช่คำรับรองความปลอดภัย

Windows event Capture → score ประมาณ 4225 ms รวมเวลารอ; Index request ไม่ใช่ ACK; เวลา browser เปิดดูไม่ใช่ pipeline latency

## หลักฐาน

- Repo: `training/evidence/rehearsal-d20261014t055117-9fd3415a/` มี audit, console, run metadata, exit/supervisor/container reports, API, sanitized origin และ SHA256 manifest
- ต้นฉบับนอก Git: `/home/saiuser/edrxdr-demo-runs/d20261014t055117-9fd3415a/`; raw-origin-AQcTEuZE.jsonl ถูกใช้ตรวจ hash แต่ไม่คัดลอก raw payload เข้า Git
- Reservation: `training/evidence/demo-reservation-20261014T054939042236Z/`; ได้รับอนุญาตถึง 14 ต.ค. 14:00 ไทย, launcher cutoff 13:55 รอบละไม่เกิน 600 วินาที ไม่ถือเป็นสิทธิ์สำหรับวันใหม่
- เก็บผลรอบเก่า 3/3/3 exit 124 และ 2/2/2 exit 0 รวมทั้งเอกสาร/หลักฐานเดิมไว้ ไม่แก้ผลย้อนหลัง

## งานต่อและการรับช่วง

1. ตรวจ HEAD/status และอ่านเอกสารนี้คู่กับ training/HANDOFF-NEXT-20261014.md ก่อนแก้ไฟล์ ห้าม reset/clean
2. เป้าหมายเดโมวันที่ 16 มีหลักฐานการไหลของ event จริงแล้ว เตรียมลำดับการนำเสนอและภาพ/วิดีโอที่ต้องใช้ หากต้องซ้อมใหม่ให้ตรวจ reservation และเวลาจริงก่อนเริ่ม GPU
3. ชุดนี้ไม่เริ่ม worker ใหม่ ไม่เปลี่ยน service/driver/interface ไม่หยุด shared stack; BlueField ยังต้อง inactive/dead/disabled
4. ปิดเว็บเฉพาะแท็บ start-ui.sh และ tunnel ได้เมื่องานนำเสนอเสร็จ ไม่หยุด shared services
5. Supervisor failure paths, Behavioral/BlueField/operator integration และ production hardening ยังแยกเป็นงานค้างตาม handoff เดิม
6. ยังไม่ลบไฟล์ข้อความทดสอบบน Windows; หากจะ cleanup ให้ระบุ exact path และคาดว่าจะเกิด Wazuh deletion event
7. หลัง commit สคริปต์สร้างและตรวจ bundle ใหม่ พร้อม checksum/receipt นอก repo ต้องดาวน์โหลดออกจาก VM แล้วตรวจ SHA256 อีกครั้ง ยังไม่ push remote

Bundle เก็บ Git history แต่ไม่รวม Docker/model volumes, ignored/untracked files, external run directories หรือรูปในบทสนทนา ประวัติย้ายไฟล์เดิมอยู่ใน handoff ฉบับก่อนและ EDRXDR-Archive ไม่ต้อง restore เพื่อทำงานต่อ
