> Current status: see [LATEST_STATUS.md](LATEST_STATUS.md). Raw integration passed on H100; model quality gates have not passed.

# งานต่อ 9 ต.ค. 2569 — RAW integration implementation, H100 pending

อ่าน HANDOFF.md สำหรับผล H100 เดิม แล้วอ่านเอกสารนี้สำหรับงานเพิ่ม
สถานะ: เพิ่มโค้ดและทดสอบ CPU แล้ว ยังไม่ได้รัน raw integration บน H100, ไม่ได้ฝึกใหม่ และยังไม่มีผลคุณภาพใหม่

## 1. รันรอบ raw offline

จาก repo จริง `~/EDRXDR-Morpheus` ให้นำ training/ ชุดนี้เข้า workflow ของทีม
ตรวจรายงาน PASS เดิมตาม HANDOFF ก่อน จากนั้นเมื่อยังมีสิทธิ์ใช้ GPU 0:

```bash
python -B -m unittest discover -s training -p 'test_*.py'
bash -n training/run_raw_offline.sh
bash training/run_raw_offline.sh
```

Runner ใช้ image, checkpoint, snapshot และ dataset เดิมแบบระบุชื่อแน่นอน ใช้ network none และ GPU 0
ไม่ได้เชื่อม Kafka หรือเปลี่ยน host configuration

สคริปต์ตรวจ hash ของ dataset และ raw archives แล้วใช้ source_file/source_line เฉพาะ train/validation
ตรวจ event_id, rule_id, weak label และข้อความตรงกับข้อความตอนฝึกทุกแถว ก่อนส่งข้อความที่สร้างจาก raw เข้า pipeline
อ่าน archive แบบ stream แต่ไม่ parse/transform/score แถว quarantine/reserve
คาดว่าจะตรวจข้อความ 6,546 events (train 5,232 + validation 1,314)
เส้นทาง GPU ใช้ 1,361 inputs เดิม + 6 missing-field cases = 1,367 inputs เมื่อข้อมูลตรงชุดเดิม
ไม่ใช่การวัดคุณภาพบนทุก train event และไม่ใช่ live ingestion

ผลใน unique directory ของ edrxdr-model-output:
- parity_report.json: ต้อง PASS, issues ว่าง, compared_rows เท่ากับ rows, raw_event_check.status PASS
- quality_report.json: precision/recall/F1/FP/FPR และ confusion counts ราย rule ที่ threshold 0.5
- score_comparison.jsonl: audit_id/source/HF score/Morpheus score/error ไม่บันทึกข้อความดิบ

Tolerance คง atol=rtol=0.0001; token/mask/row mapping ต้องตรงทุกแถว ไม่ใช้ nan_to_num
รอบข้อความเดิมยังรันด้วย run_morpheus_offline.sh ได้ ไม่มี --raw-snapshot
ไม่ต้องฝึกเพื่อแก้ tokenizer และไม่แก้ adapters CLS/SEP หรือ inference

## 2. Input / output contract: wazuh-context-v2-raw-1

Input: JSON object ของ Wazuh; model feature มีแค่ rule.description และ full_log
rule หาย/null ให้ถือเป็น object ว่าง; rule ที่เป็นชนิดอื่น reject
ยึด build_context_dataset.context_text เดิม: ค่า falsy ถูกแปลงเป็นข้อความว่างก่อนตรวจชนิด
ดังนั้น null/false/0/empty container ตามพฤติกรรมเดิมถือว่าหาย; truthy non-string reject
strip whitespace ขอบข้อความ แล้วสร้างตรงตัว:

```text
Description: <description หรือ [missing]>
Log: <full_log หรือ [missing]>
```

หายทั้งสอง field หรือเหลือแต่ whitespace: reject, ไม่ให้คะแนน
การแก้ให้ strict types มากกว่านี้ต้องเปลี่ยน contract version และทดสอบใหม่
ห้ามเติม package fields เข้า v2b เดิมเงียบ ๆ
raw verification ต้องมี manager.name, agent.id, id, rule.id และ integer rule.level 0..15
level >=7 ใช้สร้าง weak label เพื่อประเมินเท่านั้น; ไม่ส่ง level/id เข้า tokenizer

Tokenizer: uncased BERT, native body + adapter CLS=101/SEP=102/PAD=0,
body <=254, รวม length 256, right padding, binary mask
Inference: HF safetensors, eval, single logit [N,1], sigmoid ครั้งเดียวใน adapter
score >=0.5 เป็น high_severity; score ไม่ใช่ calibrated attack probability

ผลคะแนนในโหมดตรวจเป็น score_comparison.jsonl โดย audit_id จับคู่กับ samples ตามลำดับที่ checker สร้าง
Metadata ของ run อยู่ parity_report.json: checkpoint, weights hash, manifest hash,
text builder hash, raw adapter hash, preprocessing adapter hash, inference adapter hash และ runtime versions
ใช้ tuple ของ hashes เหล่านี้เป็น run/model contract identity; ชื่อ checkpoint อย่างเดียวไม่เพียงพอ

Schema ที่เสนอสำหรับ shadow ในอนาคต (ยังไม่ได้สร้าง sink):
{schema_version, event_id, model_weights_sha256, preprocessing_sha256,
 text_contract_version, high_severity_score, predicted_label, threshold,
 scored_at_utc, mode:"shadow"}
Rejected event แยกเป็น {event_id, status:"rejected", reason_code}; ห้ามใส่ score=0 แทนข้อผิดพลาด
ห้ามส่ง raw text/secrets ไป dashboard โดยปริยาย

## 3. ปรับคุณภาพข้อมูลก่อนฝึก v3

v2b rule 2901 เป็น FP ทั้ง 258 แถว และ positive validation อยู่ rule เดียว
ใช้ผลนี้เป็น development diagnosis; validation ไม่ใช่ fresh holdout อีกต่อไป
ห้ามย้าย rule 2901 หรือ rules ใน validation/test/reserve เข้า train

ขั้นตอนที่ต้องทำบนข้อมูลจริง:
1. เก็บ snapshot รอบใหม่แบบ read-only จาก closed archives ตามสิทธิ์ของทีม
2. ทำ aggregate inventory ตาม rule/label/host/time/package action, missing fields และ duplicate/template frequency
   ตรวจเฉพาะตัวอย่างใหม่ที่จำเป็นในระบบที่ได้รับอนุญาต ไม่ dump แถวเดิมซ้ำ
3. หา training rules ใหม่ที่เป็น package install/update/remove/inventory และ vulnerability events
   เพิ่มทั้ง low/high ตาม rule.level; ห้ามสมมติว่าการติดตั้งแพ็กเกจคือ high หรือโจมตี
4. ตรวจ field paths จริงก่อนเลือก feature: package name/version, action, CVE/severity, process/user,
   และ context ก่อนหน้า เฉพาะที่มีจริงและมี ณ เวลา inference ไม่ใช้ข้อมูลอนาคตหรือ label/rule.level
5. ถ้าต้องเพิ่ม input context ออก contract v3 + builder รุ่นใหม่ และสร้าง train/validation ใหม่แบบ reproducible
   ใช้ host/time/template grouping, คงสมาชิก rules เดิมและ quarantine; deduplicate ก่อนแบ่ง
6. จัด package subgroups ที่มีทั้ง labels ใน development data; เก็บ missingness/truncation ราย rule
   สำหรับ rule 533 ที่ถูกตัดทุกแถว ต้องออกแบบบริบทก่อนฝึก ไม่แอบเพิ่ม max_length ใน v2
7. ทดลอง v2 text เทียบ v3 context บนชุดประเมินเดียวกัน พร้อม baseline ง่ายและอย่างน้อย 3 seeds
   เลือก threshold ด้วย validation เท่านั้น; report mean/range และ FP ต่อ 1,000 low events

ยังไม่มี raw snapshot/weights ใน ZIP จึงยังทำ inventory จริง เพิ่มตัวอย่างจริง หรือยืนยันคุณภาพที่ดีขึ้นไม่ได้

## 4. เกณฑ์ผ่านที่เสนอให้ทีมตกลงก่อนรอบถัดไป

Numeric development gates ที่เพิ่มใน quality_metrics.py (threshold 0.5):
- precision >=85%, recall >=90%, F1 >=85%, FPR <=10%
- rules ที่ n>=30: FPR <=20% เมื่อมี low และ recall >=80% เมื่อมี high
- denominator เป็น 0 รายงาน null ไม่แทนด้วยคะแนนดี
- rule 2901 ต้องรายงานแยกและผ่าน FPR gate

เกณฑ์เหล่านี้เป็นข้อเสนอ ยังไม่ใช่ข้อตกลง SLA หรือสิทธิ์เปิด shadow
Numeric pass อย่างเดียวไม่พอ: ต้องมีหลาย positive rules, host/time coverage,
confidence intervals แบบ group bootstrap และตัวอย่างเพียงพอตามแต่ละ subgroup
report absolute FP, low count, false alerts ต่อช่วงเวลา และ analyst review burden
ถ้า coverage ไม่พอให้ INCONCLUSIVE แม้ตัวเลขผ่าน

## 5. แผน 479 reserve events ก่อนเปิดผล

479 events / 7 rules เป็น reserve สำหรับ one-time exploratory generalization audit
ไม่ใช้ในการฝึก เลือก features/threshold/checkpoint หรือ early stopping
ก่อนรัน: ลงทะเบียน hashes ของ snapshot/index/model/builder/tokenizer,
freeze threshold+metrics+gates+package subgroup definitions และบันทึกเวลา/ผู้อนุมัติ
ตรวจจำนวน/สมาชิกจาก index โดยไม่เรียกโมเดลหรือเปิด text เพิ่มเพื่อจูน
ประเมินครั้งเดียวหลัง development gates ผ่าน: micro/macro per-rule, TP/FP/TN/FN,
precision/recall/F1/FPR, group uncertainty และ missing/truncation โดยใช้ contract ที่ freeze
มี high เพียง 2 rules และหนึ่ง rule มี 1 event: ห้ามถือเป็น production acceptance
หากเปิดผลแล้วต้องบันทึกว่า reserve ถูกใช้แล้ว; รอบปรับโมเดลต่อไปต้องมี prospective holdout ใหม่
old test ยัง quarantine เสมอ; ผล v1 test ที่เปิดแล้วใช้เป็น historical evidence เท่านั้น

## 6. Shadow gate และแผนประสานเจ้าของระบบ

ยังไม่ต่อ Kafka/OpenSearch ในชุดนี้
เมื่อ quality+coverage+parity ผ่าน ให้เจ้าของระบบร่วมกำหนด read-only consumer group,
allowed topics, offset policy, rate/resource budget, score index + retention/ACL,
latency/throughput/drop/duplicate limits, review period และ rollback owner ก่อนเปิด
ทดสอบใน isolated replay ก่อน shadow จริง; output ต้องแยก index/label ว่า experimental shadow
Dashboard แสดง score, version, missing/rejected counts, lag และ analyst feedback
หยุด shadow เมื่อมี schema drift, nonfinite scores, lag/resource budget เกิน หรือข้อมูลรั่ว
ไม่มี automated response และไม่มีการเปลี่ยน Wazuh alert severity เดิม
