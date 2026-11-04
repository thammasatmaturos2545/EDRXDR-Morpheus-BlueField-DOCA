# EDRXDR–Morpheus–NEXUS — ส่งต่อ DFP / Endpoint Ransomware

วันที่ 5 พฤศจิกายน 2026 (Asia/Bangkok)
สถานะ: เจ้าของงานสั่งพัก งานนี้จัดทำเอกสารส่งต่อเท่านั้น ไม่ใช่คำสั่งเปิดงานทดลองใหม่
เป้าหมายเจ้าของงาน: ส่งระบบใช้งานจริงสิ้นเดือนพฤศจิกายน ไม่ใช่เพียงเดโม; ยังไม่ผ่าน production acceptance

## เริ่มอ่านตรงนี้

VM: saiuser@172.16.30.147
Repo: /home/saiuser/EDRXDR-Morpheus
Branch ที่คาด: work/nexus-exact-ai-v1 ต้องตรวจใหม่ก่อนเขียน
HEAD ล่าสุดก่อนช่วงงานนี้ที่มี operator evidence: cd4437d (ไม่ใช่การยืนยัน HEAD ปัจจุบัน)
อ่าน docs/architecture/EDRXDR-DFP-RANSOMWARE-NEXUS-v1.md,
training/HANDOFF-DFP-APPSHIELD-PROGRESS-20261103.md รวม Follow-up และเอกสารนี้
หากไฟล์เก่าพูดถึง BlueField ให้ใช้คำสั่งเจ้าของงานล่าสุดด้านล่างเป็นขอบเขตปัจจุบัน

เพื่อน/AI ต้องตรวจ Git และ runtime แบบอ่านอย่างเดียวก่อน งานสร้างเอกสารนี้ไม่ได้ทดสอบ VM โดยตรง
ผู้ใช้เป็นผู้รันคำสั่งบน VM และส่ง aggregate results; ห้ามอ้างว่า AI ตรวจเองครบแล้ว
รักษา staged/untracked/WIP ทั้งหมด ห้าม reset/clean, git add ., ย้าย/ลบข้อมูลเดิม หรือ commit งานอื่นปน
เดิมมี staged training/START-HERE-DFP-HANDOFF-20261103.md และ untracked หลายรายการ ต้องดูสถานะจริงใหม่

## ขอบเขตล่าสุดที่เจ้าของงานเลือก

- ไม่ใช้ BlueField ในแนวทางที่จะทำต่อ ไม่เริ่ม RShim/AppShield/DPU/firmware operations
- DFP ทำต่อเฉพาะ Agent003; Agent004 ยังพัก; Network telemetry นอกขอบเขต
- Ransomware เปลี่ยนแนวทางเป็น endpoint file/process behavior ผ่าน Wazuh
- โมเดล AppShield 297 inputs เดิมยังใช้ replay เท่านั้น ห้ามเสียบ FIM แทน feature vector เดิม
- ยังไม่แทน live BERT และ automated response ยังปิด
- ยังไม่ได้เลือกโฟลเดอร์ข้อมูลจริงที่จะป้องกัน เจ้าของงานสั่งพักระหว่างถามเรื่องนี้
- อย่าเริ่ม GPU/training/logging/collector/service ใหม่โดยถือว่า handoff นี้อนุมัติ
- ห้ามส่ง raw logs/datasets/weights/keys/ชื่อบัญชี/ข้อมูลส่วนตัวเข้าแชตหรือ Git

## Runtime ที่มีหลักฐานก่อนส่งต่อ

NEXUS nexus-all-events-prod-3006.service เคยยืนยัน active ที่:
/mnt/nexus-copilot-mQTssj/release-dfp-aed1715-1l2ozb3v/frontend
Model Lab 773 replay observations = DFP 666 + Ransomware 107
DFP Diagnostic เดิม 12 windows / 845 records เป็น frozen diagnostic ไม่ใช่ live detector
History/live-indexer เดิมรักษาไว้ ต้องตรวจสถานะปัจจุบันใหม่
การเปลี่ยน target architecture ออกจาก BERT ไม่เท่ากับมีหลักฐาน runtime cutover

## DFP: งาน CPU ล่าสุด

Private experiment:
/home/saiuser/edrxdr-nvidia-lab-znmqaTGL/dfp-auth-cpu-development-eoriljcd

ข้อมูล journal เดิม 2130 records, 2 บัญชีที่เจ้าของงานรู้จักและระบุว่าใช้งานโดยคน
ไม่ได้แปลว่าทุกเหตุการณ์เป็น benign/authorized ground truth
218 account windows แบ่ง fit 74 / calibration 97 / retrospective check 47
โมเดลใหม่แยกบัญชี 2 ตัว ฝึก CPU 5 epochs; save/reload parity ผ่าน
contract: linux-journal-auth-observed-counts-engineering-0 (6 count features)
ssh_auth_success, ssh_auth_failure, pam_session_open, pam_session_close,
pam_auth_failure, sudo_invocation

Model 1: 57/86/42 windows; loss maxima 4.081069469451904 / 175.5917510986328 / 24.385910034179688
Model 2: 17/11/5 windows; loss maxima 3.3725688457489014 / 32.7076416015625 / 2.365483045578003
Model 2 มีหลาย features เป็นศูนย์ตลอดช่วง; ห้ามถือว่าเป็นหลักฐาน interactive SSH account
Loss เป็น reconstruction error ไม่ใช่ probability หรือข้อสรุปว่าถูกโจมตี
ยังไม่รับรอง source coverage, representative normal baseline หรือ independent detection quality
ยังไม่เลือก threshold ไม่ deploy ไม่แทน BERT
Report SHA256: 13d20a90e92033c7b6d6eacd5b6bb7adb4379f57e2eccc249c3f75a3cef2de79

## DFP observer เดิม — ตรวจสถานะก่อน ไม่เริ่มซ้ำ

เจ้าของงานอนุญาต passive observation สูงสุด 24 ชั่วโมงเพียงรอบนี้
Unit: edrxdr-dfp-auth-prospective-pysjui5a.service
Output: /mnt/nexus-copilot-mQTssj/dfp-prospective-data/dfp-prospective-observation-pysjui5a
เริ่ม 5 พ.ย. 2026 03:59:58.934916 +07; max 86399 วินาที
source deadline ประมาณ 6 พ.ย. 2026 03:59:57.934916 +07; service มีเผื่อหยุด 120 วินาที
ผลล่าสุดที่เคยส่งมี first poll committed แต่ยังไม่มี aggregate completion ล่าสุด

คำสั่งอ่านสถานะ:
python3 -B /mnt/nexus-copilot-mQTssj/dfp-observer-v2-package-w1WF8PGn/dfp-prospective-observer/status.py /mnt/nexus-copilot-mQTssj/dfp-prospective-data/dfp-prospective-observation-pysjui5a

อ่าน journal เดิมเฉพาะ family ที่กำหนด เก็บ pseudonym/normalized records ใน private SQLite
ไม่เก็บ raw message/account/IP ไม่เรียกโมเดล ไม่ฝึก ไม่ใช้ GPU ไม่เขียน Kafka/OpenSearch
RAM512MB CPU25%, 200MiB soft guard, หยุดหาก free disk ต่ำกว่า10GiB
ครั้งแรกล้มเพราะ /home free1.663GiB; ย้าย output ไป /mnt โดยคง guardเดิม ไม่ลดเงื่อนไข
ห้ามขยายเวลา/restart รอบใหม่เอง การพักล่าสุดไม่ได้สั่งหยุด observer ที่อนุญาตไว้
หากเจ้าของงานขอหยุด ให้หยุดเฉพาะ unit นี้ ไม่จับหยุด service อื่น

กิจกรรมทดสอบ FIM และ sudo ในช่วงนี้อาจปนใน observer ต้องบันทึกเป็น experimental activity
ห้ามนำข้อมูลช่วงทดสอบทั้งหมดไปติดป้าย benign หรือใช้เป็น independent quality โดยอัตโนมัติ

## Endpoint Ransomware: ผลจริงที่ยืนยันแล้ว

ก่อนทดสอบ Agent003 มี FIM enabled, frequency43200วินาที(12ชั่วโมง), directory entries2
ไม่มี realtime=yes หรือ whodata=yes ใน config ที่อ่าน; ไม่ใช่ effective coverage proof

ทดสอบชั่วคราวเฉพาะ private directory ด้วย realtime=yes check_all=yes report_changes=no
ไม่เปิด who-data ไม่แตะ BlueField ไม่ใช้ malware
สร้าง plain-text baseline12ไฟล์ แล้ว added4 / modified4 / deleted4
restart เฉพาะ local wazuh-agent ตอนเปิด/คืนค่า มี independent restore timer10นาทีก่อนแก้ config
ผล restore และการอ่านซ้ำยืนยัน config ตรง original bytes และ local agent active

Private probe:
/var/lib/edrxdr-endpoint-probes/probe-8yug2fer
มี original.conf, receipt.json, restored.json, operations.json และไฟล์ทดสอบ
ห้าม paste config/receipt private contents หรือทิ้งหลักฐาน
ต้นฉบับสคริปต์:
/mnt/nexus-copilot-mQTssj/endpoint-fim-v2-*/endpoint-fim-probe/

Manager project=wazuh/service=wazuh.manager รับ Agent003 ครบ12รายการ:
added4 / modified4 / deleted4, realtime12, foreign-agent0, malformed0
ผล narrow synthetic transport เท่านั้น ไม่ใช่ ransomware detection accuracy
การคืนค่าเอา temporary FIM entry ออกแล้ว จึงไม่ได้เปิดเฝ้าพื้นที่ทดสอบต่อเนื่อง

## Offline file-behavior implementation ที่ทดสอบแล้ว

แพ็กเกจ nexus-endpoint-file-behavior-20261105.tar.gz
SHA256 bedeacd8241b5ba4df0cd8fb8dd6e69944f8d90a5bccd2986dddb7014ba77e0d
บน VM แตกไว้ /mnt/nexus-copilot-mQTssj/endpoint-behavior-*/endpoint-file-behavior/
ยังไม่ได้เพิ่ม source นี้เข้า Git/runtime (เอกสารส่งต่อนี้ไม่ได้เปลี่ยนข้อเท็จจริงนั้น)

file_behavior.py: pure offline feature builder, 60/300sec event-time windows
แยก endpoint และ source mode, dedup identical retries, reject identity conflicts
เก็บหลาย operations บนไฟล์เดียวได้ ไม่สร้าง empty windows
รับ strict digest references ไม่รับ raw path/full_log/user
build_windows ไม่มี model/threshold/verdict/network/filesystem IO
shape ของ digest ไม่ใช่ identity proof; live projection/namespace/pseudonym/late-arrival finalization ยังต้องออกแบบรับรอง

14 tests ผ่านบนเครื่อง local และ operator VM
check_probe.py อ่าน bounded current Manager alerts สูงสุด8MiB เฉพาะ probe/Agent003
ยืนยันคืน config และ private projection ใน memory ไม่ save raw values
ผลจริง:
status PRIVATE_PROBE_REPLAY_FEATURE_PASS_NOT_RANSOMWARE_QUALITY
unique_records12, duplicate0, feature_windows1
feature_action_totals added4/deleted4/modified4, source_modes realtime
config_original_bytes_match=true, local_agent_active=true
coverage_accepted=false, ransomware_detection_verified=false, threshold_selected=false
model_invocations0, runtime_changes=false, direct_network_writes0
อ่านเฉพาะ current alert file; ไม่ใช่ historical-retention acceptance

## ทำต่ออย่างไรเมื่อเจ้าของงานกลับมา

1. Read-only Git/runtime/observer status ก่อน รักษา WIP และรอบ observerเดิม
2. ถ้า observerจบ ตรวจ receipt/hash/poll gaps และ workload context ก่อนพิจารณาข้อมูลใหม่
   ไม่ฝึกใหม่หรือเลือก threshold โดยอัตโนมัติ
3. ยืนยันโฟลเดอร์ข้อมูลจริงบน Agent003 และผู้ใช้งาน/งานปกติที่ต้องรองรับ
   ยังไม่เลือกแทนเจ้าของงานและไม่เปิดทั้งไดรฟ์
4. ออกแบบ nuisance/benign bulk-copy/update tests และ controlled file-change scenarios ในพื้นที่ทิ้งได้
   ไม่ใช้ ransomwareจริง; อย่าใช้แค่ synthetic burst12เหตุการณ์ตั้ง threshold production
5. กำหนดว่าจำเป็นต้องผูก process/user ด้วย who-data หรือไม่
   ปัจจุบันยังไม่มี process attribution ที่รับรอง อย่าเปิด audit/whodata โดยไม่มี scoped plan/rollback
6. Freeze source contract, identity, event-time/lateness, coverage, alert budget และ evaluation protocol
   ก่อนเปิด shadow service หรือ deploy NEXUSใหม่
7. ตรวจคุณภาพแยก DFP กับ endpoint ransomware; independent evaluation, false-positive load,
   detection/ingestion latency, retry/restart/rotation/resource limits และ rollback
8. BERT replacement และ automated response ต้องมี acceptance และ explicit cutover scope แยก
   ห้ามอ้างว่าขั้นตอนข้างต้นหรือปลายเดือนเป็นหลักฐานว่าระบบพร้อมแล้ว

## คำสั่งตรวจเริ่มงานแบบอ่านอย่างเดียว

cd /home/saiuser/EDRXDR-Morpheus || exit 1
GIT_OPTIONAL_LOCKS=0 git branch --show-current
git --no-pager log -5 --oneline
GIT_OPTIONAL_LOCKS=0 git status --short
git --no-pager diff --check
systemctl --user show nexus-all-events-prod-3006.service --no-pager -p ActiveState -p SubState -p WorkingDirectory
systemctl show edrxdr-dfp-auth-prospective-pysjui5a.service --no-pager -p LoadState -p ActiveState -p SubState -p Result
docker ps --format 'table {{.Names}}\t{{.Status}}'

อย่าอ่าน environment values/keys/raw log contents ออกแชต
รายชื่อ path ข้างต้นเป็น operational metadata; private artifacts อยู่ VM เท่านั้น
เอกสารนี้ไม่ใช่การอนุมัติเริ่ม collector/training/runtime ใหม่ ไม่ push และไม่รับรองส่งงานเสร็จ
