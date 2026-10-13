> Latest checkpoint: see training/HANDOFF-DEMO-CLOSE-20261014.md. Run d20261013t181858-e1bbae7e: 2/2/2, container and launcher exit 0; API and operator UI observation verified. Earlier exit 124 remains historical.

# ส่งต่อ EDR/XDR: Severity flow demo — 13 ตุลาคม 2026

## อ่านส่วนนี้ก่อน

เอกสารนี้ supersede สถานะ “ยังไม่ได้ทำ continuous demo” ในเอกสารส่งต่อก่อนหน้า สำหรับ run `d20261013t164314-c1b4d787` เท่านั้น ผลยืนยันคือ bounded near-real-time microbatch ไม่ใช่บริการ production 24/7 และไม่ใช่ hard real time

VM `saiuser@172.16.30.147` repo `/home/saiuser/EDRXDR-Morpheus`
Branch `work/bluefield-shadow-quarantine` HEAD ก่อนอัปเดตเอกสาร `cb514aa52bd742db9902527caaf64dc62fa14a12`
Working tree มีงานที่ยังไม่ commit ดู `training/evidence/severity-flow-d20261013t164314-c1b4d787/git-status-before.txt` และ git status ใหม่เสมอ ห้าม reset/clean หรือเขียนทับงานเพื่อน

## ผลที่เสร็จและมีหลักฐาน

1. Windows Agent ย้ายจาก Manager 192.168.218.130 มา 172.16.30.147 สำเร็จ; Manager แสดง ID004 windows-agent Active สำรอง config/key อยู่ใต้โฟลเดอร์ติดตั้ง Agent บน Windows (backup-edrxdr-*); ห้ามนำ client.keys เข้า Git/แชท
2. สร้างไฟล์ข้อความไม่มี executable content ชื่อ EDRXDR-demo-20261013-234421.txt ใน Common Startup ที่ Agent เฝ้าดูอยู่
3. Wazuh alert `1791909861.2210586`, Agent004, rule554 level5, event added เวลา 2026-10-13T16:44:21.854Z (23:44:21.854 ไทย)
4. Worker รับข้อมูลใหม่หลัง source boundary partition0 offset17193 ไม่ย้อน backlog; captured/scored/indexed อย่างละ3 (offset17193–17195)
5. Severity ผ่าน frozen Morpheus GPU pipeline จริง โดย batch1 หนึ่งรายการใช้6.9726วินาที batch2สองรายการใช้1.4946วินาที จาก audit batch_complete; ไม่ใช่ benchmark ทั่วไป
6. Raw Kafka envelope ของ offset17193 ตรวจ alert ID, agent, filename, UID และ SHA256 ตรงกับผลโมเดล/audit สำเร็จ ส่วนอีก2รายการไม่ได้ตรวจเจาะจงว่ามาจาก Windows
7. API total=3/shown=3 และภาพ Dashboard แสดงทั้ง3 พร้อม polling ทุก3วินาทีหลัง request จบ; lag capture/score/index เป็น0 ณ snapshot เวลา23:47 ไม่ใช่การรับประกันตลอดเวลา
8. worker_stopped เวลา23:52:30.695 ไทย มี counts3/3/3; ผู้ใช้ส่ง docker ps ไม่พบ container รอบนี้ และ nvidia-smi เวลา23:53:02 แสดง0MiB ไม่มีprocess

Launcher exit evidence: {"console-20261013T164314.txt.exit-code": "124"}
ต้องแยก “หยุดและคืนGPUแล้ว” จาก “ยืนยันexit0แล้ว” ห้ามสร้างไฟล์exit-codeย้อนหลังเอง

## ตัวตนหลักฐาน

- Run `d20261013t164314-c1b4d787`
- UID `036d8161ba1ac286f7ebc96fc6629b2b7aa658e932b3080eec8d10a0b09cea71`
- Raw SHA256 `949e795c9c161fa6ef10ba1742e558f45fa885c856e98e031bc3ca73b3abddfb`
- Source wazuh-alerts partition0 offset17193
- Document ID `202b1c7f3d1250b56dc053f95ba17ff819752d61a03dfa7ff74301143a27847b`
- Model `wazuh-severity-context-v2-balanced-20261008T190719Z-1398863`
- Engine SHA256 `64ef3bad1a0c4e60de34681697db8fec748a31de450dd9df1e8b9825e1afd9ca`
- Score0.003172682598233223 threshold0.5 label low_severity; ไม่ใช่หลักฐานว่าปลอดภัยหรือวัดความแม่นยำได้จากเหตุการณ์เดียว
- production_ready=false; automated_response_allowed=false; Behavioral ไม่ได้รันใน worker นี้

## เวลาและการตีความ

API capture-to-score: 9752ms สำหรับoffset17193, 3492msสำหรับ17194,3491msสำหรับ17195
Audit captured-after-Kafka-ACK ถึง index ACK: ประมาณ10.04/5.02/6.02วินาทีตามลำดับ จุดเริ่มต่างจาก captured_at_utc ในเอกสาร อย่ารวมเป็น metric เดียว
UI browser-first-seen ที่เห็นในภาพเป็นเวลาของ browser session และขึ้นกับ clock sync ไม่ใช่หลักฐาน end-to-end latency ที่เที่ยงตรง
indexed_at ในเอกสารเป็น index request start; เวลายืนยัน persistence อยู่ audit ack_at_utc

## เส้นทางและไฟล์สำคัญ

Windows → Wazuh Manager → live Kafka wazuh-alerts → run-scoped raw topic บน replay Kafka → Morpheus Severity → run-scoped output topic → replay OpenSearch → /api/demo → /demo

- `demo/worker.py`, `demo/run.sh`, `demo/compose.yml`, `demo/start-ui.sh`, `demo/test_worker.py`, `demo/README.md`
- `frontend/src/app/demo/page.tsx`, `frontend/src/app/api/demo/route.ts`, `frontend/src/lib/demo.ts`, `frontend/tests/demo.cjs`
- UI port3001 สร้าง build แยกใต้ ~/edrxdr-demo-ui.*; ไม่แก้ build/port3000
- Worker container `edrxdr-demo-d20261013t164314-c1b4d787` ถูกลบเมื่อจบรอบ (--rm)
- Index `demo-severity-d20261013t164314-c1b4d787`
- Topics indexชื่อข้างต้นต่อท้าย -raw/-output; groupsต่อท้าย -capture/-score/-indexer
- Evidence ต้นฉบับ `~/edrxdr-demo-runs/d20261013t164314-c1b4d787/`: run.json, audit.jsonl, console log, windows-origin-verification.json, raw-verification-*.json
- สำเนาที่ควรเข้าGit `training/evidence/severity-flow-d20261013t164314-c1b4d787/` มีเฉพาะ audit/state/verification/hash inventory ไม่รวม raw payload หรือ key
- Topic retention24ชั่วโมง cap64MiB ไม่ได้ลบ topic/index อัตโนมัติ; rawอาจหมดอายุก่อนวันนำเสนอ ให้รักษา verification/evidence และซ้อมรอบใหม่

## การติดตั้ง/แก้ไขที่ทำไป

- แพ็ก `/tmp/edrxdr-severity-flow-demo-20261013.tar.gz` SHA256 `6857b3ea25c2e7c684e244f4aa8dc5ae311520e0448b4715cbd58bd5bc70accb`
- apply.py ตรวจHEAD/126source guards เพิ่ม10ไฟล์ ไม่ทับdirtytree ไม่เริ่มGPU
- บนVMผ่าน worker11tests, Shadow23tests, TypeScript, ESLint, shell syntax, frontend demo/overview/Shadow20/BlueFieldShadow10/history7 และregression7groups
- Validationเดิม `/tmp/edrxdr-flow-install-StQsBRuy/validation-20261013T125448032198Z.txt` ผู้ใช้copyไป `training/evidence/severity-demo-install-20261013/` แล้ว
- start-ui build/typecheckผ่านบนVM และเว็บReady port3001
- แก้ YAML tmpfs จากรายการไม่quoteเป็น `tmpfs: ["/tmp:rw,size=1g"]` หลังรอบแรกสร้างcontainerไม่สำเร็จ; backup `training/evidence/demo-tmpfs-fix-20261013T130109Z/`
- เปลี่ยนreservation2รอบพร้อมbackup ล่าสุด `training/evidence/demo-reservation-20261013T163343Z/`
- Source runtime/adapter hash validation และ model parity ไม่ได้ข้าม

## GPU และบริการร่วม

สิทธิ์รอบล่าสุดเฉพาะ13ต.ค.23:00–14ต.ค.01:00ไทย launcher cutoff14ต.ค.00:55; max600วินาทีต่อsession UUID GPU-61a1dd9b-a3c2-86dc-15b9-1277b5b949bb
สิทธิ์นี้ไม่ครอบคลุมวันที่16 ต้องจองใหม่ก่อนซ้อม/เดโม และปรับlauncherพร้อมหลักฐานการจอง ห้ามขยายเวลาเอง
BlueField publisherคงinactive/dead/disabled ไม่ได้ซ่อมlive publisher
Morpheus live containerเก่าedrxdr-morpheusหยุดจากCUDA errorวันที่1ต.ค.; workerเดโมแยกต่างหาก ไม่ต้องเปิดเก่าเพื่อให้statusเขียว
ห้ามลงdriver/reboot/แก้interface/หยุดshared stackหรือprocessทีมอื่น

## การจัดไฟล์ก่อนหน้า

ย้าย7รายการ backup/package/dashboard-review/handoff เข้า `~/EDRXDR-Archive/20261012T135349958660Z/` ไม่ลบ ไม่คืนพื้นที่ มีmanifest.jsonและorganize_edrxdr_20261012.py ไม่ต้องrestoreเพื่อทำงานต่อ
เอกสารbackupอยู่ `~/EDRXDR-Archive/documentation-backups/`, frontendbackupอยู่ `~/EDRXDR-Archive/frontend-backups/`
Model volume edrxdr-model-output mount /models แบบreadonly; dataset volumeที่เคยสำรวจ edrxdr-dataset ต้องตรวจpathจริงก่อนใช้ ห้ามprune volumes
รักษาไฟล์raw-verificationบนVMอย่างจำกัดสิทธิ์ ไม่รวมในGitแบบเหมา

## งานต่อเรียงลำดับ

1. ตรวจterminallauncherเดิม/console logเพื่อหาสาเหตุไม่มีexit-code อย่ารันGPUใหม่เพียงเพื่อสร้างexit0
2. เก็บAPI snapshotและภาพ/วิดีโอเดโมในพื้นที่หลักฐานที่เหมาะสม ระบุsnapshotเวลา ไม่อ้างผู้ตรวจscriptได้ดูUIเอง
3. Review diff และcommitโค้ด demo/frontend/sink แยกตามงาน พร้อมtests; commitเอกสารนี้อย่างเดียวไม่ทำให้cloneใหม่ได้โค้ดเดโมทั้งหมด ตรวจ staged paths ก่อนทุกครั้ง
4. ซ้อมรอบใหม่ในreservationใหม่ ใช้event markerใหม่หลังworker_ready ยืนยันidentity/hash/API/UIอีกครั้ง เก็บlog exitและshutdown; ทดสอบrestart/resume/failure recoveryแบบแยกก่อนกล่าวอ้าง
5. หน้าเว็บควรอธิบายworker stopped/staleได้ แยกGPU detected/Fabric N/A/livecontainerเดิมกับworker demo แสดงagent/pathผ่านการออกแบบcontractที่ไม่รั่วrawหากจะเพิ่ม
6. ทำสไลด์/วิดีโอfallbackสำหรับวันที่16 อธิบายbounded microbatch ไม่ใช่24/7 production; modelqualityยังต้องประเมินอิสระ; AEไม่มีscoreไม่เท่ากับปลอดภัย
7. หลังเดโม: long-running lifecycle, capacity/latency/soak, authentication, access control, retention/cleanup, backup restore และobservability
8. BlueField live, operator replay authorization และproduction sink integrationยังเป็นงานแยก; step8มี123tests/preflightผ่านแต่replay_authorized=false
9. ไฟล์ทดสอบWindowsยังไม่มีหลักฐานว่าลบแล้ว ลบเฉพาะไฟล์markerเมื่อเก็บหลักฐานครบ การลบอาจสร้างalertใหม่

## คำสั่งรับช่วง (อ่านก่อนเริ่มGPU)

```bash
cd ~/EDRXDR-Morpheus || exit 1
TZ=Asia/Bangkok date -Is
git branch --show-current
git log -3 --oneline
git status --short
cat training/HANDOFF-SEVERITY-FLOW-20261013.md
cat demo/README.md
cat demo/run.sh
docker ps --format 'table {{.Names}}\t{{.Status}}'
nvidia-smi
```

เปิดUIโดยไม่เริ่มGPU: `bash demo/start-ui.sh` (ถ้าport3001ใช้อยู่ให้ตรวจprocessก่อน ไม่killเหมา)
เปิดผลเดิม: `http://172.16.30.147:3001/demo?run=d20261013t164314-c1b4d787` ถ้าOpenSearch/index/UIยังอยู่
เริ่มworkerเฉพาะช่วงจองที่ตรวจแล้ว: `bash demo/run.sh` ใช้runIDใหม่ที่แสดง; เหตุการณ์ก่อนboundaryจะไม่ถูกรับ
UIและworkerอยู่คนละterminal หยุดเฉพาะตัวที่เราเปิด ไม่compose downทั้งstack

## ขอบเขตการตรวจเอกสารฉบับนี้

Updaterอ่านauditและorigin reportบนVMจริง ตรวจ3occurrencesและworker_stopped และเก็บhashsource ณ เวลารัน รายงานUI/API/GPU shutdownมาจากoutputและภาพที่operatorส่งในแชท ไม่ใช่การทดสอบใหม่โดยupdater ไม่มีการเปิดGPU/เปลี่ยนบริการ/commit/pushในscriptนี้
