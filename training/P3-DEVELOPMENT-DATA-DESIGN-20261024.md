# P3: provenance ledger และ split manifest — draft 24 ต.ค. 2026

สถานะ: design only; ไม่มีการสร้าง training examples, เปิด holdout, แบ่ง dataset, scoring, เปลี่ยน threshold หรือใช้ GPU

## หลักฐานตั้งต้น

Snapshot ภายใน VM: `/home/saiuser/nexus-quality-snapshot-ixl2h41e`

| รายงาน | SHA256 ที่ผู้ดูแลรายงาน |
| --- | --- |
| inventory.json | `8b4f56796c1d4d6d5bc71b4172ffb10bc3d78c09185ed1396f3adde1f6ae18c6` |
| target-cohort-profile.json | `773832d5b87cf3a321fd8bf3995b083233ddbe065fb19327a2d1f295b2209a9e` |
| manifest.json | `6e894fc90fde4e7b26e008ef3ba90e3714e133dc947c3a3241d92c272bbd56bb` |
| source-before.json | `9a4919790db96bbee9b5f6b8cd603f758e5ea3e34c595f7709b6dd031c24d74c` |

Manifest มี metadata ของไฟล์ 14 รายการ; source-before ครอบคลุมชื่อ archive วันที่ 09–22 โดยยังไม่ได้ตรวจความหมายของแต่ละ field หรือเทียบ hashes รายไฟล์ในรอบนี้

`source_stable_during_copy=true` ยืนยันตามข้อความใน manifest เท่านั้น ยังไม่ใช่การตรวจ source hashes ใหม่หรือหลักฐาน origin รายเหตุการณ์

Manifest ยังระบุ `event_dates_not_yet_verified=true` และ `lab_and_replayed_events_not_yet_classified=true` ขณะที่ inventory รายงาน date-range/timezone issues เป็น 0 ให้เก็บทั้งสองหลักฐานพร้อม hash แยกกัน อาจเป็นผลคนละขั้นตอน ห้ามแก้ flag ใน snapshot หรือสรุปว่า provenance ผ่านจากผล date check

## A. Provenance ledger ภายใน VM

หนึ่ง record ต่อ cohort ที่มี membership อ้างอิงชัดเจน; ถ้าต้นทางหรือสถานะต่างกันต้องแยก record ไม่รับรองทั้ง rule จากตัวอย่างเดียว

| Field | ความหมายและข้อกำหนด |
| --- | --- |
| schema_version / ledger_id | รุ่น schema และ ID ของ ledger; สร้างใหม่เมื่อข้อกำหนดเปลี่ยน |
| cohort_id | ID ที่คงที่ ไม่ใส่ raw log, hostname หรือ path ของเหตุการณ์ |
| snapshot_report_hashes | hashes ของ inventory/profile/manifest/source-before ที่ใช้จริง |
| membership_ref / membership_sha256 | อ้างไฟล์สมาชิกภายใน VM และ hash; ตอนนี้ยังไม่สร้างไฟล์หรือเดารายชื่อสมาชิกจาก counts |
| member_count / rule_ids / weak_label_basis | จำนวน, rules และเหตุผล weak severity label; ไม่ใช่ analyst-confirmed attack label |
| utc_window / source_group_refs | ช่วงเวลาและ manager-agent group IDs ภายใน VM; ห้ามส่ง identity จริงออกภายนอก |
| origin_kind | `unknown`, `lab`, `replay`, `operational`, `mixed`; เริ่ม `unknown` และแยก mixed ให้ละเอียดก่อนใช้ |
| provenance_status | `unestablished`, `marker_only`, `verified`, `conflict`; เริ่ม `unestablished` |
| evidence_refs | reference/hash ของ source metadata และ scenario/change record ที่ตรวจได้จริง ไม่ฝังข้อความดิบ/secret |
| verification | reviewer, เวลา UTC, วิธีตรวจ, ขอบเขตที่ตรวจ; เว้นว่างจนมีการตรวจจริง |
| protected_membership_status | `unchecked`, `excluded`, `clear`, `conflict`; `clear` ต้องผ่าน metadata comparison ที่ได้รับอนุญาต |
| input_contract / missingness | รุ่น text builder/tokenizer และ counts missing/truncation; ไม่เปลี่ยน v2 input เงียบ ๆ |
| template_policy_ref / template_group_ref | รุ่น normalization/grouping และ reference ของกลุ่ม; ข้อความต่างกันไม่เท่ากับ template ต่างกัน |
| eligibility / exclusion_reasons | เริ่ม `pending_review`; ห้ามถือ `verified` เพียงอย่างเดียวเป็นสิทธิ์ฝึก |

การยืนยัน provenance ต้องผูก source reference + UID/hash ที่ตรวจย้อนกลับได้กับบันทึกเหตุการณ์/ผู้รับผิดชอบที่ได้รับอนุญาต; marker และความคงที่ตอน copy เพียงอย่างเดียวไม่พอ หากไม่มีหลักฐานให้คง unestablished ไม่สร้าง origin ขึ้นเอง

ใช้ canonical serialization และ digest ตาม policy ที่กำหนดก่อนสร้าง membership; การ hash ID ไม่ทำให้ข้อมูลเป็น anonymous โดยอัตโนมัติ

## B. สถานะ target ปัจจุบัน (aggregate เท่านั้น)

- Rule 550 รวม 55 high: 54 แถวยังไม่ยืนยัน lab origin; 1 แถวพบ known lab marker แต่ยังไม่ยืนยัน provenance ครบ ทั้ง 55 มี syscheck/path
- Rule 2901 รวม 7 low: ยังไม่ยืนยัน lab origin ทั้ง 7 แถว; ไม่ใช่ validation เดิม 258 แถว
- ตัวเลขนี้เป็น review queues ไม่ใช่ cohort membership manifests หรือ training splits
- Rule 2901 ต้องถูกกันออกจาก train ตามข้อกำหนดเดิม ไม่ย้ายเข้า train เพื่อแก้คะแนน แม้เป็น UID ใหม่

## C. Split manifest แบบ draft

เริ่มด้วย `status=draft_unassigned`, `training_allowed=false`, `gpu_execution_allowed=false`, train/dev/holdout assignments ว่าง และ `protected_membership_verified=false` การสร้างแบบออกแบบนี้ไม่ออกสิทธิ์เปิด reserve

Manifest ต้องมี:

1. Schema/policy versions, snapshot hashes, provenance ledger hash และวันที่ freeze
2. References และ hashes ของ protected manifests เดิม โดย metadata review ที่ได้รับอนุญาต; ไม่อ่าน raw text หรือผล reserve เพิ่มเพื่อจูน
3. Input contract และ missingness/truncation policy; ไม่เติม feature จากอนาคตหรือ rule.level/label เข้าโมเดล
4. UTC cutoff/windows, manager-agent grouping และ template/duplicate grouping policy ที่ freeze ก่อนเลือกโมเดล/threshold
5. สมาชิกหรือ reference/hash ของสมาชิกแต่ละ split พร้อม counts/rules/time/source groups; ยังไม่กำหนด ratios/cutoffs จากข้อมูลไม่ครบ
6. รายงาน overlap ตาม UID/source identity/exact text/template groups และการจัด connected components; ถ้าข้าม time/endpoint boundaries ให้ exclude หรือ redesign และบันทึกเหตุผล ไม่แยก component เงียบ ๆ
7. Coverage matrix ของ positive และ low cohorts ตาม rules/scenarios/time/endpoint/provenance/missingness พร้อม unresolved items
8. Approval record ของ split/evaluation plan และ holdout access policy; ไม่เปิดผล holdout จนได้รับอนุญาตตาม gate เดิม

## D. Gates ก่อนเสนอโมเดลทดลอง

- Source integrity: ตรวจความหมายของ metadata ก่อนคำนวณ/เทียบ hashes; ตรวจรายไฟล์ภายใน snapshot โดยไม่แตะ shared source container หากไม่จำเป็น
- Provenance: eligible cohorts ต้องยืนยัน origin และสิทธิ์ใช้งาน; unknown/marker_only/conflict ไม่เข้า train อัตโนมัติ
- Protected sets: ไม่มี protected membership ถูกย้าย; rule 2901 ไม่เข้า train; ไม่ใช้ reserve เพื่อเลือก features/checkpoint/threshold
- Leakage: group separation ผ่านหรือระบุว่าออกแบบแยกไม่ได้; ไม่อ้างความเป็นอิสระจาก distinct text counts
- Positive diversity: มีหลาย positive rules/scenarios/time/source groups ที่ยืนยันที่มา พร้อม low controls; ถ้ายังไม่พอให้ INCONCLUSIVE ไม่ใช้จำนวนแถวรวมชดเชย coverage
- Freeze: ทีมเห็นชอบ metrics/subgroup gates, evaluation protocol และ baseline comparisons ก่อนทดลอง
- Execution: ต้องมี GPU reservation/guard ใหม่และคำสั่งผู้ใช้แยกต่างหาก ห้ามเริ่ม training/inference จาก design นี้

## งาน read-only ถัดไป

ตรวจเฉพาะชื่อและชนิด field ใต้ `manifest.files` กับ `source-before` เพื่อกำหนด integrity check ให้ตรง schema ก่อนอ่าน archive/hash payload จากนั้นหาเฉพาะ metadata ที่ยืนยัน provenance ได้บน VM ภายใต้สิทธิ์เดิม ไม่เปิด raw logs/datasets/weights ส่งออกภายนอก
