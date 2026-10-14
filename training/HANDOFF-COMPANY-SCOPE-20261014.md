# ส่งต่องาน EDR/XDR: สถานะตามโจทย์ SIAM AI และวิธีรับช่วง

อัปเดตจากหลักฐานถึง 14 ตุลาคม 2026 (Asia/Bangkok) สำหรับประชุมความก้าวหน้า onsite วันที่ 16 ต.ค. กลุ่มละไม่เกิน 1 ชั่วโมง ให้นำ notebook และระบบที่ทำอยู่ไปตรวจรายละเอียด ไม่ใช่การประกาศว่าจบสโคปทั้งหมด

## 1. เริ่มอ่านตรงนี้

- VM: `saiuser@172.16.30.147`, hostname `oa-hgx-h100-bu-02`
- Repository: `/home/saiuser/EDRXDR-Morpheus`
- Branch: `work/bluefield-shadow-quarantine`
- Checkpoint ก่อนเอกสารนี้: `142fc7692ea0068054e184b38e0805555aa83210` (`142fc76`)
- ผลล่าสุด: Windows event จริงผ่าน Wazuh → Kafka → Morpheus GPU Severity → Kafka output → OpenSearch → Dashboard; รอบล่าสุด 5/5/5 และปิดสำเร็จ
- Git clean ตามผลที่ผู้ปฏิบัติงานส่งหลัง commit แต่ต้องตรวจใหม่ทุกครั้งที่รับงาน
- เอกสารนี้จะอยู่ใน commit ถัดไปของชุด handoff ให้ดู `git log -1` และ receipt ของ bundle ใหม่เพื่อทราบ final HEAD
- ห้าม reset/clean, force checkout, restore archive หรือเขียนทับงานค้างเพื่อให้ตรงเอกสาร

## 2. โจทย์บริษัทและฐานการประเมิน

อ้างอิงเอกสาร `SIAM.AI - BU.pdf` จำนวน 8 หน้า ที่ผู้ใช้ให้ตรวจในบทสนทนา:

- หน้า 2: โครงการพัฒนาระบบ EDR/XDR อัจฉริยะบน SIAM AI Cloud ด้วย Wazuh และ NVIDIA Morpheus; ระยะโครงการที่เอกสารระบุ 12 ม.ค.–30 พ.ย. 2569
- หน้า 3: Deploy Wazuh, Integrate Morpheus, AI pipeline สำหรับ Big Security Data ด้วย GPU/DPU และ use case เฉพาะ SIAM AI
- หน้า 5: Wazuh Implementation, Logs/FIM/Vulnerability Detection, Morpheus Streaming AI, Advanced Rules/Alerts จาก AI และ Automatic Response Playbook เช่น Block IP/Isolate Host
- หน้า 6: Input จาก endpoint/network/logs/telemetry → collection → AI analysis → decision making → security alerts/incident reports/response actions

PDF ต้นฉบับอยู่ที่เครื่องผู้ส่ง `C:\Users\bagel\Downloads\SIAM.AI - BU.pdf`; ไม่ได้รวม PDF ใน Git/bundle โดยชุดอัปเดตนี้ ให้ส่งสำเนาผ่านช่องทางที่บริษัทอนุญาตหากผู้รับยังไม่มีไฟล์ SHA256 ของเอกสารที่ใช้อ้างอิงอยู่ในหลักฐานการอัปเดตนี้

คำว่า “ยังไม่ยืนยัน” ด้านล่างหมายถึงหลักฐานที่ตรวจมายังไม่พอ ไม่ได้ยืนยันว่าไม่มีโค้ดหรือไม่มีการตั้งค่า ต้องตรวจ repo/config และผลทดสอบก่อนพัฒนาเพิ่ม

## 3. ตารางเทียบสโคปกับงานจริง

| ข้อกำหนด | ทำแล้วและหลักฐาน | สิ่งที่ยังเหลือ |
|---|---|---|
| Wazuh implementation | Manager และระบบประกอบบน VM; Linux/Windows Agent เคยรายงาน Active | ยืนยันขอบเขต endpoint บริษัทจริง วิธีติดตั้งซ้ำ ดูแล และรับรองความครอบคลุม |
| Log collection | Wazuh alerts ผ่าน Kafka/pipeline จริง | ตรวจแหล่งข้อมูลที่บริษัทยอมรับว่าครบ เช่น network devices/cloud logs; แยก data source ที่เชื่อมแล้วจากแผน |
| FIM | Windows file-added Rule 554 มีต้นทาง/raw hash ตรงผลบนเว็บ | กำหนดโฟลเดอร์สำคัญ/เหตุการณ์ที่บริษัทต้องการ ทดสอบ changed/deleted และกรณีปกติ |
| Vulnerability Detection | มี Wazuh เป็นพื้นฐาน | ยังไม่มีหลักฐาน inventory/vulnerability workflow ที่ตรวจยืนยันในรอบนี้ ต้องตรวจสถานะและผลก่อนอ้างว่าเสร็จ |
| Morpheus streaming AI | Bounded microbatch Severity GPU ผ่านจริง 5/5/5 | บริการต่อเนื่อง, restart/recovery, backlog/load และการนำไปใช้จริง |
| Advanced Rules/Alerts จาก AI | มี score, threshold, label และ Dashboard | ยังไม่ยืนยันกฎตัดสินใจที่เปลี่ยนผล AI เป็น security alert/incident และใช้งานจริงครบวงจร |
| Automatic response | ปิด automated response; มีงาน operator guard บางส่วน | ยังไม่มีหลักฐาน playbook Block IP/Isolate Host ครบสายพร้อมสิทธิ์ ขอบเขต rollback และ audit ในสภาพแวดล้อมทดสอบ |
| Use case เฉพาะ SIAM AI | ใช้ Windows file event พิสูจน์เส้นทางข้อมูล | เลือกภัย/ทรัพย์สินที่เกี่ยวกับบริษัท กำหนด expected results/acceptance criteria; เพิ่มไฟล์ข้อความยังไม่พิสูจน์การตรวจจับโจมตี |
| Big Data / GPU-DPU | H100 inference จริง; BlueField มี isolated review | ยังไม่มี throughput/load/data-loss/latency benchmark หรือ live DPU integration ที่ครบ |
| Alerts/incident reports | Wazuh alerts และผล Severity แสดงบนเว็บ | รายงาน incident ที่มีเวลา หลักฐาน สาเหตุ ผลกระทบ การตัดสินใจ/response; เอกสาร handoff ไม่ใช่ incident report |

อย่าระบุเปอร์เซ็นต์สำเร็จรวมโดยไม่มีน้ำหนักและเกณฑ์รับงานที่ตกลงกัน การรันโมเดลได้ไม่เท่ากับพิสูจน์ว่าตรวจจับได้ดีกว่าเดิม

Automation และ Big Data เป็นงานในสโคปบริษัทที่ยังไม่ครบ ไม่ใช่งานนอกสโคป ส่วน AE/Behavioral และ BlueField เป็นแนวทางที่ทีมเลือกใช้ PDF นี้ไม่ได้บังคับชื่อโมเดล AE หรืออุปกรณ์ BlueField รุ่นเฉพาะ ให้ยืนยันกับบริษัทว่าต้องส่งผลลัพธ์ใดและเทคโนโลยีใดเป็นข้อบังคับเพิ่มเติม

## 4. ผล live ล่าสุดและข้อจำกัด

- Run: `d20261014t055117-9fd3415a`, เริ่ม 14 ต.ค. 12:51:17 ไทย; หยุด 13:00:37
- Source `wazuh-alerts`, partition 0, offsets 25727–25731; captured/scored/indexed 5/5/5
- UI แสดง 2 → 3 → 5 รายการระหว่างรอบ และเปลี่ยนเป็นผลย้อนหลังหลังหยุด; ภาพอยู่ในบทสนทนา ยังไม่มีวิดีโอที่ยืนยันว่าเก็บไว้
- Windows Agent `004`, alert `1791957206.906202`, Rule 554 Level 5, event `added`
- ไฟล์ `C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Startup\EDRXDR-demo-20261014-125326-f559452b.txt` สร้าง 12:53:26
- Event UID `333018ff5d1a010d8c6489f8112b90b00b96046b616ba572557641e0a3ef29e6`, offset 25729
- Raw SHA256 `6bc8749336414c6c3500da2f3f46f99dc7346e0e32e3d40802758d5fc72cacd8` ตรวจจาก Kafka envelope ตรง capture/scored/indexed/API
- Model `wazuh-severity-context-v2-balanced-20261008T190719Z-1398863`; threshold 0.5
- Engine SHA256 `64ef3bad1a0c4e60de34681697db8fec748a31de450dd9df1e8b9825e1afd9ca`
- Container/launcher exit 0, OOMKilled=false, stop_confirmed=true, reconciliation_required=false; consumer cleanup ครบ
- ผลตรวจ GPU 13:02:49 แสดง 0 MiB และไม่มี compute process ค้าง เป็น snapshot หลังรอบ ไม่ใช่การรับรองสถานะปัจจุบัน
- เป็นหลักฐาน live normal-completion หลังแพตช์ supervisor ใหม่ ยังไม่ใช่ failure-injection validation
- Capture → score ของ Windows event ประมาณ 4225 ms รวมการรอ ไม่ใช่ inference time ล้วน; Index request ไม่ใช่ ACK; browser first-seen ไม่ใช้คำนวณ pipeline latency
- Severity-only, bounded near-real-time microbatch, automated response OFF, production_ready=false; low_severity ไม่ใช่คำรับรองว่าปลอดภัย

## 5. Checkpoint และประวัติที่ต้องรักษา

| Commit | ความหมาย |
|---|---|
| 5701979 | Detached supervisor และรอบ 2/2/2 ที่ container/launcher exit 0 |
| 181b5f0 | Handoff/evidence ของรอบดังกล่าว |
| cfecdcf | ตรวจ deadline/สถานะหลัง stop และ reconciliation; offline tests 14 กรณี |
| 8f737f9 | UI แยก historical/heartbeat และแก้ latency; regression และภาพ UI |
| 506fbea | Handoff รวมก่อนซ้อมรอบใหม่ |
| 142fc76 | เก็บผลซ้อม 5/5/5, reservation, origin/API/shutdown และเอกสาร |

รอบ `d20261013t164314-c1b4d787` ผ่าน 3/3/3 แต่ launcher exit 124 ต้องเก็บผลนี้ไว้ รอบ `d20261013t181858-e1bbae7e` ผ่าน 2/2/2 และ exit 0 เป็นอีกชุดหลักฐาน ห้ามแก้ผลเก่าให้กลายเป็นผ่านด้วยผลรอบใหม่

## 6. ที่อยู่หลักฐานและโค้ด

Paths ในรายการนี้อ้างอิง root `/home/saiuser/EDRXDR-Morpheus`:

- `training/HANDOFF-REHEARSAL-20261014.md`: รายละเอียดผล 5/5/5
- `training/HANDOFF-NEXT-20261014.md`: ประวัติระบบและงานก่อนรอบล่าสุด
- `training/evidence/rehearsal-d20261014t055117-9fd3415a/`: audit, console, run, exit/container/supervisor, API, sanitized Windows origin, GPU snapshot, SHA256 manifest
- `training/evidence/demo-reservation-20261014T054939042236Z/`: สิทธิ์จองรอบนี้และ run.sh ก่อนเปลี่ยนเวลา
- `training/evidence/demo-detached-d20261013t181858-e1bbae7e/`, `training/evidence/demo-close-20261014/`: รอบ 2/2/2
- `training/evidence/severity-flow-d20261013t164314-c1b4d787/`: รอบ Windows เดิมที่ launcher exit 124
- `training/evidence/supervisor-followup-20261013T190745844629Z/`: offline tests
- `training/evidence/demo-presentation-20261013T191242957316Z/`: UI regression
- `demo/run.sh`, `demo/supervise.py`, `demo/worker.py`, `demo/compose.yml`: launcher/worker
- `frontend/src/app/demo/page.tsx`, `frontend/src/app/api/demo/route.ts`, `frontend/src/lib/demo.ts`: UI/API/parser
- `/home/saiuser/edrxdr-demo-runs/d20261014t055117-9fd3415a/`: ต้นฉบับนอก Git รวม raw-origin JSONL; ห้ามเผยแพร่ raw/secrets โดยไม่ตรวจ

GPU snapshot มี trailing whitespace ที่มาจาก nvidia-smi และถูกเก็บแบบเดิมเพื่อรักษา hash ตอน commit ยกเว้น blank-at-eol เฉพาะไฟล์นี้ ห้าม trim ทุก evidence file แล้วอ้างว่า byte/hash เดิม

## 7. วิธีรับงานต่อ — แยกเครื่องให้ชัด

### Windows PowerShell: เชื่อมต่อ VM

```powershell
ssh saiuser@172.16.30.147
```

### VM H100: ตรวจแบบอ่านอย่างเดียวก่อน

```bash
cd /home/saiuser/EDRXDR-Morpheus || exit 1
TZ=Asia/Bangkok date -Is
git branch --show-current
git log -5 --oneline
git status --short
cat training/HANDOFF-COMPANY-SCOPE-20261014.md
systemctl show edrxdr-bluefield.service --no-pager -p ActiveState -p SubState -p UnitFileState
docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}'
ss -ltnp | grep ':3001' || true
docker exec wazuh-wazuh.manager-1 /var/ossec/bin/agent_control -l
```

ส่งผลให้แชทรับงานต่อ ไม่คัดลอกคำสั่งแก้ reservation เก่าทันที ถ้า Git เปลี่ยนหรือ dirty ต้องอ่านงานนั้นก่อน

### VM H100: เปิดเว็บโดยไม่เริ่ม GPU

ถ้าพอร์ต 3001 ยังไม่ถูกใช้งาน:

```bash
cd /home/saiuser/EDRXDR-Morpheus || exit 1
bash demo/start-ui.sh
```

สคริปต์ build frontend แยก รอ Ready และเปิดแท็บไว้ ถ้ามี process ใช้พอร์ตอยู่ให้ตรวจเจ้าของ ไม่ kill ตามหมายเลขพอร์ตหรือ prefix

### Windows PowerShell อีกแท็บ: tunnel

```powershell
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -L 127.0.0.1:3001:127.0.0.1:3001 saiuser@172.16.30.147
```

ใส่รหัสแล้วนิ่งเป็นปกติ เปิดแท็บค้างไว้ ไม่เปิด tunnel ซ้ำถ้าอันเดิมทำงาน จาก browser Windows เปิด:
`http://127.0.0.1:3001/demo?run=d20261014t055117-9fd3415a`

`/demo` เป็นหน้าเว็บ; `/api/demo` เป็น JSON; 127.0.0.1 บน Windows หมายถึง Windows จึงต้องมี tunnel

### VM: offline checks เมื่อแก้โค้ด

```bash
cd /home/saiuser/EDRXDR-Morpheus || exit 1
test_env=$(mktemp -d /tmp/edrxdr-review-XXXXXXXX)
python3 -m venv --without-pip "$test_env/venv"
"$test_env/venv/bin/python" -B -m unittest discover -s demo -p 'test_supervise*.py' -v
cd frontend
node tests/demo.cjs
npm run typecheck
```

ตรวจ dependency เดิมก่อน ไม่ติดตั้งลง shared environment โดยไม่จำเป็น ผล offline ไม่แทนผล integration

## 8. วิธีซ้อมใหม่และเกณฑ์ผ่าน

1. ยืนยันวัน/เวลา/UUID GPU ที่ได้รับสิทธิ์ล่าสุด ตั้ง cutoff เผื่อหยุดและตรวจผล พร้อม backup reservation/launcher; ตรวจไม่มีงานทีมอื่นก่อนเริ่ม
2. เปิดเว็บและ tunnel ก่อน เริ่มบันทึกหน้าจอ ใช้ run ใหม่ เพราะ run เก่าอาจมี retained container และ Kafka retention gap
3. เริ่ม `bash demo/run.sh` เฉพาะในช่วงที่ได้รับอนุญาต คำสั่งนี้ใช้ GPU ต่างจาก start-ui.sh
4. เปิดอีกแท็บตรวจ exact container ของ Run ID และ log จนเห็น worker_ready ก่อนสร้าง endpoint event ที่ได้รับอนุญาต
5. ใช้ Windows PowerShell Administrator สร้างไฟล์ข้อความทดสอบชื่อใหม่ใน monitored path ที่ตกลงไว้ เก็บชื่อ/path/creation time อย่าสร้างสคริปต์ executable หรือใช้การโจมตีจริงเพื่อเดโม
6. ตรวจ Wazuh agent/rule/path/alert ID และ raw hash ให้ตรง source offset/UID ใน capture → scored → indexed → API/UI; จำนวนรวมอย่างเดียวไม่พอเพราะมี background events
7. เก็บภาพระหว่างจำนวนเพิ่ม ไม่ใช้ภาพย้อนหลังอ้างว่า live; source high offset รับเหตุการณ์หลัง boundary ไม่ย้อน backlog
8. ปล่อย bounded run จบเอง แล้วตรวจไฟล์ `console-TIMESTAMP.txt.exit-code` และ `.supervisor.json`; `.launch.exit-code` เป็นผลเริ่ม container ไม่ใช่ผลจบรอบ
9. ตรวจ container exited/Running=false/ExitCode=0/OOMKilled=false, stop_confirmed=true, reconciliation_required=false และ GPU process ของรอบไม่ค้าง
10. เก็บหลักฐานก่อน retention หมด อัปเดตเอกสาร/commit/bundle และตรวจ SHA256 สำเนานอก VM เก็บผล error/124 ตามจริง

worker_stopped อย่างเดียวไม่ยืนยัน process exit; GPU memory ที่ยังค้างขณะ worker กำลังรอ event ก่อนจบรอบไม่ได้แปลว่า leak โดยอัตโนมัติ

## 9. แผนก่อนประชุมวันที่ 16

- Reply นัดหมายเวลา onsite และจอง Siam AI ครอบคลุมการเตรียม/ประชุมไม่เกิน 1 ชั่วโมง; ยังไม่มีเวลานัดเฉพาะที่ยืนยันใน handoff นี้
- ใช้ notebook ที่นำไปจริง ทดสอบ network/VPN/SSH/tunnel และ Windows Agent ในเครือข่าย onsite
- เตรียม walkthrough: ผัง → event ต้นทาง → AI result → หลักฐานจับคู่ → shutdown → งานค้าง
- เตรียม source, logs, ภาพ และวิดีโอสำรองแบบเปิด offline; bundle ไม่ใช่ระบบ runnable ครบโดยไม่พึ่ง VM
- เตรียมข้อมูลโมเดล: dataset/label/split/metric/threshold/model artifact และ baseline Wazuh ที่ตรวจยืนยันได้ อย่าแต่งผลที่ยังไม่มี
- นำตารางสโคปในเอกสารนี้ให้อาจารย์ช่วยประเมินปริมาณงานและลำดับที่ต้องทำต่อ
- แบ่งเวลาเสนอแนะ: ภาพรวม 5 นาที, เดโม 15, ตรวจโค้ด/โมเดล/หลักฐาน 25, งานค้าง/ข้อเสนอแนะ 15

## 10. งานที่เหลือทั้งโครงการ

ลำดับแนะนำต่อไปนี้เป็นแผนงาน ไม่ใช่การรับรองว่าสามารถทำครบก่อนวันที่ 16:

1. ตกลง use case และเกณฑ์รับงานกับบริษัท: แหล่งข้อมูล,ภัย,ผลที่ต้องได้, latency/throughput และผู้อนุมัติ response
2. ตรวจและพิสูจน์ Vulnerability Detection ที่มีอยู่ เก็บ inventory/CVE mapping/ผลแจ้งเตือนตามขอบเขตที่ตกลง
3. ประเมินคุณภาพ AI ด้วยข้อมูลแยกประเมินที่เหมาะสม precision/recall/FP/FN และเปรียบเทียบ Wazuh baseline การมี score ไม่ใช่หลักฐานเพิ่มประสิทธิภาพ
4. ทำ decision rules ที่ใช้ AI+บริบทเป็น security alerts/incident reports พร้อมเหตุผล/dedup/audit
5. พัฒนา response playbook ใน isolated test environment พร้อม allowlist/approval/rollback/verification ห้ามเปิด response บน shared VM เพียงเพื่อให้เดโมครบ
6. ทำ long-running pipeline, restart/recovery/idempotency และ reconcile กรณีส่งผลแล้วแต่ไม่ได้ ACK; ทดสอบ SIGTERM/Docker outage/stop failure/evidence-write failure อย่างควบคุม
7. ทำ load benchmark throughput/latency percentiles/resource/backlog/loss พร้อม baseline; ทบทวน GPU/DPU requirements กับบริษัท
8. ถ้าเลือก Behavioral/AE/BlueField ให้เชื่อมและทดสอบ nullable schema อย่างถูกต้อง; live normalizer เดิมเคยมี null→zero coercion จึงห้ามส่ง schema ใหม่เข้าทางเดิมโดยไม่ตรวจ
9. Operator authoritative replay/recovery, retention/cleanup, security controls และ backup/restore model/runtime ยังไม่เสร็จ

## 11. ข้อจำกัดและไฟล์ที่จัดเก็บไว้

- Latest reported GPU reservation: 14 ต.ค. ถึง 14:00 ไทย, launcher cutoff 13:55 เป็นเวลาของรอบนี้เท่านั้น ให้ตรวจสิทธิ์ใหม่ก่อนรันครั้งหน้า
- GPU UUID `GPU-61a1dd9b-a3c2-86dc-15b9-1277b5b949bb`
- BlueField ต้อง inactive/dead/disabled; ห้ามแก้ driver/network interface, หยุด shared stack/process ทีมอื่น หรือเปิด automated response
- Morpheus service เก่าที่ exited ไม่ใช่ demo container; ห้าม restart เพื่อให้หน้า status เป็นสีเขียว
- BlueField review เดิมมี 6 archived records ผ่าน transport/normalization/persistence แยก ยังไม่ใช่ live DPU flow; operator sink มี offline/preflight ไม่เท่ากับ replay จริง
- วันที่ 12 ต.ค. ย้าย backup 3 ไฟล์, package zip 1, dashboard-review 2 โฟลเดอร์ และ EDRXDR-HANDOFF เข้า `/home/saiuser/EDRXDR-Archive/20261012T135349958660Z/` มี manifest/restore script; ไม่ลบ ไม่คืนพื้นที่ ไม่เปลี่ยน service และไม่ย้าย repo หลัก/personal worktree/volumes
- ไม่ต้อง restore archive เพื่อรับช่วง ไฟล์ test .txt บน Windows ยังไม่ได้ยืนยันว่าลบ หากจะลบให้ระบุ exact path และคาดว่าจะเกิด deletion alert

## 12. Backup และการส่งต่อ

Bundle ที่ยืนยันก่อนเอกสารนี้:
`edrxdr-rehearsal-20261014-20261014T060821Z.bundle`
ครอบคลุมถึง 142fc76, SHA256:
`916508fbfb726dcb169b72c71c15e1c24aaedfb50558389ecdd7f10ad62888f4`
ตรวจผ่านทั้ง VM และสำเนา Windows แล้ว ยังไม่มี push ในชุดงานที่รายงาน

ชุดอัปเดตเอกสารฉบับนี้จะออก bundle ใหม่หลัง commit ให้ดูผลจริง/receipt เพื่อทราบ final HEAD และ SHA256 ไม่อ้างว่าติดตั้งบน VM แล้วจากการได้สคริปต์เพียงอย่างเดียว

Git bundle ไม่รวม Docker images/volumes/model, dependencies, secrets/config นอก Git, ignored/untracked files, external runs หรือรูปในแชท ต้องสำรองแยกก่อนคืน/ย้าย VM การ clone bundle กู้ source ไม่ได้กู้ระบบพร้อมใช้งานทั้งหมด

กู้เฉพาะกรณีจำเป็นในโฟลเดอร์ใหม่: `git clone -b work/bluefield-shadow-quarantine /path/to/verified.bundle EDRXDR-restored` ห้ามทับโฟลเดอร์ทำงานเดิม

## 13. ข้อความสำหรับแชทผู้รับงาน

รับช่วง EDR/XDR บน saiuser@172.16.30.147 repo /home/saiuser/EDRXDR-Morpheus branch work/bluefield-shadow-quarantine เริ่มตรวจ Git/เวลาจริงและอ่าน training/HANDOFF-COMPANY-SCOPE-20261014.md คู่กับ training/HANDOFF-REHEARSAL-20261014.md ห้าม reset/clean ผล 5/5/5 ยืนยัน Windows origin, Morpheus GPU, API/UI และ clean exit แล้ว แต่สโคปบริษัทยังค้าง vulnerability workflow, AI quality evaluation, advanced decision/alerts/incident reports, automatic-response playbook และ load/recovery งานวันที่ 16 เป็นประชุมความก้าวหน้า onsite ต้องเตรียม notebook/ระบบและหลักฐานให้ตรวจได้ ห้ามเริ่ม GPU จนยืนยัน reservation ใหม่ BlueField ต้องปิดและ automated response OFF ตรวจ receipt bundle ใหม่เพื่อทราบ HEAD เอกสารล่าสุด
