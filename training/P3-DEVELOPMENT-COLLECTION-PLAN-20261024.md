# P3: แผนเก็บ development data และเกณฑ์รับข้อมูล — 24 ต.ค. 2026

**สถานะ: proposed plan; ยังไม่อนุมัติการเก็บข้อมูล/สร้างเหตุการณ์/ฝึกโมเดล**

เอกสารนี้จัดทำจากผล aggregate ที่ผู้ดูแลรายงาน ไม่ใช่ผลทดลองโมเดลใหม่ การเพิ่มไฟล์นี้ไม่เปลี่ยน configuration, split, threshold หรือสิทธิ์ GPU

## 1. ปัญหาที่ต้องแก้

- Snapshot P3 มี 19,994 แถว / 90 กฎ / 6 manager-agent pairs; ขาด full_log 11,004 แถว
- กฎที่ไม่พบใน checkpoint manifest เดิมมี 53 กฎ; 11 กฎมี high รวม 55 แถว และไม่พบ low ภายใน 11 กฎนั้น
- แต่ละกฎ high พบเพียงหนึ่ง manager-agent pair; ยังไม่ตรวจว่าข้ามกฎเป็นคู่เดียวกันหรือไม่
- High 47/55 แถวขาด full_log; 8 แถวที่มีมาจาก rules 202/203/204/2502
- จำนวนข้อความ/วันไม่ยืนยัน template diversity หรือ independent incidents; high/low เป็น weak severity labels ไม่ใช่ confirmed attacks/benign labels
- Provenance ของกลุ่มใหม่และ row/template overlap ยังไม่ยืนยัน ไม่มีข้อมูลชุดใดได้รับสิทธิ์เข้า train จากแผนนี้

## 2. หลักฐานและข้อกำหนดที่ต้องรักษา

| รายการ | หลักฐานที่รายงาน |
| --- | --- |
| Snapshot archive integrity | 14/14 hashes ตรง manifest; metadata ไม่เปลี่ยนระหว่างตรวจ |
| Inventory SHA256 | `8b4f56796c1d4d6d5bc71b4172ffb10bc3d78c09185ed1396f3adde1f6ae18c6` |
| Checkpoint dataset manifest SHA256 | `354e3c9dc9febe49173fa416cdd943cf3512540dded5f18e0ae3d800908b8669` |
| Rule-policy report SHA256 | `266f93ed52b941b14befb57d9be96ecf0e53bd187a4e3e3b73a74bcb83f8e66f` |
| New-rule metadata profile SHA256 | `c35dc7e32c739458e4c7bb0042f58d1bd2e6db6547f74917e4584ff6be289d49` |

Rule550 อยู่ quarantine_old_test เดิม 157 แถว: กัน P3 ทั้ง 55 แถวออกจาก train ตาม whole-rule policy แม้เชื่อม recorded lab evidence ได้หนึ่งแถวแล้ว

Rule2901 อยู่ validation เดิม 258 แถว: กัน P3 ใหม่ 7 แถวออกจาก train เช่นกัน ห้ามย้าย rule นี้เข้า train เพื่อแก้คะแนน

Rules/สมาชิกเดิมใน validation, quarantine และ reserve ทุกชุดต้องคงเดิม ไม่ใช่เฉพาะ 550/2901 ไม่เปิด holdout text/results เพิ่มเพื่อเลือกข้อมูลหรือจูนโมเดล

## 3. ลำดับงานและขอบเขตการอนุมัติ

1. **Metadata/source review:** ตรวจ definition และเวอร์ชันของ 11 กฎ, source references, provenance records และสิทธิ์เจ้าของข้อมูลภายใน VM ไม่อนุมาน scenario จากหมายเลขกฎ
2. **Scenario proposal:** เจ้าของข้อมูล/endpoint เลือกสถานการณ์และกิจกรรมปกติที่เกี่ยวข้อง กำหนด expected observation, weak severity และข้อจำกัดของ label ก่อนรัน
3. **Collection approval:** ต้องระบุเจ้าของ endpoint, ขอบเขตไฟล์/ข้อมูล, คำสั่งที่อนุญาต, ช่วงเวลา, ปริมาณ/พื้นที่เก็บ, stop condition, ผู้ rollback และสิทธิ์ดูข้อมูลจริงให้ครบ
4. **Split protocol approval:** กำหนด rule ownership, time/endpoint/template separation และ evaluation plan ล่วงหน้า ก่อนสร้าง examples หรือทดลองโมเดล
5. **Approved acquisition:** ทำได้เมื่อมีคำอนุมัติเก็บข้อมูลแยกต่างหาก ไม่เปิด GPU อัตโนมัติ ไม่สร้าง lab event บน shared VM จากเอกสารนี้
6. **Admission review:** ตรวจ provenance, integrity, protected overlap และ coverage แล้วออก membership manifest ที่มี version/hash โดยผู้รับผิดชอบ
7. **Experimental training proposal:** เสนอได้หลังผ่าน admission/split review; ต้องมี GPU reservation/guard และคำสั่งผู้ใช้ใหม่ก่อนรันจริง แยกจาก live model

## 4. กลุ่มที่จะพิจารณา ไม่ใช่ training assignments

| กลุ่มเป้าหมาย | กฎ | งานที่ต้องทำก่อนคัดเลือก |
| --- | --- | --- |
| มี full_log ใน snapshot แต่ตัวอย่างน้อย | 202, 203, 204, 2502 | ยืนยัน source/scenario, สิทธิ์ใช้งาน และเก็บบริบทจากหลาย source/time groups ที่ได้รับอนุญาต |
| ขาด full_log ใน high ทั้งกลุ่ม | 19004, 19005, 19014, 60110, 60602, 60776, 61110 | หาสาเหตุ missingness และข้อจำกัดการเก็บก่อนตัดสินใจว่าจะมี context จริงเพิ่มได้หรือเป็น description-only cohort |
| Low controls | ยังไม่กำหนด rule IDs | เลือกกิจกรรมปกติจากบริบทที่เกี่ยวข้องและกฎที่ไม่ protected ตามนโยบายที่อนุมัติ ไม่สุ่ม low จำนวนมากเพียงเพื่อปรับสัดส่วน |

ไม่ลด Wazuh level หรือแก้ผลเดิมเพื่อสร้าง low ไม่ถือว่า lab event คือ attack และไม่สร้าง text ปลอมแทน full_log ที่หาย

Existing train-rule high 1,796 แถวมี rule23505 ถึง 1,370 แถว จึงไม่ใช้ปริมาณรวมเป็นหลักฐานความหลากหลาย หรือเติมข้อมูลตามสัดส่วนเดิมโดยไม่ตรวจ subgroup coverage

## 5. Collection matrix ที่ต้องตกลงก่อนเก็บ

แต่ละ scenario ต้องระบุ rule definition/version, origin lab/replay/operational, allowed source groups, time blocks, semantic template families, high/low controls, expected fields และเจ้าของอนุมัติ

เป้าหมายเชิงออกแบบคือหลาย positive rules/scenarios, หลาย independent source groups และหลายช่วงเวลา ไม่ยอมรับเพียงการรัน template เดิมซ้ำเพื่อเพิ่มจำนวน ไม่มีขั้นต่ำจำนวนแถวหรือจำนวนเครื่องที่รับรองความพร้อมจาก P3 นี้ ต้องกำหนด sampling budget และจำนวนที่พอประเมิน uncertainty ตาม subgroup ก่อนเก็บ

Low controls อาจอยู่คนละ rule ในบริบทเดียวกัน ไม่บังคับให้ static high rule ต้องมี low ด้วยการเปลี่ยน label หาก field ไม่สามารถเก็บได้ตามสิทธิ์ ให้เก็บ missingness reason และรายงาน coverage ไม่ครบ

ข้อมูล description-only ต้องแยก cohort และวัดผลแยก ห้ามปนแล้วอ้างว่าโมเดลเห็น full context หรือเติม full_log จากข้อมูลอนาคต

## 6. เกณฑ์รับข้อมูลเข้า candidate pool

| Gate | ต้องมี | หากไม่ผ่าน |
| --- | --- | --- |
| Authority | ขอบเขตใช้งานและผู้อนุมัติที่ระบุได้ | pending/excluded; ไม่คัดลอก raw เพิ่ม |
| Provenance | Source reference/hash เชื่อมกับ scenario/change record และผู้ตรวจได้ | unestablished/marker_only/conflict; ไม่เข้า train |
| Integrity/identity | Hash, canonical identity, exact source refs และ UTC timestamp ตรวจได้ | แยก review; ไม่แต่ง timestamp/UID |
| Protected boundary | Metadata comparison ที่ได้รับอนุญาตและ whole-rule policy ผ่าน | กันออกจาก train; ไม่ย้าย protected rules หรือสมาชิก |
| Contract | รุ่น input builder/tokenizer, field availability/type และ truncation policy ชัดเจน | หยุด review หรือเสนอ contract ใหม่อย่างเปิดเผย |
| Leakage | UID/source identity/exact text/template grouping และ time/source separation ตรวจตาม policy | กัน connected groups ออกหรือ redesign; ห้ามสุ่มแถวแก้ให้ตัวเลขผ่าน |
| Coverage | Coverage matrix high/low, rules/scenarios/time/source groups พร้อม limitations | INCONCLUSIVE; ไม่ชดเชยด้วย duplicate/repeated events |

ผ่าน integrity หรือ provenance อย่างเดียวไม่เท่ากับผ่าน admission และการผ่าน candidate-pool admission ไม่ได้อนุมัติ training/deployment

## 7. Split และ evaluation protocol

- Frozen protected manifests เดิมไม่เปลี่ยน original validation ที่ใช้วิเคราะห์แล้วไม่ใช่ fresh holdout อีกต่อไป; reserve เดิมคง one-time policy เดิม
- กำหนดก่อนว่า unseen rules ใหม่จะใช้พัฒนา หรือกันไว้ประเมิน/สำรอง โดยได้รับความเห็นชอบ ห้ามยกเลิก whole-rule protection เงียบ ๆ
- กำหนด UTC windows และ manager-agent grouping จากแผน prospective พร้อม template/duplicate connected components ให้อยู่ฝั่งเดียว; ไม่ใช้ row random split เป็นทางลัด
- หากรักษา whole-rule และ time/endpoint/template separation พร้อมกันไม่ได้ ให้รายงานและ redesign ไม่แยก component เพื่อเพิ่ม coverage
- นิยาม template policy ก่อนประเมิน overlap; hashing/normalization ไม่รับรอง anonymity หรือไม่มี leakage และไม่แก้ live v2 input contract
- แยกคำถาม seen-rule performance ออกจาก unseen-rule generalization รายงาน micro/macro, subgroup counts, TP/FP/TN/FN, missingness/truncation และ group uncertainty ตาม protocol ที่อนุมัติ
- ห้ามใช้ผล protected reserve เพื่อเลือก features/checkpoint/threshold การเลือก threshold ของโมเดลทดลองต้องใช้ development protocol ที่อนุมัติ และไม่เปลี่ยน live threshold อัตโนมัติ
- เป้าหมาย numeric quality gates เดิมยังเป็นข้อเสนอ ไม่ได้กลายเป็น SLA/สิทธิ์ deploy จากแผนนี้ coverage/provenance ที่ไม่พอต้องระบุ INCONCLUSIVE แม้ numeric metrics ผ่าน

## 8. สิ่งที่ต้องได้ก่อนเสนอ training

1. Authorized scenario register และ collection approvals
2. Provenance ledger ที่อ้างหลักฐานภายใน VM ไม่ฝัง raw logs/secret ใน Git
3. Immutable membership references/hashes และ exclusion report ของ protected/duplicate/conflict records
4. Coverage/missingness report และ split manifest ที่ freeze และได้รับอนุมัติ
5. Evaluation/baseline/threshold-selection plan และรายการข้อจำกัดที่ยังไม่ปิด

วาง raw data, identities, source paths และ row-level evidence ไว้พื้นที่ส่วนตัวบน VM ตามสิทธิ์/retention ที่ตกลง ไม่ส่งออกภายนอกและไม่ใส่ dataset/weights ลง repo การ hash ข้อมูลไม่ใช่สิทธิ์ส่งออก

## 9. Operational guardrails

- GPU ใช้ร่วมกับ LuckyFive ต้องตรวจ reservation/guard ใหม่ ห้ามหยุด process ของเพื่อน
- ห้ามแตะ shared stack/driver/network, build ทับ runtime .next หรือ restart/change shared systemd state
- ไม่ reset หรือ consume lag/offset เพื่อเก็บข้อมูลเพิ่ม ค่า offset/lag ใน handoff ไม่ใช่คำสั่ง resume
- BlueField/rshim และ automated response ต้อง OFF; ไม่มี containment/playbook ในแผนนี้
- หากจะเก็บ lab จริง ให้ใช้ขอบเขตที่เจ้าของอนุมัติและมี rollback ไม่ทำบน endpoint ทีมอื่นโดยอนุมานสิทธิ์

**งานที่อนุญาตในรอบนี้มีเพียงจัดทำเอกสารแผน ไม่ใช่การเริ่ม acquisition หรือ training**
