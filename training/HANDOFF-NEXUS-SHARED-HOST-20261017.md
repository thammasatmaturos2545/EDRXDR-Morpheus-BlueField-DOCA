# ส่งต่องาน NEXUS EDR/XDR หลังเหตุการณ์เลือก Wazuh Manager ข้ามกลุ่ม

จัดทำ 17 ต.ค. 2026 (Asia/Bangkok) จากผล Git และผลทดสอบที่ผู้ปฏิบัติงานส่ง ไม่ใช่การตรวจ VM สดโดยผู้เขียน

## 1. จุดเริ่มรับงาน

- VM: saiuser@172.16.30.147
- Repo: /home/saiuser/EDRXDR-Morpheus
- Branch ปัจจุบันที่ตรวจ: work/nexus-exact-ai-v1
- HEAD ก่อนชุดเอกสารนี้: 8cc05cc0999168dee960f451533c64b7d22fb1c8
- เวลา Git snapshot: 17 ต.ค. 09:03:42 ไทย; working tree มีงานค้าง ห้าม reset/clean/checkout ทับหรือ commit รวมทั้งหมด
- คู่มือเดิม training/HANDOFF-NEXUS-20261015.md ยังเป็น untracked และต้องรักษาไว้
- คู่มือ training/HANDOFF-COMPANY-SCOPE-20261014.md มีข้อมูลพื้นฐาน/สโคปบริษัท แต่รายการงานที่ยังไม่มีหลักฐานบางส่วนล้าสมัย ให้ใช้ผลล่าสุดในเอกสารนี้ประกอบ
- เอกสารวันที่ 17 ฉบับก่อนที่ตั้งต้น 5b6955a ไม่ได้ติดตั้ง เพราะ preflight หยุดก่อนแก้ repo ให้เลิกใช้ install_shared_host_handoff_20261017.py กับ branch นี้
- ชุดนี้เพิ่มเอกสารและหลักฐาน provenance เท่านั้น ยังไม่แก้ runtime bug

## 2. เหตุการณ์วันนำเสนอและข้อค้นพบ

ผู้ใช้รายงานว่า 16 ต.ค. เมื่อเปิดงานร่วมกับอีกกลุ่มบนเครื่องเดียวกัน ระบบของเราเลือก Wazuh Manager ของอีกกลุ่ม ทำให้นำเสนอไม่ได้ เหตุการณ์นี้แยกจากผลซ้อมที่ผ่านก่อนหน้า ไม่เปลี่ยนผลเก่า

ข้อค้นพบจากโค้ดที่เก็บไว้และ diff ที่ส่ง:

- frontend/src/app/api/wazuh/route.ts ใช้ docker ps กรอง com.docker.compose.service=wazuh.manager และ running แล้วเลือกผลตัวแรก ไม่กรอง Compose project
- diff 5b6955a..8cc05cc เพิ่ม deterministic event UID แต่ไม่แก้ manager resolver
- diff งานค้างเพิ่ม selectBalancedWazuhAlerts เปลี่ยน tail -n 100 เป็น tail -c 4194304 และส่ง sampledAlerts; ไม่แก้ manager resolver เช่นกัน
- frontend/src/app/api/status/route.ts ใน source เดิมกรอง service-only แล้วรวม states; diff ที่ส่งไม่พบการแก้ไฟล์นี้ จึงต้องตรวจด้วยว่าหน้าสถานะรวมข้อมูลข้าม project หรือไม่
- การเพิ่ม exact UID ไม่ได้แก้ source selection โดยตัวมันเอง ถ้าเลือก manager ผิดก็ยังรับข้อมูลผิดต้นทางได้

กลไกเลือกตัวแรกเป็น defect ที่ตรวจพบใน source และสอดคล้องกับเหตุการณ์ แต่ยังไม่มี incident-time container IDs/labels, process cwd/build และ log วันจริงพอจะยืนยัน root cause ของทุกส่วน ห้ามอ้างว่าทั้ง GPU/Kafka pipeline ใช้ manager ผิดจากการพบ frontend bug เพียงจุดเดียว

สำคัญ: runtime Dashboard ตาม handoff วันที่ 15 อยู่ /home/saiuser/edrxdr-nexus-integrated-preview-20261015 ไม่ใช่ยืนยันว่า process รันจาก repo หลัก ต้องตรวจ source/build ที่รันจริงด้วยก่อนสรุปว่าแก้ source แล้ว deployment หาย

## 3. ผลที่มีหลักฐานแล้ว พร้อมขอบเขต

| งาน | หลักฐานที่อ่านจากผลส่งมา | ขอบเขต/ข้อจำกัด |
|---|---|---|
| H100 live ถึง NEXUS | h100-live-e2e-20261014t182610z/result.json PASS, UID ab444373341573048c7967e8a2e2468d4fadc5d16873e70c1cff597c18c16a4c | Wazuh → Normalizer → Kafka input → H100 Morpheus → Kafka output → fail-closed indexer → OpenSearch → /api/events → NEXUS; matched ด้วย event_uid; ไม่ใช่ production/accuracy acceptance |
| Linux FIM lifecycle | fim-live-20261014t190819z/result.json PASS | Agent 003, /tmp/edrxdr-fim-lab/probe.txt, added/modified/deleted Rules 554/550/553; ไม่แทนการทดสอบทุก endpoint |
| Vulnerability Detection | vulnerability-live-20261014t191437z/result.json PASS | พบเอกสาร 7,646 ใน wazuh-states-vulnerabilities-*, Agent 003, sample 10; ไม่ใช่จำนวน CVE ไม่ซ้ำหรือผล remediation |
| sudo use case | sudo-usecase-20261014t191852z/result.json PASS | Rule 5402, Agent 003, UID และ Kafka key ตรง; ยืนยัน detection/transport ไม่ได้ยืนยัน GPU inference ของเหตุการณ์นี้ |
| SSH failure use case | ssh-fail-usecase-20261014t192315z/result.json PASS | Rule 5710, Agent 003, UID/key/source ตรง; timing รวม polling/test harness overhead |
| Normalizer benchmark | normalizer-performance-20261014t193519z/result.json PASS | isolated replay Kafka → Normalizer → Kafka ไม่มี GPU; 100 และ 1,000 events ไม่มี missing/duplicate ตามการทดสอบนี้ |
| Active Response lab | active-response-lab-20261014t195436z/result.json PASS | สร้าง marker ชั่วคราวแล้ว rollback 21.036192 วินาที; ไม่แก้ firewall/account/network ไม่ kill process; ไม่ใช่ Block IP/Isolate Host หรือ AI-triggered response |

ทุก path ของหลักฐานในตารางอยู่ภายใต้ training/evidence/ ใน repo อย่านำวันที่ UTC ในชื่อโฟลเดอร์ไปเรียกว่าเวลาไทย: 14 ต.ค. 18–19 UTC ตรงกับเช้ามืด 15 ต.ค. ไทย

รายละเอียด benchmark: 100 events = 375.536 events/s, p95 147.05 ms; 1,000 events = 624.411 events/s, p95 1329.05 ms, p99 1383 ms มี queueing สูงขึ้นใน burst ไม่ใช่ throughput/latency ทั้งระบบ EDR/XDR หรือ H100

Vulnerability severity snapshot: unknown '-' 3,210; High 2,750; Medium 1,102; Critical 486; Low 98 ไม่แปลง unknown เป็นปลอดภัย และจำนวน snapshot อาจเปลี่ยนได้

## 4. NEXUS, UID lookup และคุณภาพโมเดล

ตาม handoff วันที่ 15 (ยังไม่ตรวจซ้ำวันที่ 17):

- Dashboard หลัก http://127.0.0.1:3001/nexus/index.html; Research ใช้ #research, #shadowdetails, #bluefielddetails, #modeldetails, #researchevidence
- Snapshot มี SOC events/alerts 109, UID lookup matched 9, Shadow Severity/Behavioral/matched 32, BlueField historical 6; เป็นคนละชุดข้อมูล ห้ามรวมเป็นยอดเหตุการณ์ใหม่
- SOC ใช้ Live OpenSearch host port 9200; Shadow/BlueField ใช้ edrxdr-replay-opensearch-1; IP 172.18.0.3 เป็นค่าประวัติ Docker IP อาจเปลี่ยน
- Runtime directory /home/saiuser/edrxdr-nexus-integrated-preview-20261015; backup /home/saiuser/edrxdr-nexus-backups/; ห้ามลบ preview หรือ start process ทับพอร์ต 3001
- Correlation ต้อง exact event_uid เท่านั้น ห้าม fallback timestamp/rule/host

ผลคุณภาพที่ handoff รายงานจาก run morpheus-raw-offline-check-20261008T203523Z-1803526: 1,314 samples, Precision 67.18%, Recall 100%, F1 80.37%, ค่าเรียกในรายงานว่า False Positive Rate 32.82%, parity/raw-event PASS แต่ numeric gate FAIL; Rule 2901 precision 0%, FPR 100%; Shadow Authorized NO และ Production Ready NO

ตัวเลขชุดนี้ยังไม่ได้อ่าน evaluation source/confusion matrix โดยตรงในงานส่งต่อครั้งนี้ ต้องตรวจนิยาม FPR ว่าใช้ FP/(FP+TN) หรือค่าอื่นก่อนนำเสนอ และตรวจ provenance/weak labels/model version ก่อนเทียบกับโมเดลที่ deploy ห้ามเปลี่ยนชื่อ metric หรือรับรองประสิทธิภาพจาก handoff อย่างเดียว เก็บ held-out แยก ไม่ใช้ชุด 479 events ฝึกโดยไม่มีแผนประเมิน

## 5. งานค้างที่ต้องรักษา

Modified ณ snapshot:

- frontend/public/nexus/app.js
- frontend/src/app/api/nexus/v1/snapshot/route.ts
- frontend/src/app/api/wazuh/route.ts
- frontend/src/lib/nexus-soc.ts

Untracked ณ snapshot:

- frontend/src/lib/uid-lookup-server.ts
- frontend/src/lib/uid-lookup.ts
- frontend/src/lib/wazuh-sampling.ts
- frontend/tests/uid-lookup.cjs
- frontend/tests/wazuh-sampling.cjs
- training/HANDOFF-NEXUS-20261015.md
- uid_lookup/ มี implementation และ tests: bounded_scan, bulk_payload/reconcile/result, checkpoint/verified_checkpoint, index_mapping, live_probe, lookup_docs, planned_scan, wazuh_uid และ tests search_integrity

Diff tracked งานค้าง 4 ไฟล์ประมาณ 892 insertions/19 deletions ไม่รวม untracked; ยังไม่ได้ review/test ทั้งชุดโดยผู้เขียน handoff นี้ ไม่ถือว่า source เหล่านี้อยู่ใน Git bundle จนกว่าจะ commit ต้องสำรอง WIP แยกก่อนเปลี่ยนงาน

## 6. ประวัติ commit ที่สำคัญ

- 093c741: SOC event explorer แยก experimental results
- f55c360/e251539: NEXUS integration / deterministic Wazuh identity
- 02c59c0/f0480b7: bounded live inference / reservation guard
- 472fa1e/a95983b: fail-closed live indexer / events API
- c143ded/f851b7a: exact UID correlation / runtime evidence
- 5142485/b491690: indexer candidate / isolated verification
- 6b6d897: live H100 NEXUS correlation
- 752b661/bcd0be5: FIM lifecycle / vulnerability evidence
- 5b558ba/e87c2ba/8db2093: sudo / SSH failure evidence
- 2f8fea3/8cc05cc: isolated normalizer benchmark / lab response rollback

ชื่อ commit เป็นดัชนีสำหรับตรวจ ไม่ใช่หลักฐานแทนการอ่าน test/evidence

รักษารอบเดิม d20261014t055117-9fd3415a = 5/5/5, d20261013t181858-e1bbae7e = 2/2/2 exit0 และ d20261013t164314-c1b4d787 = 3/3/3 launcher exit124 ตามเดิม

## 7. รับช่วงแบบอ่านอย่างเดียว

Windows PowerShell:

```powershell
ssh saiuser@172.16.30.147
```

VM:

```bash
cd /home/saiuser/EDRXDR-Morpheus || exit 1
TZ=Asia/Bangkok date -Is
git branch --show-current
git log -8 --oneline
git status --short
cat training/HANDOFF-NEXUS-SHARED-HOST-20261017.md
ss -H -ltnp 'sport = :3001'
curl --noproxy '*' --max-time 10 -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3001/nexus/index.html
systemctl show edrxdr-bluefield.service --no-pager -p ActiveState -p SubState -p UnitFileState
docker ps -a --filter label=com.docker.compose.service=wazuh.manager --format '{{.ID}} {{.Names}} project={{.Label "com.docker.compose.project"}} service={{.Label "com.docker.compose.service"}} status={{.Status}}'
```

ผล HTTP 200 ไม่ยืนยัน source identity/API content ตรวจ PID ที่ฟัง 3001 แล้วอ่าน cwd ของ exact PID เช่น readlink -f /proc/PID/cwd หลังแทน PID ที่ตรวจจริง ไม่ dump process environment ซึ่งอาจมี secrets เทียบ build/source runtime กับ repo และไฟล์งานค้าง

ต้องยืนยัน project/container เจ้าของเรากับผู้ดูแลก่อน docker exec อ่านข้อมูลภายใน อย่าอ่าน alert payload ทุก manager เพื่อหาอันที่ใช่ ชื่อเดิม wazuh-wazuh.manager-1 ไม่ใช่หลักฐาน ownership ปัจจุบัน

Windows อีกแท็บ หากยังไม่มี tunnel:

```powershell
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -L 127.0.0.1:3001:127.0.0.1:3001 saiuser@172.16.30.147
```

เปิด http://127.0.0.1:3001/nexus/index.html คงแท็บ tunnel ไว้ การเปิด UI ไม่ใช่เริ่ม inference อย่าใช้ demo/start-ui.sh โดยอัตโนมัติเมื่อ NEXUS preview อาจครองพอร์ตอยู่

## 8. P0: แก้การเลือก resource และตรวจ deployment

1. บันทึก incident timeline, URL ที่ผิด, source runtime, config ที่ไม่ใช่ secrets, exact container ID/project/service ของเราและ candidate metadata ที่จำเป็น โดยไม่เก็บ payload อีกกลุ่ม
2. ทำ manager resolver กลางกำหนด identity ของเราอย่างชัดเจน เช่น project + service หรือ exact container ที่ inspect ตรวจ project/service อีกครั้ง; ชื่อ env ใด ๆ ที่ออกแบบต้องระบุว่า newly introduced ไม่ใช่แค่ตั้งค่าที่โค้ดไม่อ่าน
3. discovery ต้องได้ exactly one ใน scope; 0/multiple/mismatch/unavailable ให้ error ชัดเจน ห้ามเลือกตัวแรกหรือ fallback ไปอีกกลุ่ม
4. ใช้ validated container ID เดียวกันในการอ่านข้อมูล; status API ต้อง scope indexer/dashboard/forwarder เช่นเดียวกัน ไม่รวมสถานะข้าม project
5. แสดง source identity/checked time ที่จำเป็นบน UI; identity failure ไม่ใช่ zero alerts และไม่ใช่ healthy state
6. ตรวจ forwarder→Kafka→normalizer→indexer source bindings แยก ไม่เหมารวมจาก frontend bug; exact UID เป็นเงื่อนไขจำเป็นในการ correlate แต่ไม่แทนการยืนยันเจ้าของ resource
7. แก้ใน branch ปัจจุบันอย่างประสานงาน ห้ามทับ UID lookup/sampling work; review ขอบเขต sampled alerts และแยก snapshot count จาก historical total
8. deploy/rebuild เฉพาะ frontend ของเราเมื่อ review แล้ว ตรวจ runtime directory/build ใหม่จริง ไม่หยุด shared services เพื่อให้ทดสอบผ่าน

Tests ที่ต้องเพิ่ม: manager สอง project running พร้อมกัน, สลับลำดับรายการ, ของเราหยุดแต่อีกกลุ่มเปิด, project mismatch, 0/หลายตัวใน scope, Docker timeout, recreate container และ status isolation เริ่มด้วย mocks/fixtures ของทีม ไม่จำเป็นต้องใช้ GPU

เกณฑ์ปิด incident: tests ผ่าน, runtime ที่ใช้จริงเลือก resource ถูก, ไม่มี fallback ข้ามกลุ่ม, integration หลาย project ผ่านในขอบเขตที่ได้รับอนุญาต และเก็บ evidence/source identity การทำ end-to-end GPU ใหม่ต้องจองใหม่และระบุผลแยก ถ้ายังไม่ได้รันให้คงสถานะ pending

## 9. งานตามสโคปที่เหลือหลังปรับข้อมูลใหม่

| ส่วน | งานต่อ |
|---|---|
| Wazuh/FIM/Vulnerability | มี lab evidence แล้ว; ตรวจ ownership/source, coverage endpoint บริษัท, inventory/remediation และ representative cases |
| AI pipeline | มี H100 exact UID path แล้ว; ทำ isolation, continuous reliability/recovery และตรวจ accuracy/model provenance |
| AI quality | ตรวจรายงานต้นฉบับและ metric definitions, ลด FP ราย rule, held-out evaluation และ baseline |
| Use cases | SSH/sudo/FIM lab มีแล้ว; ตกลง use case บริษัท/เกณฑ์รับงานและ expected outcome |
| Active Response | marker rollback ผ่านเฉพาะ lab; Block IP/Isolate Host, approval/rollback/verification และ AI decision path ยังไม่ยืนยัน ห้ามเปิด production |
| Performance | normalizer-only benchmark มีแล้ว; full pipeline/GPU sustained load, latency percentiles, recovery/backpressure ยังไม่ยืนยัน |
| Dashboard | P0 source isolation; ต่อด้วย auth/RBAC, auto-start/recovery ของบริการตัวเอง, historical pagination/filter/exact UID |
| DPU/BlueField/operator | historical/isolated evidence เท่านั้น ต้องตรวจ requirement และ integration เพิ่ม |

ยังไม่มี feedback อาจารย์เพิ่มเติมนอกเหนือจากเหตุการณ์เลือก Manager ที่ผู้ใช้รายงาน ไม่ตั้ง deadline หรือผลประเมินแทนผู้ใช้

## 10. ข้อจำกัดและ backup

Shared VM: ห้าม reset/clean, ลบ index/backlog, reset Kafka offsets, แก้ driver/CUDA/network หรือหยุดงานทีมอื่น BlueField ต้อง inactive/dead/disabled; production automated response OFF ผล lab marker ไม่ใช่อนุญาตใช้ response จริง ไม่มี GPU reservation ล่าสุดที่ยืนยันสำหรับวันที่ 17

Bundle ที่ตรวจ checksum ก่อนหน้านี้ครอบคลุมเพียง 5b6955a ไม่ใช่ 8cc05cc หรือ WIP ปัจจุบัน ต้องออก bundle ใหม่และเก็บ WIP archive แยก Git bundle ไม่รวม untracked/modified source, model/runtime volumes, external runs และ preview runtime

ตัวติดตั้งชุดนี้ตรวจ branch/HEAD และไม่มี staged changes แต่ยอมรับ working tree ที่มีงานค้างโดยทำ manifest+tar ของ tracked/untracked ที่เปลี่ยนก่อนเพิ่มเอกสาร ตรวจว่า bytes/status งานค้างเหมือนเดิมก่อนและหลัง commit เอกสาร ไม่แก้/commit งานค้าง ไม่แก้ HANDOFF-NEXUS-20261015.md และไม่แก้ pointers เดิม เพื่อลดการชนงานของทีม

WIP archive ไม่รวม ignored files, model/volumes, preview runtime หรือ secrets/config นอก Git ไม่ใช่ระบบ restore พร้อมใช้งาน; เก็บ archive ที่สิทธิ์จำกัด ส่งให้ผู้รับเฉพาะช่องทางของทีมและตรวจเนื้อหาก่อนเผยแพร่ ห้าม extract ทับ repo เดิมโดยไม่ review

หาก installer พบ branch/HEAD เปลี่ยน, staged work, symlink ในชุด WIP หรือไฟล์เปลี่ยนระหว่างทำงาน จะหยุด ไม่ลบ/rollback งานของทีม ให้อ่านข้อความและ git status ก่อนดำเนินต่อ ผล commit/bundle/sha ให้ยึด output จริง ไม่ใช้ test commit จากเครื่องผู้เขียน

## 11. Prompt รับช่วง

รับช่วง NEXUS EDR/XDR VM saiuser@172.16.30.147 repo /home/saiuser/EDRXDR-Morpheus branch work/nexus-exact-ai-v1 parent checkpoint 8cc05cc0999168dee960f451533c64b7d22fb1c8 อ่าน training/HANDOFF-NEXUS-SHARED-HOST-20261017.md ก่อน ตรวจ HEAD/status จริง ห้าม reset/clean มี UID lookup/sampling/NEXUS WIP ต้องรักษา Runtime เดิมอยู่ /home/saiuser/edrxdr-nexus-integrated-preview-20261015 ต้องตรวจ PID/cwd/build ไม่ start frontend ทับ วันจริงเลือก Wazuh Manager อีกกลุ่ม โค้ด API ใช้ service-only discovery แล้วเลือกตัวแรก; diff ปัจจุบันยังไม่แก้ resolver ให้เริ่มแก้ source identity และ tests multi-project โดยไม่อ่าน payload/หยุดงานอีกกลุ่ม มีหลักฐาน H100 exact UID, FIM lifecycle, vulnerability, SSH/sudo, isolated normalizer benchmark และ lab marker rollback แล้ว แต่ไม่ใช่ production หรือ response network จริง เก็บผลซ้อม/exit124เดิม แยก committed evidence กับ WIP และ historical runtime ห้ามใช้ GPU โดยไม่มี reservation ใหม่ BlueField ปิดและ production automated response OFF แยกคำสั่ง Windows/VM พร้อมตรวจ runtime ก่อนอ้างว่าแก้แล้ว
