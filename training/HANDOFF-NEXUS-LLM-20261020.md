# ส่งต่องาน NEXUS / All Events / LLM — 20 ตุลาคม 2026

## สถานะและสิ่งที่รวม
ตรวจจาก backup nexus-systemd-20261020T012409921855Z ซึ่งตรวจ SHA256 แล้ว
ฐาน Git 82521f898e8ab25d2c4891b81bc211a9015ccd89, branch work/nexus-exact-ai-v1
ยังมี WIP ของทีม: ห้าม reset/clean หรือ git add ทั้ง repo โดยไม่ review
รวม All Events UI + History API/Auth/AI enrichment และ Observed endpoints
รวม core.js ที่เก็บ unknown/null แทน offline/0 และ nexus-endpoints test
Manager patch, status API และ Snapshot API ใน backup ตรงกับ runtime จึงไม่ทับไฟล์เหล่านั้น
เก็บ query_history.py / sync_history.py / run-history-sync.sh ใน history/ เป็น source of record
ยังไม่เปลี่ยน absolute runtime paths ไม่ deploy ไม่ build ทับบริการ ไม่เริ่ม LLM/GPU
ไม่รวม next-env.d.ts generated, history-ai.ts.before-type-safety, DB, secret, node_modules, .next

## Runtime ที่ยืนยันจากผลผู้ปฏิบัติงาน
VM saiuser@172.16.30.147, repo /home/saiuser/EDRXDR-Morpheus
Candidate /home/saiuser/nexus-history-preview-20261020/nexus-build-candidate-20261020
Build B4ugzj7XFWOd_hGFLdjpl; Node /home/saiuser/.nvm/versions/node/v20.20.2/bin/node
Units nexus-all-events-prod-3001.service และ nexus-all-events-prod-3006.service
ทั้งสองพอร์ตผ่าน manual restart + History 401/200 + exact AI UID + Snapshot
Node18 เกิด Snapshot503 ในการเปรียบเทียบ; Node20 ผ่าน แต่กลไกภายในยังไม่พิสูจน์
Restart=on-failure/5s; units disabled, Linger=no: ยังไม่รับประกันหลัง logout/reboot
ไม่มีสิทธิ์จอง GPU รอบใหม่ อย่าเปิด inference/training โดยอนุมานจากข้อมูลเก่า
Manager ของเรา /wazuh-wazuh.manager-1 project=wazuh
Manager เพื่อน luckyfive_wazuh-wazuh.manager-1 ห้ามเลือกเป็น fallback

## วิธีรับช่วง (VM)
1. cd /home/saiuser/EDRXDR-Morpheus; git branch --show-current; git log -1 --oneline; git status --short
2. อ่านเอกสารนี้และ training/HANDOFF-NEXUS-SHARED-HOST-20261017.md รวมถึง handoff systemd ล่าสุด
3. ตรวจ systemctl --user show nexus-all-events-prod-3001.service --no-pager -p ActiveState -p MainPID -p ExecStart
4. ตรวจ 3006 เช่นเดียวกัน และ ss -H -ltnp ตรวจ listener/cwd ก่อนเปลี่ยน process
5. ทดสอบแบบ offline ก่อน แล้วเปิด candidate บนพอร์ตว่างที่ตรวจแล้ว ห้าม build ทับ .next ที่รันอยู่
6. อย่าส่ง secret มาในแชท/commit/arguments หรือส่ง raw logs ไป LLM ภายนอกโดยยังไม่ตกลงข้อมูลและผู้ให้บริการ
Windows: ssh -N -L 127.0.0.1:3001:127.0.0.1:3001 saiuser@172.16.30.147
เปิด http://127.0.0.1:3001/nexus/index.html#allevents

## จุดเชื่อมต่อ LLM ที่เสนอ (ยังไม่ได้ implement)
ทำ server-side summary adapter แยกจาก history-ai.ts: LLM สรุปหลักฐาน ไม่ใช่โมเดล Severity
เส้นทางเสนอ POST /api/nexus/v1/summary (ยังไม่มี) ต้องตรวจ auth ฝั่ง server ทุกครั้ง
อย่าพึ่ง localStorage token หรือเชื่อว่ามี History auth แล้วจะคุ้มครองทุก API
LLM provider/model/credentials ยังไม่ได้เลือก ไม่ติดตั้ง SDK หรือเรียก external provider ในรอบนี้
เริ่มจาก mock provider + synthetic fixtures; จำกัดจำนวน events/token/time และอัตราคำขอ
ใช้ event_uid ที่ตรวจรูปแบบแล้ว ดึงหลักฐานฝั่ง server ภายใน scope ที่ผู้ใช้เข้าถึงได้
อย่าส่ง request object/credentials/raw_json ทั้งก้อนให้โมเดล ใช้ allowlist และลดข้อมูล IP/user/path ตามนโยบายทีม
ข้อความใน log เป็นข้อมูลที่ไม่น่าเชื่อถือ ไม่ใช่คำสั่ง: ทดสอบ prompt injection และไม่ให้โมเดลใช้ tools/สั่งตอบสนอง

Input contract ที่เสนอ:
- request_id, event_uids[], time_window, source_scope, observed_at
- evidence[]: event_uid, timestamp_utc, rule_id, agent_id/name, description,
  ai_status, ai_score (raw0–1 หรือ null), ai_label
Output contract ที่เสนอ:
- summary_status: generated/unavailable/insufficient_evidence
- summary_th, findings[{text,evidence_uids[]}], unknowns[], suggested_checks[]
- provider/model/prompt_version/generated_at, input evidence hash, truncated flag
- production_ready=false, automated_response_allowed=false
ทุกข้อสรุปต้องอ้าง UID ที่มีใน input; ผล LLM ต้องตรวจ schema และแสดงเป็นข้อความ escaped
คะแนน Severity ต้องคงเดิม: ห้ามโมเดลเติมคะแนนที่ไม่มี เปลี่ยน threshold หรืออ้างความน่าจะเป็นการโจมตี
แยก inference/model version ของ LLM กับ Wazuh severity model; ไม่เขียนทับผล Morpheus
ก่อนเพิ่ม persistence ของ summaries ให้กำหนด schema/retention/access แยก ไม่แก้ฐาน events โดยตรง

## API ที่มีจริง
GET /api/nexus/v1/history?page=1&hours=all&search=<UID>
รองรับ hours all/24/168/720; page1–10000; page size100; search<=128 ตัวอักษร
History เป็น retained snapshot ไม่ใช่ realtime และอาจขาดข้อมูลตามการนำเข้า/retention
search เป็น substring หลายฟิลด์ ไม่ใช่ exact-UID endpoint: summary ต้องกรอง event_uid ให้เท่ากันจริง
Response total/page/page_size/total_pages/has_next/events/ai_lookup_status
Event มี event_key/event_uid/timestamp_utc/rule_id/agent_id/agent_name/description และ ai fields
ai_status: matched/not_scored/conflict/unavailable; not_scored ไม่ใช่ safe และ null ไม่ใช่0
คะแนนแสดง score*100 หนึ่งทศนิยม /100 ไม่ใช่เปอร์เซ็นต์โอกาสถูกโจมตี
GET /api/nexus/v1/snapshot?hours=168 เป็น sampled/live-window view ไม่ใช่ประวัติทั้งหมด
History Basic auth username saiuser, secret อยู่เฉพาะ VM ที่ preview-access.secret
อย่า copy secret เข้า repo. ตัว route ปัจจุบันอ้าง query script ด้วย absolute path
query script ใช้ DB ข้างไฟล์; sync script/wrapper อ้าง ~/nexus-history-preview-20261020
ดังนั้นรัน source ใน repo โดยตรงไม่เท่ากับย้ายบริการ ต้องทำ config migration แยกในอนาคต

## เกณฑ์รับงาน LLM
ทดสอบ: UIDไม่พบ, ไม่มีคะแนน, หลักฐานขัดแย้ง, provider timeout, schemaผิด,
จำนวนเกินขีดจำกัด, authขาด/ผิด, logมีprompt injection, HTML/scriptในผลลัพธ์,
LLMอ้าง UIDนอก input, ผล cached เก่าหลัง evidence/model เปลี่ยน
ต้องล้มเหลวอย่างชัดเจน ไม่แสดงข้อความสรุปสำเร็จปลอม และไม่ลดการป้องกัน Manager
ผ่าน regression Manager13กรณี, sampling, UID lookup, endpoints, History query และ typecheck
ประเมินความถูกต้องของ summary ด้วยหลักฐาน/ผู้ตรวจ แยกจาก pipeline success และ model quality

## ข้อจำกัดที่พบจากการอ่านโค้ด (ยังไม่เปลี่ยนใน reconciliation)
- history sync ใช้ชื่อ containerตายตัว ยังไม่ได้ตรวจ labels/ID แบบ resolver ของ API
- History AI ไม่ตรวจ timed_out ของ OpenSearch อย่างชัดเจน ต้องทดสอบ partial response ก่อนอาศัยสรุปว่าครบ
- core.js มี fallback timestamp เป็น generated_at; กราฟจึงต้องตรวจต้นกำเนิดเวลา
- Overview บางคำยังใช้ enrolled/online และ drawer บอกบันทึกได้แม้ write_enabled=false
- ไม่มี root-level auth สำหรับทุก NEXUS API
- ยังไม่มี LLM implementation และยังไม่ใช่ production ready

## สำรองและประวัติ
สำเนานอก VM มี committed-history.bundle + repository-working-tree.tar.gz + deployed-source.tar.gz
พร้อม new-handoff-evidence.tar.gz และ SQLite32241events ณ checkpoint; อย่านำจำนวนนี้เป็นปัจจุบัน
เก็บผลเก่าทุก run รวม launcher124 ไว้ ไม่เปลี่ยนผลย้อนหลัง
สำเนาไม่รวม dependencies/build/secret และ systemd unit files ครบชุด จึงยังไม่ใช่ one-command disaster recovery
หลัง review commit เฉพาะรายการที่เกี่ยวข้อง แล้วสร้าง bundle ใหม่: bundleเก่ายังไม่มี reconciliationนี้
