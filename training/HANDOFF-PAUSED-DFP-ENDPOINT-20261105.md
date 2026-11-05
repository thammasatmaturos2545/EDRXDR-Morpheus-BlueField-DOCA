# ส่งต่อ EDRXDR–Morpheus–NEXUS — พักงาน / DFP / Endpoint / Human Review

วันที่ 5 พฤศจิกายน 2026, Asia/Bangkok
สถานะ: เจ้าของสั่งพัก แล้วอนุญาตเขียนเอกสารส่งต่อเท่านั้น
วันสอบ: **27 พฤศจิกายน 2026** ไม่ใช่กำหนดสิ้นเดือนเดิม

## 1. เริ่มตรงนี้และอ่านให้ครบ

VM: saiuser@172.16.30.147 (oa-hgx-h100-bu-02)
Repo: /home/saiuser/EDRXDR-Morpheus
Branch ที่คาด: work/nexus-exact-ai-v1 ต้องตรวจจริงก่อนทำงาน
HEAD ล่าสุดที่ operator ยืนยันก่อนชุดงานนี้: 2fd3a6c
เอกสารนี้จะมี commit เพิ่มต่างหาก ตรวจ commit ของไฟล์ด้วย git log

อ่านตามลำดับ:
1. docs/architecture/EDRXDR-ENDPOINT-HUMAN-REVIEW-v2-20261105.md
2. training/HANDOFF-PROJECT-NEXUS-ENDPOINT-20261105.md ทั้งไฟล์
3. เอกสารนี้ (ผลและขอบเขตล่าสุด)

หลักฐาน VM ในรอบนี้มาจากผู้ใช้รันคำสั่ง/ส่ง aggregate outputs ไม่ใช่ AI SSH ตรวจโดยตรง
SSH จาก AI เคยเข้าไม่ได้ ห้ามอ้างว่ามี key/เชื่อมต่อโดยตรงแล้ว
รักษา staged/untracked/WIP ทุกชิ้น ห้าม reset/clean, git add ., overwrite หรือ commit งานคนอื่นปน
เดิมมี staged training/START-HERE-DFP-HANDOFF-20261103.md 193บรรทัดและ untracked history/,uid_lookup/,handoff/evidence หลายรายการ ต้องดูสถานะปัจจุบันใหม่

## 2. ขอบเขตที่ยังมีผล

- Agent003 เป็นเป้าหมายแรก; Agent004 พัก; network telemetry นอก scope
- ไม่ใช้ BlueField/RShim/DPU/AppShield ในเส้นทาง endpoint ใหม่
- Dashboard รุ่นนี้ถอด LLM summary แล้ว ไม่เรียก provider เพื่อให้คำแนะนำจากหน้าใหม่
- ยังไม่แทน live BERT และ automated response ยังปิด ไม่มี execution endpoint
- ยังไม่เลือกโฟลเดอร์ข้อมูลจริงที่จะป้องกัน การทดสอบล่าสุดใช้เฉพาะ fresh scratch directory
- เจ้าของยังไม่ทราบเกณฑ์สอบว่าบังคับ ransomware AI classifier หรือยอมรับ behavior rules
  ห้ามตัดสินแทนหรืออ้างว่ากฎเท่ากับ classifier ที่วัดคุณภาพแล้ว
- ห้ามเปิด final holdout/family6 หรือ metadata/labels-16695.json
- ไม่เริ่ม GPU/training/collector/observer รอบใหม่ ไม่ขยายรอบเดิมหรือ preview โดยอาศัย handoff เป็นคำอนุญาต
- การยืนยันโค้ด/HTTP/FIM transport ไม่ใช่ detection quality หรือ production acceptance
- ห้ามส่ง raw logs/datasets/weights/keys/passwords/private registry/decisions เข้าแชตหรือ Git

## 3. Production runtime และ Model Quality ที่แก้แล้ว

Unit: nexus-all-events-prod-3006.service, bind127.0.0.1:3006
WorkingDirectory ที่ตรวจ: /mnt/nexus-copilot-mQTssj/release-human-review-no-llm-r2n1_jrx/frontend
ยังเป็น release ของซอร์ส2fd3a6c/LLM retired; source candidates ด้านล่างไม่ได้ถูก deploy ทับ
Production HumanReview ยังไม่ได้ provision named users/catalog/DB หรือเปิด writes จริง
ModelLab773 = DFP666 + Ransomware107 เป็น replayเดิม ไม่ใช่ผลตรวจใหม่

ModelQuality503 แก้แล้วหลังเจ้าของอนุญาต scoped restart3006:
- runtimeเดิมชี้พาธไม่มี quality_report.json/parity_report.json; repoเดิมมีทั้งคู่
- ตรวจด้วย TypeScript validators จาก HEAD และ threshold agreement ผ่าน
- ตรึงสำเนา legacy development reports และ append EnvironmentFile ผ่าน drop-in ใหม่ที่เรียงหลังของเดิม
- HTTP200 และ report hashes ตรง; APIเดิมยังตอบสถานะเดิม; WorkingDirectory ไม่เปลี่ยน
- quality SHA d3855b285168d61f8d60a14eb22cf99aea0b71c948787ed36627e3308b6a0b6d
- parity SHA 331e61e36c34515ff96e281a584dac54adee8541c5df53a7da220b94f1dd5a35
- **นี่คือรายงาน development เก่า ไม่ใช่คุณภาพ DFP/endpoint ใหม่**

ห้ามลบ /mnt/nexus-copilot-mQTssj/model-quality-repair-plan-j2izri20
บริการอ้างถึง model-quality.env และ frozen reports ใน directoryนั้น
ผลจริง: apply-result-private.json; rollback helper: apply-quality-repair.py
manual rollback ใช้เฉพาะเมื่อเจ้าของ/ผู้มีสิทธิ์ร้องขอ:
python3 -B /mnt/nexus-copilot-mQTssj/model-quality-repair-plan-j2izri20/apply-quality-repair.py --rollback
อย่ารัน rollback เป็นส่วนของ read-onlyรับช่วง เพราะจะ restart3006
ห้ามลบ cutover-plan-human-review-_bqyjx2e หรือ review-override.env ที่ releaseเดิมยังใช้อ้างอิง

## 4. บัญชีผู้ทบทวนและ preview — แยกจาก production

เจ้าของเตรียม named reviewer1คนสำเร็จ โดยกรอกรหัสบน VM ผ่าน getpass
Private staging: /mnt/nexus-copilot-mQTssj/human-review-users-staged-56aiy2uv
มี reviewers.json0600 ใน directory0700; ไม่ใช่บัญชีที่เปิดบน productionแล้ว
ไม่ต้องส่งรหัส/registryให้ AI และอย่าสร้างซ้ำเพียงเพราะพบ scriptเตรียมบัญชี

Preview preparation: /mnt/nexus-copilot-mQTssj/human-review-preview-prepared-7bnf620l
Preview unit: nexus-human-review-preview-7bnf620l.service (user unit)
Preview port:127.0.0.1:3013; browserผ่าน tunnel13013
Catalog ว่าง ไม่มี fake alerts แทนผลจริง
Copied registry/private DB ใช้เฉพาะ private-reviewใต้ preparation ไม่ใช่ live human-review root
Buildแยกผ่าน ใช้ dependenciesเดิม ไม่ติดตั้งใหม่ จำกัด2CPU/4GiB/10min
APIunauthenticated GET/POST401; production3006ไม่เปลี่ยน
ภาพ browser จากเจ้าของยืนยัน named login,0รายการ และ PREVIEW banner
ยังไม่พิสูจน์ browserบันทึกความเห็นต่อ alertจริง เพราะยังไม่มี alert

Preview จำกัด1ชั่วโมง เริ่มตาม unitเดิมเท่านั้น
กำหนดหยุดที่รายงาน: **5พ.ย.2026 17:18:43.226620+07 รวมstop grace30s**
ถ้ารับช่วงหลังเวลานี้ ให้ถือว่าต้องตรวจว่า stopped ไม่ใช่เปิดใหม่อัตโนมัติ
การพักล่าสุดไม่ได้สั่ง restart/ต่อเวลา/เปลี่ยน production

## 5. Human Review / Publisher source candidates

**ยังอยู่นอก Git/runtime** ภายใต้ /mnt/.../incoming และ directories ที่แตกไว้
การ commit เอกสารส่งต่อนี้ไม่ใช่การ merge/deploy source เหล่านั้น

ล่าสุด: nexus-evidence-publisher-candidate-20261105.tar.gz
SHA b041e418f4bea46abb971793ee49f7f5a15428f37317d7eaa140b06c22cff5a2
Directory pattern: /mnt/nexus-copilot-mQTssj/evidence-publisher-*/evidence-publisher-candidate
Operator VM ผ่าน47+17Python tests =64 และ16API/DOM groups ทั้งหมด

ความสามารถที่ทดสอบด้วย synthetic fixtures/disposableSQLite:
- immutable catalog snapshots/publication chain, append-only decisions, transactional更新และrollback
- external anchor pin, idempotent retryหลังrevisionเปลี่ยน, conflict/stale rejection
- ประวัติชี้ไปหลักฐาน/คำแนะนำรุ่นที่ตัดสินใจจริง; retired itemsอ่านอย่างเดียว
- named authก่อนอ่านcatalog/DB; viewerห้ามเขียน; POSIX owner/mode/no-followจริงผ่าน
- typed schema v2: evidence {record_ref, identity_contract, sha256}; ไม่เปลี่ยน journal/file refsให้กลายเป็นlegacy event_uid
- v1เก่ายังอ่านในประวัติได้; **production v1 readerยังไม่รองรับv2จนกว่าจะdeploy reader/UIที่ตรวจแล้ว**
- evidence/policy builder ตรวจhash/profiles/feature/model/endpoint/window/record-membership; ปฏิเสธraw fields/foreignscope/classifier semanticsที่ยังไม่รับรอง
- scoreเป็นnative loss/count ไม่แปลงprobability; forced experimental/unknown coverage/investigate-only

ขอบเขต batch foundation:32transitions,20cumulative alert IDs,2MiB snapshot history,100decisions/alert,8MiB response
ยังไม่ใช่ unbounded live feed; ห้ามทิ้งDB/auditเมื่อเต็ม
ยังไม่มี real accepted policy/threshold, trusted producer execution seal, private provisioning/real publication CLI หรือ quality acceptance
hash/flags/profile declarations ไม่พิสูจน์ว่าโมเดลรันจริง/ข้อมูลครบ/labelจริง/physical identityถูกต้อง
Testsผ่านไม่ใช่อนุญาตนำ synthetic policy หรือ alertsไปเติม production/preview

ประวัติแก้ source-binding: การคัด workerจากแชตเคยขาด finalLF จึง16698bytes/hash9d219...
ไฟล์Gitจริง16699bytes/LF1/hash33b1519eebed3827b6a43849a7cc3a58bb636e8a608797121e48e0b78b852a4b
แก้สำเนาและmanifestให้ตรงbytesจริงแล้ว ไม่ได้ normalize bypass ตอนตรวจ
Archive integration9b7d...รุ่นก่อนมีbindingเก่าต้องrepair; เลือกอ่าน publisher packageล่าสุดที่ผ่านแล้วเป็นหลัก

## 6. DFP โมเดลเดิมและ observerเดิม

Existing CPU experiment:
/home/saiuser/edrxdr-nvidia-lab-znmqaTGL/dfp-auth-cpu-development-eoriljcd
2account models,5epochs,218windows:fit74/calibration97/retrospective47; reload parityผ่าน
6features: ssh_auth_success,ssh_auth_failure,pam_session_open,pam_session_close,pam_auth_failure,sudo_invocation
contract linux-journal-auth-observed-counts-engineering-0
Lossไม่ใช่probability ไม่poolModel2ที่ข้อมูลน้อยกับModel1เพื่อทำให้ผลดูดี
ยังไม่เลือกthreshold ไม่independentquality ไม่แทนBERT
อย่าใช้ archive7features/alert10features/Duo/AppShield297แทนกัน

Observer system unit: edrxdr-dfp-auth-prospective-pysjui5a.service
Output: /mnt/nexus-copilot-mQTssj/dfp-prospective-data/dfp-prospective-observation-pysjui5a
เริ่ม5พ.ย.03:59:58.934916+07, max86399seconds
source deadline **6พ.ย.2026ประมาณ03:59:57.934916+07**; serviceเผื่อcleanupตามขอบเขตเดิม
ล่าสุดที่อ่านยังOBSERVING; **เอกสารนี้ไม่ได้ตรวจสถานะปัจจุบันใหม่**
การพักไม่ใช่การสั่งหยุด/เริ่มซ้ำ/ต่อเวลา observerเดิม

คำสั่งอ่านสถานะเท่านั้น:
python3 -B /mnt/nexus-copilot-mQTssj/dfp-observer-v2-package-w1WF8PGn/dfp-prospective-observer/status.py /mnt/nexus-copilot-mQTssj/dfp-prospective-data/dfp-prospective-observation-pysjui5a

Snapshotที่เคยอ่าน:285records,179candidate/106unscored,2accounts,45account-timebuckets
Globalevent-timebuckets41 เป็นคนละตัวนับกับaccount-timebuckets45 ไม่ใช่ข้อผิดพลาดเอง
ยังไม่มี complete/trainingeligiblewindowsที่รับรอง ไม่ได้แปลว่าทุกwindowพิสูจน์ว่าข้อมูลหาย
Pollmetadata1269polls/maxgap32.698701sec/no gap>45sec เป็นsnapshotเก่า ไม่ใช่source completeness

## 7. สาเหตุ unscored ที่ตรวจจากต้นทางแล้ว

Saved projectionเก็บunsupported_message_formatโดยยุบหลายสาเหตุ และไม่เก็บprogram/subreason
Read-onlyprojection audit12testsผ่าน ไม่อ่านjournal/keysแล้วพบกู้subcauseจากprojectionอย่างเดียวไม่ได้
เจ้าของอนุญาตแยกให้ตรวจjournalเดิมแบบboundedและอ่านเฉพาะexperimentHMACkeyในmemoryเพื่อจับคู่
ขอบเขตนั้นเป็นงานตรวจครั้งที่เสร็จแล้ว ไม่ใช่อนุญาตอ่านraw/keysในอนาคตโดยอัตโนมัติ

ผลจริง source review:
- snapshot295records; sourceช่วง2026-11-04T20:59:58.934916Zถึง2026-11-05T10:00:26.141543Z
- target unscored110 จับคู่identity AND payloadตรง110, missing0
- ทั้ง110มีsourcefamilySSHและรูปแบบtransport notice, one_selected_program110
- ไม่มีการreclassify/overwrite originalrecords ไม่เปลี่ยนparser/observer ไม่เก็บ/ส่งrawmessages/keyvalues
- **ไม่ใช่110attacksที่พลาด และรูปแบบnoticeก็ไม่พิสูจน์benignหรือsemanticacceptance**
- source coverage/baselineยังไม่รับรอง ไม่จำเป็นรีบpatchparserที่รันจากunscoredfraction37.2%
Package: nexus-dfp-existing-source-diagnostic-20261105.tar.gz
SHA160d2024bf5674c1303d35a122941c10454572bf62eaace7e7ad1afe018f3bab
อย่ารันซ้ำเป็น routine เพราะจะอ่านต้นทางและคีย์อีก

## 8. หลัง observerจบ: ใช้เครื่องมือที่เตรียมไว้ ไม่เก็บรอบใหม่

Package nexus-dfp-postround-readiness-20261105.tar.gz
SHA b7f1122ae59598f5e3bcbe60ddbca1a914d67e11002c0aa4d6a5d95f2304f1a0
Directory pattern /mnt/nexus-copilot-mQTssj/postround-audit-*/dfp-postround-readiness
10synthetic testsผ่านบนVM; ผลจริงล่าสุดเป็น WAIT_ORIGINAL_OBSERVER_COMPLETION ไม่ใช่postroundPASS

เมื่อรอบจบและunitหยุดแล้ว ค่อยรัน run.pyจากdirectoryที่ตรวจSHAตรง
ตรวจreceipt finalhash,codebindings,SQLite/counts/poll ledger/time/resourceguardsและstableDBhash
อ่านnormalizedDBแบบro/query_only ไม่มีkey/rawjournal/model; สร้างเฉพาะaggregate reportใหม่แยกต้นฉบับ
TechnicalPASSไม่ใช่baseline/coverage/quality/trainingapproval; รายการเหล่านั้นยังnot_assessed
หากยังOBSERVINGจะWAIT ไม่เปิดรอบใหม่; stale receipt/failed/incompleteต้องตรวจ ไม่ฝืนpromote

## 9. Evaluation core ที่เตรียมไว้

Package nexus-dfp-evaluation-core-20261105.tar.gz
SHA c5c86e1377ceb9382f96c797121c0f0f0e44b6fc956bffcebadcd66e439b573a
Directory pattern /mnt/nexus-copilot-mQTssj/evaluation-core-*/dfp-evaluation-core
19synthetic testsผ่านบนVM; ไม่ได้อ่านdata/modelจริง ไม่ได้fit/score/selectthreshold

ตรวจ per-account model/protocolpins,source-membership leakage,chronological/disjoint windows
แยก conditional scored metrics กับ end-to-end eligible metrics; positiveที่ไม่scoredเป็นmissedcaseในpipeline
Unknownlabel/coverageแยกบัญชีไม่ทำเป็นbenign; undefineddenominatorเป็นnull
Falsealert denominatorเฉพาะlabelled-negative entity-windowhours ไม่ใช่เวลาสังเกตทั้งหมด
Latencyที่คำนวณคือwindow-end-to-alert ไม่ใช่attack-onset/response latencyทั้งหมด
ต้องมีreference labels/coverageและpolicyที่ตรึงและรับรองภายนอกก่อนใช้ประเมินจริง; ไม่มีrealprotocolในแพ็กเกจ

## 10. Endpoint controlled testล่าสุด — จบและคืนค่าแล้ว

เจ้าของอนุญาตfresh scratch12plain-text files และ20modificationsใน3cases
ไม่มีมัลแวร์/encryption/deletionของข้อมูลจริง ไม่เฝ้าทั้งdrive ไม่เปิดwhodata
realtimeFIMเฉพาะscratch, restartlocalwazuh-agentตอนเปิด/คืนค่า, independentrestoretimer10minก่อนconfigwrite

14testsผ่าน; ผล VMจริง:
- quiet-small-edits:4modified events/4unique paths
- normal-bulk-update:8modified events/8unique paths
- controlled-fast-update:8modified events/8unique paths
- all20path+sha256_after matches true, duplicates0,foreignagent0,missingidentity0,wrongmode/event0
- normal_bulk_and_controlled_fast_have_same_case_aggregate_signature=true
- ไม่เลือกthreshold ไม่เรียกโมเดล ไม่อ้างransomwarequality/sourcecoverage
- RESTORE_PASS หลังcasesจริง; agentactive; CONTROLLED_COMPARISON_FINISHED

Private evidence: **/var/lib/edrxdr-endpoint-probes/probe-3nbmtzzn**
เก็บoriginal.conf/receipt/restored/privatecase timestamps/comparison-aggregateไว้ ไม่ลบ/เปิดเผยprivateconfig
Package nexus-endpoint-controlled-cases-20261105.tar.gz
SHA dac2a73296045348cd2f776f60d554774cae82e66e95dfebe5b46cf580380aa6
Directory pattern /mnt/nexus-copilot-mQTssj/controlled-cases-*/endpoint-controlled-cases
**อย่ารันapplyซ้ำจากhandoff** งานทดสอบนี้จบแล้ว

ข้อสรุปจำกัด:สองcasesให้aggregatecountsที่ทดสอบเหมือนกัน จึงใช้aggregateนั้นแยกสองcasesนี้ไม่ได้
ไม่เท่ากับพิสูจน์ว่าfulltime-windowfeaturesทุกชนิดเหมือนกัน หรือโมเดลทุกแบบทำไม่ได้
ต้องreview richerprocess/content/timing featuresและnuisancebehaviorพร้อมindependenttestsก่อนอ้างransomwareclassifier
การมีWazuhrule/format/testscenario labelไม่ใช่attack groundtruth
FIM/SSH/sudo/testingactivityระหว่างobserverต้องคงexperimentalcontext ไม่labelทั้งหมดbenign

Probeเก่า12/12ที่ /var/lib/edrxdr-endpoint-probes/probe-8yug2fer ยังเป็นหลักฐานtransportเดิม อย่าลบ
SourceFIMoriginal configคืนค่าแล้ว ไม่ได้เปิดเฝ้าrealprotectedfolderหรือscratchต่อเนื่อง

## 11. สิ่งที่ทำต่อได้เมื่อเจ้าของกลับมา

1. ตรวจ Git/HEAD/WIP/runtime/observerเดิมแบบread-onlyก่อน ไม่รีบdeploycandidate
2. ถ้าobserverจบ ใช้postroundaudit แล้วreviewsourceexposure/retention/context/identity/normalbaseline
3. ตรึงsource/feature/identity/time/lateness/missingness,splits/reference/evaluation/alertbudgetก่อนcalibration
4. ยืนยันเกณฑ์สอบและprotectedpathจากเจ้าของ ห้ามเลือกเองหรือใช้testcountsแทนclassifierที่โจทย์บังคับ
5. ใช้existingCPUmodelตามcontractเดิมเมื่อมีscopedapprovalและhashbindingsครบ ไม่เริ่มfit/GPUใหม่อัตโนมัติ
6. ตรวจtrustedproducerexecution/outputsealและrealpolicyหลักฐานก่อนpublishเข้าHumanReview; ไม่ใช้syntheticthresholdจากtests
7. ก่อนprovision/preview/productionwritesต้องแผนและrollbackที่อนุญาตแล้ว รักษาaudit/cataloghistory
8. ทำrealcontrolled/normal/independentquality,E2E/latency/retry/rotation/resourcesตามscope; BERTcutoverแยก,automatedresponseปิด

## 12. คำสั่งเริ่มรับช่วงแบบอ่านอย่างเดียว

cd /home/saiuser/EDRXDR-Morpheus || exit 1
GIT_OPTIONAL_LOCKS=0 git branch --show-current
git --no-pager log -5 --oneline
GIT_OPTIONAL_LOCKS=0 git status --short
git --no-pager diff --stat
git --no-pager diff --cached --stat
systemctl --user show nexus-all-events-prod-3006.service --no-pager -p ActiveState -p SubState -p WorkingDirectory
systemctl show edrxdr-dfp-auth-prospective-pysjui5a.service --no-pager -p LoadState -p ActiveState -p SubState -p Result
systemctl --user show nexus-human-review-preview-7bnf620l.service --no-pager -p LoadState -p ActiveState -p SubState

อย่าส่งenvironment/registry/password/rawlogsหรือprivatedecisionsกลับแชต
เอกสารนี้คือสถานะส่งต่อ ไม่ใช่อนุญาตทำงานทดลอง/เปลี่ยนruntimeหรือเปิดรอบใหม่
