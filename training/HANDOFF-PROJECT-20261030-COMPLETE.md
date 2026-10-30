# EDRXDR–Morpheus–NEXUS: สถานะโครงการและคู่มือรับช่วงฉบับรวม

วันที่จัดทำ: 30 ตุลาคม 2026 (Asia/Bangkok)
จุดล่าสุด: Experiment B ของ BERT v4 ฝึกเสร็จและตรวจ exit/checkpoint/evidence แล้ว
สถานะรวม: Research prototype; ยังไม่ยืนยัน production readiness

## 1. อ่านเอกสารนี้อย่างไร

เอกสารนี้รวมผลที่ผู้ปฏิบัติงานส่งจาก VM ในแชท, รายงานส่งต่อวันที่ 23 ต.ค., รายงานวันที่ 30 ต.ค. ที่จบ STEP 166.40 และประวัติการจัดระเบียบไฟล์ ไม่ใช่ผลตรวจ VM สด ณ เวลาที่เพื่อนเปิดอ่าน

- ให้หลักฐานล่าสุดของแต่ละส่วนมาก่อนเอกสารเก่า อย่าใช้ PID, HEAD, port หรือ path เก่าเป็นค่าคงที่
- อย่านำสถานะการรัน NEXUS วันที่ 20 ต.ค. ไปทับ runtime หลังวันที่ 22–30 ต.ค.
- แชทเก่าเต็มแล้ว รับช่วงจากไฟล์และ evidence บน VM ได้ ไม่ต้องเริ่มการทดลองใหม่เพราะอ่านแชทเก่าไม่ได้
- สถานะว่า “ผ่าน” ระบุขอบเขตที่ตรวจเท่านั้น การส่ง event ครบไม่ได้พิสูจน์ความแม่นยำของโมเดล
- ข้อมูลจากรายงานเก่าที่ยังไม่ได้เปิดหลักฐานต้นฉบับตรวจซ้ำ ให้ถือเป็น reported historical result
- เอกสารฉบับนี้ยังไม่ได้ยืนยันว่าถูก commit/push บน VM จนกว่าผู้รับช่วงจะตรวจ Git จริง

## 2. เป้าหมายโครงการและผลงานที่ทีมทำ

พัฒนาต้นแบบ EDR/XDR รับเหตุการณ์ Windows/Linux ผ่าน Wazuh ส่งเข้า Kafka/normalizer ประมวลผล AI ด้วย Morpheus/BERT เก็บผลใน OpenSearch และแสดงหลักฐานบน NEXUS พร้อม SOC Copilot ช่วย analyst ทบทวน

```text
Windows/Linux → Wazuh → Forwarder/Normalizer → Kafka
     → Morpheus/BERT → Kafka output → validated indexer → OpenSearch
     → NEXUS API → Dashboard / analyst review

Wazuh active/rotated alerts → History sync → SQLite → History API → All Events
Saved review reports → auth + schema/evidence validation → SOC Copilot

CAM-LDS attack steps → frozen family split → BERT v4 tactic experiments A/B
                (เส้นทางทดลองนี้ยังไม่ถูก deploy เป็น Severity บน NEXUS)
```

ใช้ Wazuh, Kafka, Morpheus, BERT, OpenSearch และ Next.js เป็นฐาน ผลงานทีมที่ควรอธิบายในการนำเสนอคือ:

1. เชื่อม pipeline, ปรับ normalizer/schema, เก็บ event identity/source/hash และตรวจผลครบสาย
2. ทำ exact UID correlation และปฏิเสธผลขัดแย้ง/ไม่ครบ แทนการจับคู่จากข้อความคล้ายกัน
3. พัฒนา NEXUS adapter, Dashboard, All Events, History index/sync/auth และ observed endpoints
4. ทำ Manager resolver แยก Compose project เพื่อแก้เหตุการณ์เลือก Wazuh คนละกลุ่ม
5. พัฒนา supervisor/checkpoint/evidence/rollback และการติดตั้งแยก candidate จาก runtime
6. ออกแบบ dataset/protocol/การแบ่งข้อมูล/การทดลอง loss ของโมเดล พร้อมข้อจำกัดการประเมิน
7. เชื่อม saved SOC review กับ authentication และ evidence validation; การสร้าง LLM draft ใหม่ยังต้องพิสูจน์

ห้ามอ้างว่าทีมสร้าง framework, pretrained BERT หรือ rule engine ของ Wazuh เอง ต้องแยกงาน integration/implementation/evaluation ของทีมจากเครื่องมือที่นำมาใช้

## 3. แผนที่เครื่องและเส้นทางสำคัญ

| รายการ | ตำแหน่ง/สถานะล่าสุดที่ทราบ |
|---|---|
| VM | `oa-hgx-h100-bu-02`, SSH `saiuser@172.16.30.147` (ตรวจการเข้าถึงจริงอีกครั้ง) |
| Main repository | `/home/saiuser/EDRXDR-Morpheus` |
| Workspace hub | `/home/saiuser/EDRXDR-workspace` — สร้างแล้ว 81 ลิงก์ |
| Archive | `/home/saiuser/EDRXDR-Archive` |
| BERT v3 | `/home/saiuser/EDRXDR-BERTv3-work` — คงที่เดิม |
| BERT v4 | `/home/saiuser/EDRXDR-BERTv4-work` — คงที่เดิม |
| History runtime/DB | `/home/saiuser/nexus-history-preview-20261020` และ `history.sqlite3` |
| UI cwd ที่ inventory วันที่ 30 รายงาน | `/home/saiuser/nexus-uid-candidate-wgpajvXL` — เคยเป็น PID1140935, port3006 |
| Indexer bind source ที่วันที่ 30 รายงาน | `/home/saiuser/nexus-continuous-indexer-8sgl87ck` |
| Live indexer container | `edrxdr-live-indexer-managed-v1` |
| UI unit หลักล่าสุด | `nexus-all-events-prod-3006.service` |
| Indexer unit | `nexus-live-indexer.service` |
| History sync | `nexus-history-sync.service` + `.timer` |
| Release ในรายงานวันที่ 23 | `/home/saiuser/nexus-copilot-release-nya54u9q` — อาจถูก override ด้วย release ใหม่แล้ว |
| Candidate วันที่ 20 | `/home/saiuser/nexus-history-preview-20261020/nexus-build-candidate-20261020` — เก็บไว้ ไม่ถือว่าเป็น runtime ล่าสุด |

Git ที่เคยตรวจจริงในแชทวันที่ 20 คือ branch `work/nexus-exact-ai-v1`, HEAD `82521f898e8ab25d2c4891b81bc211a9015ccd89` และมี WIP หลายไฟล์ รายงานท้องถิ่นวันที่ 30 ซึ่งจบ STEP166.40 อ้าง HEAD `a049b7a` จึงต้องตรวจ HEAD จริงก่อนทำงาน ห้ามใช้ hash ใดในเอกสารนี้ไป reset/checkout ทับงาน

ใน workspace มีหมวด `live`, `code`, `experiments`, `protected`, `review`, `storage-review`, `deletion-review`, `inventory` และลิงก์ archive การแก้ไฟล์ผ่านลิงก์คือแก้ไฟล์ต้นทาง ไม่ใช่สำเนา

## 4. สถานะองค์ประกอบระบบ

| ส่วน | ทำแล้ว | ยังไม่ยืนยัน/งานค้าง |
|---|---|---|
| Wazuh | Agent/Manager, FIM, SSH/sudo และ vulnerability lab | health/coverage ปัจจุบันและแหล่งข้อมูลของแต่ละกลุ่ม |
| Kafka/Normalizer | ส่งข้อมูล, normalize, UID, benchmark จำกัดขอบเขต | backlog/lag/recovery ต่อเนื่องและ topic/group isolation ปัจจุบัน |
| Morpheus Severity | มี bounded GPU inference/e2e จริง | continuous live inference, quality, long-run reliability |
| Indexer/OpenSearch | จัดเก็บผล, exact UID lookup, managed indexer มีรายงานว่ารัน | ผลต่อเนื่องครบทุก event/retention/recovery หลัง restart |
| NEXUS | Overview, Threat detection, Endpoints, History, research views | sampled totals/time-series wording, complete health semantics |
| History | SQLite dedup/index/pagination/sync/auth, rotated archive support | growth limit/retention, backup rotation, exact UID API, source guard ให้เทียบเท่า resolver |
| Copilot | saved drafts8รายการ, auth/schema/evidence validation ผ่านตามรายงานวันที่22 | generation draftใหม่ครบสาย, provider/runtime, analyst approval, evaluation |
| BERT v4 | A และ B ฝึกเสร็จ, dev comparison, evidence | error analysis, baseline/ablation, decision freeze, final holdoutครั้งเดียว |
| DFP/Behavioral/AE | มีประวัติ research/shadow | ยังไม่ยืนยัน live behavioral pipeline/quality |
| BlueField/DPU | มีประวัติตรวจ/research | live network integration ยังไม่ยืนยัน; ไม่เปิด service เอง |
| Response | lab marker-file + rollback | ยังไม่มีการยืนยัน AI-triggered block/isolation production |
| Operations | backup, rollback, bounded execution, archive/hub | logout/reboot recovery และ shared-resource agreement |

## 5. ผล pipeline และ lab ที่รักษาไว้

- Windows-origin run `d20261014t055117-9fd3415a`: captured/scored/indexed 5/5/5, offsets25727–25731, UIอัปเดต2→3→5, shutdown/launcher/container exit0 ตามหลักฐานรอบนั้น
- Windows agent004 file added Rule554 มี raw SHA256 และ UID/source ตรงกัน รอบนี้ยืนยัน integration ไม่ใช่ accuracy100%
- Run `d20261013t181858-e1bbae7e`: 2/2/2 และ exit0
- Runเก่า `d20261013t164314-c1b4d787`: 3/3/3 แต่ launcher exit124 ต้องเก็บผลเดิม ห้ามแก้ย้อนหลังว่า exit0
- Historical evidence อยู่ใน `training/evidence/` และ external run dirs เช่น `/home/saiuser/edrxdr-demo-runs/`; bundle ไม่ได้รวม external run dirs โดยอัตโนมัติ
- FIM lab: added554 / modified550 / deleted553; sudo5402; SSH failure5710 ตามรายงานเก่า ไม่ใช่การยืนยัน attack coverage ทุกแบบ
- Normalizer benchmark ที่รายงาน:100events≈375.5events/s,p95≈147.1ms;1000events≈624.4events/s,p95≈1329.1ms เป็น normalizer-only ไม่รวม GPUทั้งระบบ
- Vulnerability counts เป็น snapshot findings ไม่เท่ากับจำนวน CVE ไม่ซ้ำหรือจำนวนที่แก้แล้ว
- Active-response lab เป็น marker-file/rollback ไม่ใช่ firewall block, host isolation หรือ production automation

## 6. NEXUS, Manager isolation และ systemd

### สิ่งที่แก้แล้วตามหลักฐาน

เหตุการณ์นำเสนอเดิม: เมื่อเปิดงานหลายกลุ่ม ระบบเลือก Wazuh Manager ผิดกลุ่ม จึงนำเสนอไม่ได้ สาเหตุเชิงระบบคือ selection scope/identity ไม่พอ ไม่ใช่เพียง “อยู่บน VMเดียวกันแล้วต้องผิดเสมอ”

- ของเรา: `wazuh-wazuh.manager-1`, Compose project `wazuh`, service `wazuh.manager`
- อีกกลุ่ม: `luckyfive_wazuh-wazuh.manager-1` — ห้ามเลือกเป็น fallback
- Resolver ตรวจ project/service, candidateจำนวนเดียว, full containerID, inspect identity/state และ fail closed เมื่อไม่กำหนดหรือกำกวม
- ชุดทดสอบ resolver13สถานการณ์ผ่านวันที่20; รายงานวันที่23กล่าวถึง UID lookup resolverอีก7กรณี ต้องตรวจโค้ดปัจจุบัน/แต่ละชุดแยกกัน
- ยังต้องมีหลักฐานทดสอบจริงหลาย Compose projects เปิดพร้อมกันตามการประสานของแต่ละกลุ่ม

วันที่20 ทดลอง systemd ด้วย Node18 แล้ว Snapshot503 ขณะที่ Node20.20.2 ผ่าน จากนั้น override ExecStart ของ3001/3006ด้วย Node20พาธเต็ม ย้ายและ manual restart ผ่านทั้งคู่ History401/200, exact UID, Snapshot ผ่าน ไม่ได้พิสูจน์กลไกภายในของ failure ทั้งหมด

วันที่22รายงานว่า reboot แล้ว3006หยุดและ startกลับได้ จึงยังไม่ถือว่า auto-start/reboot recoveryผ่าน วันที่30หลังจัดแฟ้ม UI/indexerยัง activeด้วยPIDเดิม และ History timer active/waiting; service sync inactive/dead อาจเป็น oneshotปกติ ต้องดู timer/last result ประกอบ

อย่าดูเพียงไฟล์ unitหลัก: systemd drop-insหลายตัวมีลำดับ override ให้ตรวจ effective `ExecStart`, `WorkingDirectory`, `DropInPaths` และ `/proc/<PID>/cwd` ก่อน deploy/ย้ายแฟ้ม อย่าใช้ PIDเก่าเพื่อ kill

สถานะล่าสุดของ3001, Linger, enabled/disabledหลังวันที่20ยังต้องอ่านใหม่ ไม่อนุมานว่าแก้ persistenceแล้ว และไม่เปลี่ยน Lingerบนบัญชีร่วมโดยไม่ได้ประสาน

## 7. All Events / History / คะแนน AI

- History API: `GET /api/nexus/v1/history?page=1&hours=all&search=<UID>`; hours all/24/168/720, page size100, search<=128ในโค้ดที่ตรวจวันที่20
- searchเป็น substringหลายคอลัมน์ ต้องกรอง `event_uid` ให้ตรงจริงก่อนใช้เป็น evidence ไม่ใช่ exact UID endpointโดยตัวมันเอง
- Historyเป็น retained snapshotที่ sync ไม่ใช่ realtime ทั้งหมด และมีข้อจำกัด retention/import
- Snapshot API: `/api/nexus/v1/snapshot?hours=168` เป็น sampled/latest-window view ห้ามนำ totalsมาเทียบตรงกับ History
- History Basic auth username`saiuser`, secretที่ `/home/saiuser/nexus-history-preview-20261020/preview-access.secret` ตามโค้ดวันที่20 ห้ามเปิดเผย/commit/copyใส่ prompt
- Authคุ้มครองเฉพาะ routeที่ติดตั้ง ไม่ใช่ authทุก NEXUS API
- Exact UIDที่เคยทดสอบ: `5062c6e96485f0415cdbeeb57e2e899f18950aa85d79983b5c5c39591e9e62ef`
- Raw Severity score `0.0005193048855289817`, display `0.1 / 100`, low_severity เป็น retained inference result ไม่ยืนยัน GPUกำลังทำงาน
- ค่า0–1อาจแสดงคูณ100เพื่ออ่านง่าย แต่ไม่ใช่ calibrated attack probability และไม่ใช่คะแนน riskรวมทุกมิติ
- แยก matched/not_scored/conflict/unavailable; missing/nullไม่ใช่0 และ not_scoredไม่ใช่ปลอดภัย
- History backup20ต.ค.มี32241events; report22ต.ค.มี35837matchingevents ทั้งคู่เป็น historical counts ต้องอ่านจำนวนปัจจุบันใหม่
- โค้ดHistoryถูก reconcileเข้า repoในรอบ20ต.ค.และ tests/typecheckผ่าน มีปัญหาCRLFใน tests/nexus-soc.cjs และส่งคำสั่ง normalizeไปแล้ว แต่ยังไม่มีผลยืนยัน normalize/commitในแชทนี้
- `history/`ใน repoเป็น source record แต่ runtime scriptยังอ้าง external path อย่าย้าย DB/scriptตาม repoโดยไม่ทำ migration

## 8. SOC Copilot และงาน LLM สำหรับเพื่อน

รายงานวันที่23อ้างผล Browser22ต.ค.: Copilot review API `/api/nexus/v1/copilot/review`, auth401/200, saved drafts8รายการและแสดงรายละเอียดได้ ดังนั้นอย่ารื้อทำ saved-report viewerใหม่โดยไม่ตรวจของจริง

ยังไม่ยืนยัน generation summaryใหม่จาก eventใหม่ครบสาย หรือ analyst approvalจริง ห้ามถือว่า saved draftเป็นผลผ่านการอนุมัติ และห้ามเดาผู้ให้บริการ/modelจากคำว่า Copilot

งานรับต่อ:
1. ตรวจ routeปัจจุบัน, feature flagsและ saved report schemaแบบไม่เปิด secrets
2. แยก saved-review flowจาก generation flow; ตรวจว่ามี provider adapterอยู่แล้วหรือยัง
3. เริ่ม synthetic fixtures/mock provider ก่อนส่ง security logsจริงไป external LLM; ตกลงขอบเขตข้อมูล/providerกับผู้รับผิดชอบ
4. ดึง evidenceฝั่งserverจาก UIDที่ผู้ใช้มีสิทธิ์อ่าน จำกัดevents/tokens/timeout/rate และใช้ allowlist fields
5. แสดงข้อเท็จจริง ข้ออนุมาน unknowns และ suggested checksแยกกัน ทุก findingต้องอ้าง UIDจาก input
6. เก็บ provider/model/prompt_version/generated_at/input hashและ truncated flag ตรวจ schemaก่อนแสดงผล
7. ไม่ให้ log textสั่งงานโมเดล/เรียกtools; ทดสอบ prompt injection, HTML escaping, unsupported claims, UIDนอกinput, provider timeoutและ stale cache
8. แยก LLM summaryจากคะแนน Morpheus และ BERTv4 ห้ามเติมคะแนน เปลี่ยนthreshold หรือสั่ง responseเอง
9. ก่อนเก็บ summariesลงฐานข้อมูล กำหนดschema/access/retentionแยกจาก eventsและหลักฐานต้นฉบับ

ตัวอย่าง contractที่เสนอ ไม่ใช่ APIที่ยืนยันว่ามีอยู่แล้ว:

```json
{
  "summary_status": "generated|unavailable|insufficient_evidence",
  "summary_th": "...",
  "findings": [{"text": "...", "evidence_uids": ["..."]}],
  "unknowns": [],
  "suggested_checks": [],
  "model": "configured server-side",
  "prompt_version": "...",
  "production_ready": false,
  "automated_response_allowed": false
}
```

## 9. แยกโมเดลและ dataset ให้ถูกก่อนทำ BERT ต่อ

| ชุด | งาน | ข้อควรระวัง |
|---|---|---|
| Wazuh Severity เดิม | high/lowจาก weak labelsสัมพันธ์ rule.level | ไม่ใช่ attack detectorอิสระ |
| BERTv3 | มี checkpoint `bert-v3-logonly-expA-16669` และ RUN_COMPLETEที่ v4ตรวจผ่าน | ผล metrics/splitทั้งหมดของv3ยังไม่ส่งมาครบ ห้ามเดา |
| BERTv4 PlanB A/B | CAM-LDS attack-step multi-label tactics11labels | ไม่ใช่ Severity0–1 และยังไม่ deployบน NEXUS |

รายงานเก่า Severity contextใช้ train5232/dev1314และรายงาน precision67.18%,recall100%,F1≈80.37%,ค่าเรียกว่าFPR32.82% พร้อม numeric gate fail ต้องตรวจ confusion matrix/นิยามFPRจากต้นฉบับก่อนอ้าง เพราะ FPRไม่เท่ากับ1−precisionโดยทั่วไป

Severity full-modelอีกชุด test1316รายงาน TP408 FP810 TN0 FN98, precision≈.335 recall≈.806 F1≈.473 เป็นคนละรุ่นกับ context/dev1314 ห้ามรวมเป็นผลเดียวกัน

STEP166.38–166.40เป็นบริบท v3 เก่า: synthetic split guard9/9และ feature ablation8/8 ไม่ใช่ผลยืนยันdatasetv4จริง `TRAINING_GATE=BLOCKED`ในโค้ดร่างนั้นพิมพ์ตายตัว ต้องดู protocolปัจจุบัน ไม่ย้อนรันขั้นเก่าเพราะแชทเต็ม

## 10. BERTv4 protocolที่ล็อกไว้

Work: `/home/saiuser/EDRXDR-BERTv4-work`

- Protocol: `protocols/bert-v4-planB-16694.json`
- Dataset: `datasets/bert-v4-planB-16695/{train.jsonl,development.jsonl,manifest.json}`
- Dataset source: CAM-LDS, Zenodo record18861762 ตาม protocolที่อ่านจากVM
- Task: attack_step_multi_label_tactic_classification; labelsเป็น weak step-level labels ไม่ใช่ ground truthรายlog
- Train458steps: families1,3,5; dev72steps: families2,4,7
- Final holdout: family6; protocolระบุ eligible100steps, ประเมินครั้งเดียวหลัง freeze ห้ามอ่านlog/labelsหรือใช้จูนก่อนกำหนด
- Targetsตามลำดับ: collection, command-and-control, credential-access, defense-evasion, discovery, execution, initial-access, lateral-movement, persistence, privilege-escalation, reconnaissance
- ไม่รวม exfiltration/impact; zero-targetstepsถูกexclude ไม่ถือว่าbenign
- Input attack-stepรวม logหลายแหล่ง: alerts.json,audit.log,auth.log,syslog,fast.log,access.log,daemon.log,kern.log
- ไม่ใช้ attackmate.json/attackmate.log/output.log; Wazuhใช้ full_logและไม่ใช้rule metadata
- source-balanced token allocation,fair round robin,max256tokens,source namesอยู่ในinput จึงอาจเป็นshortcut
- train/devไม่มี shared token sequenceตามmanifest แต่มี train possible-label-hint1stepที่ต้องทบทวน ไม่แก้frozenข้อมูลเงียบ ๆ
- Fixed threshold0.5, devใช้เลือกmodel, finalholdoutไม่ใช้tune
- ต้องทำ source-only baselineและ source-order ablationตามprotocol

Hashesที่ต้องรักษา:

```text
protocol  c7c35882c15f60999970e26d119227129afd256362a8b7c26f079f68ff1b4492
train     faff273c1e8e2741a010a6b549a91983a1110e0416592a80fc40c405aa779db1
dev       db14bfbd53800816757cd4cb4c19f1cec1c66420227a4e2801f5c94da9483075
archive   ba824f500af6d64925792d6a693e54afb761d1cfb5fe515efb2206035772bade
labels    cc27fee6d78b6de3d5d2172b334269bbcd9747dac80b6882e8982229b2540afe
tokenizer 851ca67100d372ca3ae031a6abd168f53489eebfd7d89523f35c5c9b4d372c3c
```

Manifestยังระบุ experimental_not_training_approved, training_approved_for_gpu=false, production_approved=false ไม่เปลี่ยนค่าเพื่อให้ผ่านเอง ประวัติแชทมีผู้ใช้จอง GPUและดำเนินการทดลองจริง แต่ไม่เท่ากับผ่าน formal dataset/production approval

## 11. BERTv4 งานที่ทำแล้วถึง Experiment B

### A

`runs/bert-v4-planB-16704` มี RUN_COMPLETE/model/tokenizer/report เลือกbest epoch3 ใช้ unweighted BCE

### B

สคริปต์ `scripts/train_bert_v4_expB_16719.py`

```text
SHA256 5adef781ed07fb11f0a52af32142a72e0dd251a00a9f87cfb6c2c39f8f4dae1c
output runs/bert-v4-planB-expB-16719
recovery runs/.bert-v4-recovery-expB-16719-best
container edrxdr-bert-v4-expb-16719
image sha256:66a654987f79ee7a929b8e24ea4e0f5eea8a02245131f0eeb97292beabcedc4e
```

STEP167.20ตรวจscripthash/syntax/weightedBCEและCPU forward/backward/finite gradientผ่าน จากนั้นตรวจprotocol+CPUpreflightก่อนฝึกจริง

Runtimeที่ถูกต้อง `/opt/conda/envs/morpheus/bin/python`, torch2.4.0+cu124, transformers4.44.2 บน image `edrxdr-morpheus-train:25.06` Pythonbase `/opt/conda/bin/python3` ไม่มีtorch; ไม่ต้องติดตั้งใหม่เพื่อแก้environmentผิด

จอง GPUถึง31ต.ค.00:00+07สำหรับรอบ30ต.ค. ตั้ง container timeoutก่อน23:55และเผื่อkill20วินาที ผู้ใช้ยืนยันอีกกลุ่มไม่ได้ใช้ ห้ามใช้สิทธิ์รอบนี้อนุมานอนุญาตรอบใหม่

ก่อนรันเคยเห็น PID189036/root `/LuckyFive/miniforge3/envs/morpheus/bin/python` ใช้≈808MiB ไม่ได้หยุดprocessนั้น การที่utilization0ไม่รับประกัน GPUว่าง รอบถัดไปต้องตรวจ/ประสานใหม่

Launchใช้ imageIDตายตัว, containerแยก, detached+init, networknone, read-onlyroot, user=saiuser, CPU4/RAM12GiB/shm1GiB, tempcache, offlineHF, work/v3read-onlyและmountrunsเขียนได้ ไม่แก้NEXUS

Hyperparameters:3epochs,microbatch8,accumulation2,effectivebatchโดยทั่วไป16,lastbatchเล็ก,AdamW lr2e-5 weight_decay.01,seed42,max256,bf16autocast,gradclip1.0

Bใช้ pos_weight=(N−positive)/positive clamp1..5 จากtrainเท่านั้น supporttrainตามลำดับ `[13,30,43,75,132,113,36,14,70,61,72]` น้ำหนัก discovery≈2.4697,execution≈3.0531,ที่เหลือ5

โหลดencoderจากv3checkpointเดียวตามscript และสร้างclassifier11outputsใหม่ เพราะเดิม3outputs เป็น warningที่คาดไว้ ต้องตรวจinitialization/seed/A scriptถ้าจะอ้างควบคุมทุกปัจจัยแบบเคร่งครัด

เลือกbestโดยtuple(macroF1,microF1)ที่threshold.5 ไม่ใช่เลือกmicroสูงสุด; เก็บbest/recoveryโดยไม่เก็บoptimizer จึงไม่ใช่checkpointสำหรับ resume optimizerต่ออย่างแม่นยำ

### ผลที่ยืนยัน

| Dev metric | A best epoch3 | B best epoch2 |
|---|---:|---:|
| Macro F1 all11 | .051948051948051945 | .17271493028480606 |
| Micro F1 | .03007518796992481 | .25573770491803277 |
| Exact match | 2/72 (.0277778) | 3/72 (.0416667) |
| Tactics F1>0 | 1/11 | 6/11 |

| Tactic | A F1 | B F1 | Dev support |
|---|---:|---:|---:|
| collection | 0 | 0 | 4 |
| command-and-control | 0 | 0 | 10 |
| credential-access | 0 | 0 | 8 |
| defense-evasion | 0 | .47826087 | 19 |
| discovery | 0 | .14814815 | 24 |
| execution | 0 | .04081633 | 3 |
| initial-access | 0 | 0 | 9 |
| lateral-movement | 0 | 0 | 3 |
| persistence | 0 | .44444444 | 20 |
| privilege-escalation | 0 | .34375 | 20 |
| reconnaissance | .57142857 | .44444444 | 3 |

B epoch1 macro.146425/micro.297143; epoch2 macro.172715/micro.255738; epoch3 macro.149137/micro.221477 จึงเก็บepoch2ตามmacroเกณฑ์เดิม ไม่เปลี่ยนเกณฑ์ย้อนหลัง

Train loss A/Bต่างสูตรห้ามเทียบตรงกัน Bดีขึ้นบนdevชุดนี้แต่ยังอ่อน:5tacticsF1ศูนย์,executionต่ำ,exactmatch3/72 และ devsupportบางclassแค่3 การเปรียบเทียบหนึ่งseed/หนึ่งsplitยังไม่พิสูจน์ generalizationหรือcausalityทั้งหมด

ผล container: exited,exit0,OOMKilled=false,runtimeErrorว่าง, RUN_COMPLETEทั้งA/B,protocol/train/devhashตรงกัน,holdout_evaluated=false,production_approved=false

Evidenceล่าสุด:
`/home/saiuser/EDRXDR-BERTv4-work/evidence/expB-complete-20261030T160734991890Z`

มี container-state.json,training.log,experiment-A-report.json,experiment-B-report.json,comparison.json,experiment-B-SHA256.json ตามคำสั่งที่รันสำเร็จ Hashmanifestใช้ตรวจmodel/tokenizer/report อย่าแก้outputทับ

### งาน BERT ถัดไปตามลำดับ

1. สำรองB checkpoint+evidenceออกจากVMและตรวจSHAก่อนจัดพื้นที่เพิ่ม; อย่าลบA/v3/recovery
2. เก็บTP/FP/FN/precision/recall/support/predicted-positiveรายtacticบนdev เพื่อแยกไม่ทำนายเลยกับทำนายผิด
3. ใช้saved checkpointกับevaluation-only; ถ้าใช้CPUfloat32แทนGPUbf16ให้บันทึกความต่าง ไม่อ้างmetricตรงกันโดยไม่ตรวจ
4. ตรวจ errors/weak labels/possible-label-hintโดยไม่เปิดfinalholdout; ถ้าจะเปลี่ยนdatasetสร้างversion/protocolใหม่
5. ทำsource-onlybaselineและsource-orderablationตามprotocol; ถ้าต้องเปลี่ยนtrainingdesignให้ freezeก่อนรัน
6. ทบทวน initialization, seeds, exclusions, class imbalance, train/dev gap ก่อนเพิ่มepochs/weightcapหรือทดลองอีกหลายแบบ
7. ไม่tune thresholdด้วยholdout; protocolปัจจุบันfixed.5 ถ้าจะเปลี่ยนต้องแยกprotocolชัดและfreezeก่อนtest
8. เลือกcandidate/เกณฑ์/แผนรายงานให้เสร็จก่อน finalholdoutfamily6ครั้งเดียว ผลไม่ดีต้องรายงานตามจริง ไม่ใช้holdoutเลือกmodelซ้ำ
9. Deploymentv4เป็นงานแยก ต้องออกแบบattack-stepinput/schema/labels11classและe2eใหม่ ไม่เสียบแทนbinarySeverityโดยตรง

## 12. การจัดระเบียบไฟล์ที่ทำจริงแล้ววันที่30ต.ค.

งานนี้เสร็จบางส่วน ไม่ใช่ล้างhomeครบ และไม่อนุมัติให้ลบทุกอย่างในreview

### คู่แรก: copy/verifyแล้วนำต้นฉบับออก

- `/home/saiuser/edrxdr-demo-ui.kK1OR9` → `/home/saiuser/EDRXDR-Archive/edrxdr-demo-ui.kK1OR9`
- `/home/saiuser/edrxdr-demo-ui.3iJery` → `/home/saiuser/EDRXDR-Archive/edrxdr-demo-ui.3iJery`
- รวม488regularfiles,ตรวจhash/metadata/symlinkเทียบmanifestก่อนลบต้นฉบับ; ไม่follow node_moduleslink
- Copyreport `copy-verification-20261030T131731278804Z.json`
- Removaljournal `cleanup-two-demos-20261030T133101722137Z.jsonl`
- สำเนาคงอยู่ครบ; freeเพิ่ม≈139.9MiBจากก่อนลบ แต่เพิ่งcopyเพิ่มก่อนหน้านั้น จึงไม่ใช่ลดข้อมูลสุทธิ≈140MiBจากจุดเริ่มงาน

### ชุดต่อมา: ย้าย25โฟลเดอร์เข้าคลัง

23demo UI suffixes:
`1Z9DUM 4wEbTw 6LixTr 6sFWZy 8ixGWq E5nCvG HEvHDu HoGr5h JCdZ6K OpT0GH SwRzT6 ZXHg9D ZtGs62 abCYVx ajylNm luhA3Q mXtBbe rMxcG5 tcAJlw vqcQmU wDUlVp yIXtPL yxqgdm`

ชื่อเต็มคือ `edrxdr-demo-ui.<suffix>` พร้อมอีก2รายการ `edrxdr-nexus-ui.916xiS`, `edrxdr-nexus-ui.YkDff4`

ย้ายจาก`/home/saiuser/<name>`ไป`/home/saiuser/EDRXDR-Archive/<name>` บนfilesystemเดียวกัน เก็บ6155regularfiles≈1.67GiB รวม.nextและsymlinks ตรวจhashก่อน/หลัง ไม่เขียนทับปลายทาง และบันทึกrollback journal

หลักฐานในArchive:
- `ui-batch-dependencies-20261030T135327987743Z.json`
- `ui-batch-manifest-20261030T140254457582Z.json`
- `ui-batch-move-20261030T140254457582Z.jsonl`

ผล ARCHIVED_COUNT=25,FILES_DELETED=False; รวมคู่แรกเป็น27โฟลเดอร์/6643regularfiles สำเนาในArchiveเก็บข้อมูลครบ การย้ายfilesystemเดียวกันช่วยลดความรก ไม่เพิ่มfreeโดยตัวมันเอง

### Workspace hub

สร้าง`/home/saiuser/EDRXDR-workspace`พร้อม81ลิงก์ ตรวจผ่าน
- `inventory/creation-report.json`
- `inventory/links.tsv` และ applied previewตามตัวสร้าง
- Planต้นทาง `/home/saiuser/EDRXDR-Archive/workspace-hub-preview-20261030T141434112323Z.json`
- mappingdigest `8c9db42e39465a6504699bd999ae17b7ff30ff21a85304f358cc3e33448e9f4c`

สร้างhubไม่ได้ย้ายruntime/repo/BERT/backupsและไม่ทำให้ทุกแฟ้มในhomeหายไป ลิงก์node_modulesของUIในArchiveยังพึ่งrepoเดิม จึงไม่ใช่backupdependenciesที่กู้คืนได้เดี่ยว ๆ

### npm cache

ล้างเฉพาะ `/home/saiuser/.npm/_cacache`≈652.09MiB หลังตรวจprocess/containerและhash เก็บ `_npx`≈1.99MiB (`create-next-app`) และ `_logs`≈.05MiB

- Review `inventory/npm-cache-review-20261030T143030103262Z.json`
- Manifest `deletion-review/npm-cacache-manifest-20261030T143837203705Z.json`
- Journal `inventory/npm-cacache-cleanup-20261030T143837203705Z.jsonl`
- Result `inventory/npm-cacache-result-20261030T143837203705Z.json`
- free2890645504→3574407168bytesตามรอบcleanup; NEXUS/indexerPIDเดิมและtimerปกติ
- คำเตือน/root/.docker/config.jsonหลังdropสิทธิ์ไม่ใช่เหตุให้chmodไฟล์root; การตรวจcontainerรอบนั้นสำเร็จ
- cachedpackagebytesถูกลบจริง ไม่มีสำเนาbytesในmanifest; ครั้งติดตั้งใหม่อาจต้องดาวน์โหลด

### สิ่งที่ยังไม่เสร็จในการจัดแฟ้ม

69รายการในreviewยังรอจำแนก ไม่ใช่deletionapproval รายงาน/evidenceอาจย้ายได้หลังdependencyreview; preview/backup/gpu-once/.lockจากชื่ออย่างเดียวตัดสินลบไม่ได้

ต้องทำตาราง source→destination→reason→dependencies→restore และpreviewก่อนย้ายจริง อัปเดตhub linksเมื่อย้ายtarget รักษาreports/checkpoints/protocol/volumes/certificates/keysและruntime

พื้นที่: `/home`แยกfilesystem9.8GB ขณะที่`/`มี3.1TBว่างในรอบinventory ต้องตรวจquota/สิทธิ์/นโยบายก่อนใช้พื้นที่root ห้ามย้ายhomeลงrootหรือแก้partitionเอง ตัวเลขfree3.33GiBหลังcacheเป็นอดีตก่อนฝึกBที่เพิ่มcheckpoint ให้ตรวจใหม่

## 13. ปัญหาสำคัญและงานค้างรวม

| ลำดับ | ปัญหา/งาน | เกณฑ์ปิดงาน |
|---|---|---|
| P0 | ตรวจGit/runtimeจริงและรักษางานร่วม | HEAD/WIP/effectiveunits/mountsปัจจุบันบันทึกแล้ว ไม่มีoverwrite |
| P0 | สำรองผลBและเอกสารฉบับนี้ | hash/restoreplan,สำเนานอกVM,ไม่ลบA/recovery |
| P0 | BERTqualityยังอ่อน | deverroranalysis+baselines+frozenfinaleval ไม่มีtestleakage |
| P0 | LiveAIต่อเนื่องยังไม่ยืนยัน | eventใหม่UIDเดียวครบWazuh→Kafka→Morpheus→index→NEXUSภายใต้GPUslot |
| P1 | SharedHostisolation | actualmulti-projecttest,explicitports/topics/groups/index/volumes,ไม่มีfallbackผิดทีม |
| P1 | LLMSummaryใหม่ | evidencegrounding/auth/errorlimits/analystreviewพร้อมผลทดสอบ |
| P1 | Reboot/logoutrecovery | ทดสอบและข้อตกลงoperatorครบ ไม่autoGPUเกินslot |
| P1 | ReconcileGit/runtimeล่าสุด | diffreview,tests,typecheck,commitแยกขอบเขตและbundleใหม่ |
| P1 | Historygrowth/partialAI | retention,sizecap,backuprestore,OpenSearchtimeout/shardfailfailclosed |
| P1 | Dashboardsemantics | samplecounts/timefallback/unknownhealth/read-onlywordingตรงข้อเท็จจริง |
| P2 | จัดแฟ้ม69รายการต่อ | inventory+preview+manifest+rollback;ไม่มีลบจากชื่อ |
| P2 | Behavioral/DFP/AE | แผนfeatures/dataset/evalและevidenceแยกจากSeverity |
| P2 | BlueFieldnetwork | hardware/passthrough/DOCAcapabilityตรวจจริงและอนุมัติก่อนเปลี่ยน |
| P2 | Automatedresponse | labpolicy,humanapproval,rollback,auditและmodelqualityก่อนเสมอ |

ไม่มีหลักฐานเพียงพอในแชทนี้ที่จะสรุปว่างาน networkทั้งหมดทำไม่ได้: VMมีEthernet/networkทั่วไปใช้งานได้ แต่ liveBlueField/DPUหรือhardwareoffloadเป็นอีกขอบเขต ต้องตรวจphysicaldevice/passthrough/interface/DOCAตามสิทธิ์ ห้ามแก้driver/interfaceเพื่อพิสูจน์เองบนเครื่องร่วม

ประเด็นประเมินเทียบโจทย์บริษัทต้องอ่านPDFต้นฉบับและทำrequirement→implementation→evidence→gapรายข้อ เอกสารนี้ไม่กล่าวว่าครบสโคปบริษัททั้งหมด วันfinalยังไม่ยืนยันและมีบริบทว่าทุกกลุ่มอาจทดสอบdataset/usecaseเดียวกัน อย่าใช้ชุดfinalมาจูน

## 14. เครื่องมือที่ใช้งานและเวอร์ชันที่เคยยืนยัน

| เครื่องมือ | หน้าที่ | เวอร์ชัน/บริบท |
|---|---|---|
| Ubuntu/Linux, SSH/SCP | VM/admin/filetransfer | hostnameตรวจแล้ว; OSปัจจุบันตรวจใหม่ |
| Docker, Compose labels/volumes | isolation, runtime/model/data | ห้ามcomposeup/downทั้งsharedstack |
| NVIDIA H10080GB | training/inference | driver580.178.04และCUDA13ที่nvidia-smiเคยรายงาน ไม่เท่ากับtorchCUDA |
| NVIDIA Morpheus | GPUAIframework | trainimage25.06,PyTorch2.4.0+cu124,Transformers4.44.2 |
| Python, PyTorch, HuggingFace, safetensors | training/evaluation/modelartifacts | ใช้morpheusenvpython; v4bestไม่มีoptimizerstate |
| Wazuh agent/manager/indexer/dashboard | endpointalerts/FIM/vulnerability | stack4.14.7ที่เคยรายงาน; installer4.14.1.debในhomeเป็นคนละartifact |
| Kafka | topics/consumer groups | image3.8.1ตามhistoricalinventory |
| OpenSearch | event/AIindex/query | image2.11.0ตามhistoricalinventory |
| SQLite, hashlib/JSON | history,checksums,evidence | SQLiteonlinebackupสำหรับDBกำลังใช้งาน |
| Next.js/React/TypeScript | NEXUSfrontend/API | Next15.5.18,React19.1.0ที่เคยbuild |
| Node.js | frontendruntime | explicit20.20.2; systemdefault18.19.1เคยทำSnapshot503 |
| systemd userservices/timers | UI/indexer/sync | effectiveoverrideสำคัญ; persistenceอ่านใหม่ |
| Git, bundle, tar, SHA256 | versioning/backups | WIP/DB/weightsไม่รวมในbundleอัตโนมัติ |
| cp,find,du,df,readlink,ss,/proc | inventory/archivechecks | rsyncไม่มีในรอบจัดแฟ้ม; rgบนVMบางรอบไม่มี |
| LLM/SOC Copilot | savedreviewและงานsummaryต่อ | ยังไม่ยืนยันprovider/model/generationruntimeล่าสุด |

เวอร์ชันตารางนี้เป็นสิ่งที่เคยยืนยัน ไม่ใช่คำแนะนำให้อัปเกรดหรือdowngradeเครื่องร่วม

## 15. Backups และวิธีกู้คืนอย่างมีขอบเขต

- ชุด20ต.ค. `/home/saiuser/EDRXDR-Archive/nexus-systemd-20261020T012409921855Z`
- Windows `C:\Users\bagel\Downloads\nexus-systemd-20261020T012409921855Z` SHAตรงVMแล้ว
- มีcommitted-history.bundle(HEAD82521f8),repository-working-tree.tar.gz,deployed-source.tar.gz,new-handoff-evidence.tar.gz,history.sqlite3(32241events),patch/status/manifest
- เป็นสำเนาก่อนreconciliation/latestNEXUS/v4B จึงไม่ใช่backupครบงานวันที่30 ต้องสำรองส่วนใหม่เพิ่ม
- รุ่น17ต.ค.มีbundle82521f8และWIPtarแยก; รุ่น14ต.ค.มีbundle checkpoints181b5f0/506fbea/142fc76/5b6955aตามประวัติ อย่านำbundleเก่าทับrepoใหม่
- Backupreconciliation `/home/saiuser/EDRXDR-Archive/documentation-backups/all-events-reconcile-20261020T013131380917Z`
- Backupunitวันที่20และprivateenvironmentอยู่ในhistoryworkspace/migrationdirs ห้ามcommitprivateenvironment
- บางarchiveรักษาsymlinkแทนdependencybytes; ต้องตรวจtargetก่อนrestore/build
- ใช้SQLitebackupAPIและintegritycheck ไม่cpDBactiveแบบละเลยWAL
- Restoreเป็นโฟลเดอร์แยก ตรวจhash/mounts/dependenciesก่อนใช้ ไม่untarทับruntime/repoที่มีWIP

## 16. ขั้นตอนเพื่อนรับงานจริง

### Windows PowerShell

```powershell
ssh saiuser@172.16.30.147
```

ถ้าต้องดูUIจากWindows เปิดอีกแท็บและตรวจlocalportไม่ชนก่อน:

```powershell
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -L 127.0.0.1:13006:127.0.0.1:3006 saiuser@172.16.30.147
```

เปิด `http://127.0.0.1:13006/nexus/index.html` หลังใส่รหัสแล้วterminaltunnelเงียบเป็นปกติ ปล่อยแท็บไว้ รหัสHistory/Copilotใช้วิธีที่ทีมอนุมัติ อย่าส่งเข้าพร้อมต์

### VM: เริ่มอ่านสถานะจริง (ไม่restart/ไม่training)

```bash
cd /home/saiuser/EDRXDR-Morpheus || exit 1
TZ=Asia/Bangkok date -Is
git branch --show-current
git log -3 --oneline
git status --short
git --no-pager diff --check
df -hT / /home/saiuser

for unit in nexus-all-events-prod-3006.service nexus-live-indexer.service nexus-history-sync.service nexus-history-sync.timer; do
  systemctl --user show "$unit" --no-pager --full \
    -p ActiveState -p SubState -p MainPID -p WorkingDirectory \
    -p ExecStart -p DropInPaths -p UnitFileState -p Result
done
loginctl show-user "$(id -u)" -p State -p Linger
ss -H -ltnp 'sport = :3006'
docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}'
```

อย่า dump`docker inspect`ทั้งobjectหรือ/proc/environทั้งvaluesเพราะอาจมีsecrets อ่านเฉพาะidentity/mountmetadataที่จำเป็น

### VM: อ่านเอกสารและผลB

```bash
cat training/HANDOFF-PROJECT-20261030-COMPLETE.md
ls -la /home/saiuser/EDRXDR-workspace/inventory
python3 -m json.tool /home/saiuser/EDRXDR-BERTv4-work/runs/bert-v4-planB-expB-16719/training_report.json
docker inspect edrxdr-bert-v4-expb-16719 --format 'status={{.State.Status}} exit={{.State.ExitCode}} oom={{.State.OOMKilled}}'
```

ถ้าfile/containerไม่พบให้รายงานและค้นpathเฉพาะworkspaceที่เกี่ยวข้อง ห้ามสร้างของใหม่ทับเพราะคิดว่าหาย

### VM: ตรวจHTTPแบบไม่ส่งsecret (ตัวเลขเปลี่ยนได้)

```bash
for path in /nexus/index.html /api/wazuh '/api/nexus/v1/snapshot?hours=168' '/api/nexus/v1/history?page=1' /api/nexus/v1/copilot/review; do
  printf '%s ' "$path"
  curl --noproxy '*' --max-time 25 -sS -o /dev/null -w '%{http_code}\n' "http://127.0.0.1:3006$path"
done
```

History/Copilot401อาจเป็นauthปกติ อย่าแก้ด้วยการปิดauth หาก503ให้ตรวจfeatureflag/runtime/sourceก่อนrestart

### ก่อนแก้โค้ด/commit/deploy

1. เลือกเจ้าของงาน: BERT/evaluation, pipeline/operations, LLM/Copilot, fileorganization ให้แต่ละคนรู้filesที่อีกคนแก้
2. เก็บcurrentdiff+untracked/sourcehashesอย่างprivate; ตรวจsecretsก่อนทำtar/commit
3. อ่านAGENTS.mdและhandoffใกล้ส่วนงาน ไม่แก้syncedsources/เป็นreference
4. ใช้exactfilelistreview/stage ไม่git add .กับWIPร่วม
5. ใช้testsของเวอร์ชันrepoจริง; node tests/wazuh-source.cjs,wazuh-sampling.cjs,uid-lookup.cjs,nexus-endpoints.cjs,nexus-soc.cjs และnpm run typecheckเมื่อเกี่ยวข้อง
6. git diff --checkผ่าน; หากCRLFให้สำรองแล้วnormalizeเฉพาะไฟล์ที่review ไม่ปิดwhitespacecheckทั้งrepo
7. Build candidateแยก,ทดสอบportว่าง,ตรวจauth/UID/schemaก่อนdeploy พร้อมrollbackของruntimeปัจจุบัน
8. Commitเฉพาะขอบเขตที่reviewแล้ว; สร้างbundleใหม่หลังcommitและสำรองWIP/DB/weights/unitconfigแยก พร้อมverifyนอกVM

## 17. Prompt พร้อมส่งให้ GPT ของเพื่อน

คัดลอกข้อความในกรอบนี้ และแนบเอกสารฉบับนี้ให้ GPT ของเพื่อน:

```text
รับช่วง EDRXDR–Morpheus–NEXUS จาก handoff วันที่30ต.ค.2026
อ่าน HANDOFF-PROJECT-20261030-COMPLETE.md ทั้งฉบับก่อน เริ่มด้วย read-only inventory
VM saiuser@172.16.30.147 repo /home/saiuser/EDRXDR-Morpheus
ห้ามถือว่า HEAD/PID/runtimeจากอดีตยังตรงจริง ตรวจ git branch/log/statusและeffective systemdก่อนแก้
รักษา WIP,backup,protocol,dataset splits,weightsและหลักฐานเก่าทั้งหมด ห้ามreset/cleanหรือoverwriteงานร่วม

สถานะล่าสุดที่ยืนยัน: BERTv4 ExperimentBฝึกครบ3epochs,exit0,noOOM,
bestepoch2,devmacroF1 .1727149303,microF1 .2557377049,exactmatch3/72
A bestmacro .05194805195,micro .03007518797,exactmatch2/72
protocol/train/dev hashesตรงกัน; finalholdoutfamily6ไม่ถูกใช้
ยัง5tacticsF1ศูนย์และยังไม่production approved
ผลBเป็น11tacticsที่attack-step ไม่ใช่Severitybinaryที่แสดงบนNEXUS
ห้ามเอาBไปเสียบNEXUSโดยตรง งานถัดไปคือper-tacticTP/FP/FN/precision/recall,
source-onlybaseline/source-orderablation และfreezeก่อนfinalholdoutครั้งเดียว
GPUจองรอบเก่าถึง31ต.ค.00:00ไทยเท่านั้น ต้องยืนยันสิทธิ์ใหม่ก่อนGPUรอบถัดไป

NEXUSล่าสุดรายงานport3006,cwd nexus-uid-candidate-wgpajvXL และmanagedliveindexer
ตรวจของจริงก่อนrestart/build/move มีHistoryและsavedSOC-Copilot8draftตามรายงานก่อนหน้า
ยังไม่ยืนยันLLM generationใหม่ครบสาย หากรับงานLLMให้ตรวจimplementationปัจจุบันก่อนสร้างซ้ำ
Summaryต้องauth/evidenceUIDgrounding/unknowns/schema/timeout/prompt-injectionguard,
ไม่เปลี่ยนคะแนนMorpheus ไม่ส่งlogsจริงไปexternalproviderก่อนตกลง ไม่เปิดautomatedresponse

จัดไฟล์แล้วบางส่วน:UIเก่า27โฟลเดอร์6643filesอยู่EDRXDR-Archive,
workspacehub81symlinksสร้างแล้ว ล้างเฉพาะnpm_cacache652MiB เก็บ_npx/_logs
69reviewรายการยังไม่อนุมัติลบ production/repo/BERTยังอยู่ตำแหน่งเดิม
ห้ามลบจากชื่อpreview/backup/tmpหรือคิดว่าhubเป็นcopy ต้องpreview/checkdeps/hash/rollbackก่อนย้าย

เริ่มด้วยสรุปสิ่งที่ตรวจยืนยันได้/สิ่งที่ต้องตรวจเพิ่ม แล้วทำงานที่ได้รับมอบหมายต่อ
แยกคำสั่งWindowsPowerShellกับVM เก็บsecretออกจากแชท/Git ไม่เปลี่ยนsharedinfra/Linger/driverเอง
```

## 18. ขอบเขตที่ยังต้องยืนยันเมื่อรับช่วง

- HEADปัจจุบัน,commitการreconciliation/CRLF,โค้ดที่เพื่อนLLMเพิ่มหลังhandoffเดิม
- runtime/sourcepathปัจจุบันทุกพอร์ต,enabled/linger/rebootbehavior
- LiveAIe2eต่อเนื่องและlag/backlogปัจจุบัน แม้indexerรันไม่ได้พิสูจน์workerกำลังscore
- ผู้ให้บริการLLM,model,configและdata-policyยังไม่ทราบจากหลักฐานนี้
- คุณภาพ/metricsv3และformaltrainingadmissionก่อนหน้าไม่ได้ส่งมาครบ
- พื้นที่freeหลังB,ตำแหน่งrootfilesystemที่อนุญาตให้ใช้,review69รายการ
- finaldate/requirementบริษัทฉบับล่าสุด,เกณฑ์ร่วมของทุกกลุ่ม

หากข้อมูลส่วนใดต่างจากเอกสาร ให้บันทึกสิ่งที่ตรวจพบและเวลาจริงไว้เป็นcheckpointใหม่ ไม่แก้ประวัติผลเก่าให้ดูเหมือนเป็นสถานะใหม่
