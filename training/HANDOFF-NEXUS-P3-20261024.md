# ส่งต่อ NEXUS P3: data readiness review — 24 ตุลาคม 2026

## สถานะรับช่วง

รอบนี้ทำ CPU/read-only review และเพิ่มเอกสารจากผลที่ผู้ดูแลรันบน VM ไม่ได้ฝึก/score โมเดล เก็บข้อมูลใหม่ สร้าง lab event หรือเปลี่ยน runtime

- Repo: `/home/saiuser/EDRXDR-Morpheus`; branch ที่ยืนยันล่าสุด `work/nexus-exact-ai-v1`; HEAD ก่อนเอกสาร P3 `fe2307c`
- ต้องตรวจ HEAD/status ปัจจุบันก่อนทำงานต่อ มี frontend WIP และ untracked งานเดิม ต้องรักษาไว้
- สิทธิ์อ่านข้อมูลเดิมรอบนี้: Agent003/004 ถึง **24 ต.ค. 2026 04:00 ICT เท่านั้น** ไม่ใช่สิทธิ์ GPU/lab/training และไม่ต่ออายุอัตโนมัติ
- รับไฟล์ที่ `/mnt/nexus-copilot-mQTssj/incoming/`; ไม่วางแพ็กเกจใน home หรือ `/tmp`

## ข้อสรุปที่ต้องใช้ต่อ

**Integrity ผ่าน แต่ยังไม่มีข้อมูล P3 ชุดใดได้รับสิทธิ์เข้า train จากการตรวจนี้**

1. Snapshot มี 19,994 แถว/UID, 90 กฎ, 6 manager-agent pairs; missing full_log=11,004, missing description=7
2. Manifest/source-before hashes ตรงกัน 14/14 และคำนวณ hash ของ compressed archives จริงตรง manifest 14/14; ไม่ใช่หลักฐาน provenance หรือ independent source authenticity
3. Rule550 เชื่อมกับ recorded FIM lab evidence ได้หนึ่งแถวด้วย canonical UID, metadata และ file hashes อีก 54 แถวยังไม่ยืนยัน; การเชื่อมนี้ไม่พิสูจน์สมาชิกของ marker-only bucket หรือ independently authenticate original lab execution
4. Rule550 อยู่ quarantine_old_test เดิม 157 แถว จึงกัน P3 rule550 ทั้ง 55 แถวออกจาก train แม้ UID ใหม่หรือมี lab evidence
5. Rule2901 อยู่ validation เดิม 258 แถว จึงกัน P3 ใหม่ 7 แถวออกจาก train ห้ามย้าย rule เข้า train เพื่อแก้คะแนน
6. กฎใน validation/quarantine/reserve อื่นต้องคง protection เช่นกัน ส่วนกฎ train เดิม/กฎใหม่ยังต้องตรวจ provenance, overlap, coverage และ policy ก่อนใช้

`P3-PROTECTED-RULE-DECISION-20261024.md` ใช้ตัดสิน **training eligibility** แทนคำว่า pending ของ rule550/2901 ใน baseline/design/link notes ที่เขียนก่อนหน้า เก็บเอกสารเดิมเป็นประวัติ ไม่แก้ snapshot หรือย้ายข้อมูลจริง

## Aggregate policy classification

| กลุ่ม | Rules | High | Low |
| --- | ---: | ---: | ---: |
| Existing train rules — review required | 23 | 1,796 | 5,229 |
| Protected validation rules | 4 | 548 | 1,187 |
| Protected quarantine rules | 4 | 304 | 1,604 |
| Protected reserve rules | 6 | 579 | 687 |
| Unseen rules — policy/provenance review required | 53 | 55 | 8,005 |

คำว่า unseen หมายถึงไม่พบใน checkpoint dataset manifest ที่ตรวจ ไม่ใช่ proof ว่าไม่มี row/template overlap หรือเป็น novel threat

Manifest SHA256 ที่แนบ checkpoint: `354e3c9dc9febe49173fa416cdd943cf3512540dded5f18e0ae3d800908b8669`; training report บันทึก hash ตรงและ smoke=false ยังไม่ได้ยืนยัน runtime model/weights binding สดในรอบนี้

## Positive diversity และ field availability

- High ใน unseen rules มี 11 rules รวม 55 แถว ไม่ใช่เฉพาะ rule550 ตามข้อสงสัยตอนเริ่มรับช่วง
- Rules: 202, 203, 204, 2502, 19004, 19005, 19014, 60110, 60602, 60776, 61110
- ขาด full_log 47/55; แต่ละ rule มี high เพียงหนึ่ง manager-agent pair และจำนวน 1–24 แถว
- ภายใน Agent003/004 ที่ได้รับสิทธิ์พบ 54 high: Agent004=53 จาก 9 rules, Agent003=1 จาก rule2502; rule19004 ไม่พบในสอง agents นี้
- ในขอบเขตสอง agents ขาด full_log 46/54 และไม่มี low ใน 11 positive rules เหล่านี้ ไม่ได้หมายความว่าไม่มี low ที่บริบทเกี่ยวข้องในกฎอื่น
- High ใน existing train rules กระจุกที่ rule23505=1,370/1,796 แถว จึงไม่ใช้จำนวนรวมแทนความหลากหลาย

## Coarse controls และ rule semantics

พบ 103 coarse links ที่ใช้ same manager-agent, same UTC day และ shared rule.groups; ไม่ใช่ 103 unique benign examples และอาจซ้ำข้าม links

อ่าน definitions ปัจจุบันเฉพาะ 9 กฎจาก verified project `wazuh`/service `wazuh.manager`; ตรวจ container identity ก่อน/หลัง ไฟล์ XML ของกฎเป้าหมายไม่ถูกแก้ไข

- Rules202/203/204 คือ reported queue load/full/flooded; rule205 คือ reported return to normal load ไม่ใช่ independent attack/benign labels
- Rule19014 คือ SCA NA→failed; rule19015 คือ NA→passed ต้องเทียบ policy/check/title และยังไม่พิสูจน์ policy version เดียวกัน
- Rule19005 เป็น SCA summary score; ไม่จับคู่กับ per-check transitions โดยตรง
- กฎ SCA ที่ตรวจมี `no_full_log` จึงอาจ missing โดยตั้งใจ ห้ามเหมารวม full_log ที่หายทั้งหมดเป็น collection failure และยังไม่ยืนยัน historical rule versions
- ตัวอ่าน XML รุ่นแรกติด ParseError ในไฟล์ Exchange ที่ไม่ใช่เป้าหมาย รุ่นสองเลือก literal target-rule files ก่อน parse; ไม่แก้ไฟล์นั้น ไม่สรุปว่า Wazuh parser/runtime เสีย และไม่ตรวจความถูกต้องของ XML นอกเป้าหมาย

## ผล event-context review

Queue: high 7 แถวและ normal 3 แถว usable ครบ จัดเป็น temporal candidates 3 กลุ่ม Agent004 ไม่มี high ค้างใน candidate grouping นี้

| UTC | First high → reported normal (ICT) | ระยะจาก first high |
| --- | --- | ---: |
| 2026-10-17 02:02:12.014–02:03:00.383 | 17 ต.ค. 09:02:12.014–09:03:00.383 | 48.369 s |
| 2026-10-19 14:49:32.269–14:50:29.848 | 19 ต.ค. 21:49:32.269–21:50:29.848 | 57.579 s |
| 2026-10-21 11:18:57.725–11:19:29.321 | 21 ต.ค. 18:18:57.725–18:19:29.321 | 31.596 s |

ไม่ใช่การยืนยัน causal recovery/incident episodes หรือ sustained healthy intervals; ต้องมี change/run record ของ Agent004 ผูกกับเหตุการณ์ก่อนระบุ origin

SCA: 19014 สองแถว และ 19015 หนึ่งแถว usable ครบ แต่ policy/check/title matching groups=0; single-outcome groups=3 จึงยังไม่มี matched SCA controls และ NA→failed/NA→passed ไม่ใช่ proof ของ failed→passed โดยตรง

เอกสาร COMPANY-SCOPE-20261014, NEXUS-SHARED-HOST-20261017 และ SEVERITY-FLOW-20261013 ที่อ่านไม่เชื่อมกับกิจกรรมคิวสามช่วง; tests วันที่13/14ไม่ยืนยันเหตุการณ์วันที่17/19/21 การค้นชื่อ activity metadata ใน `training/evidence` ตามวันที่และรูปแบบชื่อที่กำหนดไม่พบ ไม่ใช่ proof ว่าไม่มีหลักฐานที่อื่น

## Evidence index: private metadata reports only

| รายงาน | Directory ใต้ `/mnt/nexus-copilot-mQTssj/` | result.json SHA256 |
| --- | --- | --- |
| FIM exact linkage | p3-provenance-26ufeeo7 | `a9724e3ccadb137bf5a0b827e9cd3a2a113188346affd091d141de11b410bca0` |
| Rule policy | p3-rule-policy-zhcbvmd6 | `266f93ed52b941b14befb57d9be96ecf0e53bd187a4e3e3b73a74bcb83f8e66f` |
| New-rule profile | p3-new-rule-profile-e_lzng32 | `c35dc7e32c739458e4c7bb0042f58d1bd2e6db6547f74917e4584ff6be289d49` |
| Authorized agent profile | p3-agent003004-profile-esxesgj3 | `e9e1ec15839c53ff597fbb2789bcd72d1b55a62c8c797364cc87e43d33807fdc` |
| Coarse controls | p3-low-control-review-uujc2u_x | `a9cca61fa1961304a4024dd1c3dfae4ea32252db40e703f7c393bbe453547365` |
| Current definitions | p3-rule-definition-review-5psu0_1u | `69cb593a7102adc6bedb63fd678fe1f1fb5f235f72f5e61192c4304196bf9cd8` |
| Event context | p3-event-context-review-nmatsits | `e294ead075a599f8307160dbfa51ca9100c5602498f42cab2f3d44ded1faa5f4` |

เอกสารรายละเอียดอยู่ใน `training/BASELINE-P3-20261024.md` และไฟล์ `training/P3-*-20261024.md` ที่เกี่ยวข้อง รายงาน row-level/identities อยู่บน VM ตามสิทธิ์ ไม่รวม raw logs/datasets/weights ใน repo หรือแพ็กเกจส่งต่อ

## งานถัดไป

1. ตรวจและ commit เฉพาะเอกสาร P3 หลัง review ไม่ใช้ `git add .`; คง frontend/งานเดิมไว้
2. ขอ approved change/run records ของ Agent004 สำหรับสามช่วงคิว ไม่เดาว่าเป็น lab หรือเหตุการณ์ปกติ ถ้าไม่มีให้คง unestablished
3. หากจะเก็บเพิ่ม ใช้ `P3-DEVELOPMENT-COLLECTION-PLAN-20261024.md` เป็นข้อเสนอ เจ้าของ endpoint ต้องอนุมัติ scenario, ขอบเขต, เวลา, budget และ rollback แยกต่างหาก
4. คง whole-rule protected policy; ทำ provenance ledger, overlap/connected groups และ time/source/template split protocol ให้ได้รับอนุมัติก่อน admission/training
5. ไม่เลือก threshold/checkpoint จาก protected results; model quality ยังไม่ผ่านตามผลรับช่วง ไม่มีผลคุณภาพใหม่ใน P3

## Guardrails

- เมื่อเลย 04:00 ICT วันที่24 ต.ค. ต้องขอช่วงอ่านข้อมูลใหม่ก่อนทำ data review ต่อ
- GPU ใช้ร่วมกับ LuckyFive ต้องมี reservation/guard ใหม่และคำสั่งผู้ใช้ก่อนใช้ ห้ามหยุด process เพื่อน
- BlueField/rshim และ automated response ต้อง OFF; ไม่แก้ driver/network/shared stack/systemd หรือ build ทับ runtime .next
- ไม่ reset/consume lag หรือขยับ offset; ไม่เปลี่ยน live weights/threshold หรือสรุป production readiness จาก metadata review
- สถานะ runtime/service/GPU สดและ reboot persistence ไม่ได้ตรวจใหม่ใน P3; ใช้ supervisor handoff เป็นประวัติและตรวจสดแบบ read-onlyเมื่อได้รับสิทธิ์
