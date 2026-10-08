> Current status: see [LATEST_STATUS.md](LATEST_STATUS.md). Raw integration passed on H100; model quality gates have not passed.

> งานเพิ่มเติม: อ่าน NEXT_STEPS_TH.md — เพิ่ม raw bridge และ quality report; H100 raw run ยัง PENDING ผล PASS ด้านล่างเป็นรอบข้อความเดิมเท่านั้น

# ส่งต่องาน EDRXDR-Morpheus

อัปเดต 9 ตุลาคม 2026 เวลาไทย (Asia/Bangkok) จากผลที่ผู้ใช้รันบน H100 จริง การทดสอบล่าสุดประมาณ 02:48 น. หลังผู้ใช้กลับมาทำ offline integration ให้เสร็จก่อนส่งต่อ ผลล่าสุด PASS

## สถานะสำคัญ

- ฝึก v1/v2/v2b สำเร็จ แต่ **คุณภาพโมเดลยังไม่พร้อม production**
- **Offline Morpheus integration PASS**: token IDs/masks/row mapping/scores ตรงกับ Hugging Face ครบ 1,361 inputs
- งานต่อคือ raw-event-to-text offline integration และพัฒนาคุณภาพข้อมูล/โมเดล ไม่ต้องแก้ tokenizer ซ้ำโดยไม่มี evidence ใหม่
- รุ่นที่เลือกทดสอบ: `wazuh-severity-context-v2-balanced-20261008T190719Z-1398863`
- โมเดลเป็น **weakly supervised Wazuh severity baseline** ไม่ใช่ independent threat detector และ score ไม่ใช่ calibrated threat probability
- ห้ามใช้คะแนนสั่ง automated response หรือเปิด production inference ณ สถานะนี้

## เครื่องและข้อจำกัด

```text
SSH:        <SSH_USER>@<H100_HOST>
Host:       <H100_HOSTNAME>
Repository: ~/EDRXDR-Morpheus
GPU:        GPU 0 — H100 80GB HBM3
Image:      edrxdr-morpheus-train:25.06
Python:     /opt/conda/envs/morpheus/bin/python
PyTorch:    2.4.0+cu124
Transformers: 4.44.2
Wazuh image: 4.14.7
```

Host driver ที่รายงานคือ 580.178.04 และ nvidia-smi แสดง CUDA 13.0 ตัวเลขนี้ไม่ใช่ PyTorch CUDA build ไม่ต้องแก้ให้เลขตรงกัน

- ใช้ VM ร่วมกับทีมอื่น รอบนี้จอง 9 ต.ค. 01:00–05:00 การจองนี้ไม่ใช่สิทธิ์ถาวร ต้องมีสิทธิ์ใช้ GPU ก่อนรันรอบต่อไป
- ไม่แตะ host drivers/CUDA, BlueField/DOCA, production Kafka หรือ shared infrastructure
- ไม่ restart/ปรับ config Wazuh เพื่อแก้โมเดล
- Docker ยังใช้ GPU/CPU/RAM/disk ร่วมกับทีมอื่น ห้ามหยุด processes ของทีมอื่น
- เก็บข้อมูล/โมเดลขนาดใหญ่ใน Docker volumes ไม่เติม `/home`
- Runners ใช้ image/cache เดิมแบบ offline ไม่ติดตั้ง dependencies ใหม่
- ห้าม prune/delete volumes หรือส่ง log/secrets/weights ขึ้น public Git

บริบทเดิมรายงาน ingestion Wazuh → Kafka → Normalizer → morpheus-input เคยผ่าน แต่ไม่ได้ทดสอบเส้นทางนี้ซ้ำในรอบปัจจุบัน BlueField/DOCA ยังติด dependency ฝั่ง infrastructure

## ตำแหน่ง artifacts

| Volume | เนื้อหา |
|---|---|
| `edrxdr-hf-cache` | bert-base-uncased cache |
| `edrxdr-model-output` | checkpoints และ reports |
| `edrxdr-dataset` | snapshot alerts และ dataset v2 |

ชื่อโฟลเดอร์ต่อไปนี้อยู่ภายใน volume ไม่ใช่ host path ใน `/home` เวลาในชื่อเป็น UTC เช่น 20261008T190719Z = 9 ต.ค. 02:07:19 เวลาไทย

ใน `edrxdr-model-output`:

```text
wazuh-severity-nlp-v1-smoke-20261007T135726Z-1881188
wazuh-severity-nlp-v1-train-20261008T182138Z-1189522
wazuh-severity-context-v2-smoke-20261008T190209Z-1373668
wazuh-severity-context-v2-train-20261008T190301Z-1377612
wazuh-severity-context-v2-balanced-20261008T190719Z-1398863
morpheus-offline-check-20261008T192400Z-1478287/parity_report.json
```

Checkpoint v2 มี model.safetensors, tokenizer files, training_report.json, dataset_manifest.json และ RUN_COMPLETE ส่วน v1 มี test_report.json ที่สร้างแยกหลังฝึก มีโฟลเดอร์ offline checks ที่ล้มก่อนหน้า บางอันไม่มีรายงาน การมีโฟลเดอร์ไม่ได้หมายถึง PASS

ใน `edrxdr-dataset`:

```text
wazuh-history-20261008T184838Z-1179365/
wazuh-context-v2-20261008T185539Z-1179365/
```

## ข้อมูลและ label

### v1

ไฟล์เดิมอยู่ที่ `morpheus/data/`: wazuh-nlp-dataset.jsonl รวม 7,395 events; train/validation/test = 4,936/1,143/1,316; จำนวน rules = 25/4/4 และ rule_id ไม่ข้าม split

Fields ใน split: event_id, rule_id, text_input, text_source, weak_label

Label เป็น string: low_severity → 0, high_severity → 1 สคริปต์แก้ให้รองรับแล้ว ตรวจจับคู่ train/validation กับต้นทาง event_id/rule_id/text ได้ครบ ไม่มี level ขัดแย้ง Label ที่พบสอดคล้องกับ high เมื่อ level ≥ 7 แต่ไม่มี generator เดิมหรือ level 6 เพื่อพิสูจน์เกณฑ์เดิมทุกกรณี

ข้อมูลเป็น Wazuh events: package changes, SSH/sudo, CVE, SCA/CIS, file/system events ไม่ใช่ packet capture หรือ attack ground truth มีทั้งกิจกรรมปกติและเหตุการณ์ด้านความปลอดภัย

Train/validation มาจาก host หลัก 6,077 events และอีก host 2 events; 4 rules ใหญ่รวม 4,657/4,936 train rows (~94%) Text ไม่ซ้ำตรง ๆ ไม่ได้แปลว่า template หลากหลาย เพราะ timestamp/CVE/package names อาจเปลี่ยนใน template เดิม

### v2 candidate

Snapshot เฉพาะ `.json.gz` ที่ปิดรอบแล้วจาก `/var/ossec/logs/alerts/2026` ใน `wazuh-wazuh.manager-1`: 20 files, 2.0 MB compressed, gzip integrity ผ่าน ไม่มีการแก้ไฟล์ต้นทาง

Audit: 8,423 events, 40 rules, 0 duplicate keys, 0 conflicting keys, 0 invalid rows; host counts 8,233/190; วันที่ 16 ก.ย.–7 ต.ค. 2026; มี full_log 2,925, rule_description 8,417, data 8,225 events

Text รูปแบบเดียวกัน:

```text
Description: <rule.description หรือ [missing]>
Log: <full_log หรือ [missing]>
```

ไม่ใส่ rule_id/rule_level เป็น model input แต่ rule description เป็นบริบทจากระบบ Wazuh ซึ่งเป็นผู้ให้ weak label อยู่แล้ว จึงไม่ใช่ independent detection

v2 กำหนด label ชัดเจน: level ≥ 7 เป็น high; ต่ำกว่า 7 เป็น low คง rule memberships เดิม:

| กลุ่ม | Events | Low / High | การใช้ |
|---|---:|---:|---|
| Train | 5,232 | 2,846 / 2,386 | ฝึก |
| Validation | 1,314 | 786 / 528 | development evaluation |
| Old-test rules | 1,398 | 825 / 573 | quarantine |
| 7 new rules | 479 | 367 / 112 | สำรอง ยังไม่ประเมินโมเดล |

7 new rules: 19007, 19008, 19009, 19010, 501, 506, 531 มี high เพียงสอง rules และหนึ่งในนั้นมีตัวอย่างเดียว จึงไม่ใช่หลักฐานเพียงพอสำหรับ production แบบกว้าง

Dataset v2 มี manifest.json, wazuh-nlp-train.jsonl, wazuh-nlp-validation.jsonl, quarantine_old_test-index.jsonl, reserve_new_rules-index.jsonl สองไฟล์ index หลังมีเพียงตัวชี้กลับ snapshot ไม่ใช่ training text

ไม่พบ conflicting identical text หรือ exact text overlap train/validation แต่ไม่ได้พิสูจน์ว่าไม่มี template/time/host correlations

Token audit: train p50=46/p95=66/max=729, validation p50=56/p95=73/max=80 เลือก length=256; train ถูกตัด 19 rows (533:17, 5402:1, 5403:1); validation ไม่ถูกตัด โดย rule 533 ถูกตัดทุกตัวอย่าง

manifest.ready_for_training ยังคง false การฝึกใช้ --experimental-data และบันทึก override อย่างเปิดเผย ไม่ได้ยกระดับเป็น production-ready

## ผลทดลองที่ยืนยันจาก H100

bert-base-uncased, single logit, BCEWithLogitsLoss, AdamW lr=2e-5, batch=8, length=256, seed=42, BF16, threshold=0.5 ทุก run เริ่มจาก base model ใหม่ ไม่ resume smoke

| Run | Evaluation | TP | FP | TN | FN | Precision | Recall | F1 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| v1 617 steps | val 1,143 | 520 | 243 | 380 | 0 | 68.15% | 100% | 81.06% |
| v1 | test 1,316 | 408 | 810 | 0 | 98 | 33.50% | 80.63% | 47.33% |
| v2 654 steps | val 1,314 | 528 | 521 | 265 | 0 | 50.33% | 100% | 66.96% |
| v2b 654 steps | val 1,314 | 528 | 258 | 528 | 0 | 67.18% | 100% | 80.37% |

v1/v2 validation มีขนาดและข้อความต่างกัน ไม่ใช่ controlled comparison ส่วน v2/v2b ชุดเดียวกันแต่ยังเป็น seed เดียว

v2b ใช้ train-only inverse-sqrt rule-count loss weights, จำกัดอัตราส่วน weights ภายใน label ไม่เกิน 5:1 แล้ว normalize ให้ average weight แต่ละ class = 1 Validation loss ไม่ถ่วงน้ำหนัก

v2b ราย rule: 5501 TN=278; 5502 TN=250; 2901 FP=258; 23504 TP=528 Positive validation ทั้งหมดมาจาก rule เดียว และ 2901 ยังผิดทั้งหมด

v1 test: 2903 TP=237; 23506 TP=171; 23508 FP=810; 550 FN=98 ผลถูกเปิดแล้ว ห้ามจูนจาก test นี้แล้วเรียกว่า fresh holdout

## Offline integration: PASS ล่าสุด

ผล 9 ต.ค. 2026 เวลา 02:48 น.: rows=compared_rows=1361, issues={}, max_absolute_score_error=0.0; threshold=0.5, BF16, tolerance atol=rtol=0.0001 ไม่มีการผ่อน tolerance หรือข้ามกรณีทดสอบ

รายงานใน edrxdr-model-output: `morpheus-offline-check-20261008T194814Z-1588236/parity_report.json`

Runtime ที่ยืนยัน: torch 2.4.0+cu124, transformers 4.44.2, cupy 13.3.0, cudf 25.02.02

Hashes จากผลรัน:

```text
dataset manifest: 354e3c9dc9febe49173fa416cdd943cf3512540dded5f18e0ae3d800908b8669
model weights: 8547792bdff3897388b07891bc2c57e0f76e81e2bb09e2b8ce55be48bfc31363
inference adapter: 93f65aeba619f92c60dcd0af7aa484b2f49a0ef75688f8ceb863a3a7153d0e68
special-token adapter: 42061f6932fecafc19cd7510a0f79d15de13f5a9c958f5b3ff5e58e0dcc4497a
```

```text
Prebuilt v2 text → InMemorySource → Deserialize → native PreprocessNLPStage
→ project-local BertSpecialTokensStage → strict HF token/mask check
→ project-local ContextSeverityInferenceStage
→ InMemorySink → HF score/row comparison
```

1,361 inputs: validation 1,314 + train coverage/long texts 42 + synthetic tokenizer checks 5 ไม่ใช้ test/reserve เริ่มที่ text ที่สร้างแล้ว ไม่ได้ทดสอบ raw-event-to-text ingestion ทั้งเส้นทาง

Config ล่าสุด: uncased hash, do_lower_case=True, native add_special_tokens=False, truncation=True, feature_length=256, column=text_input, pipeline batch=16, model batch=8, threads=1 เพิ่ม CLS=101/SEP=102 ใน project-local stage โดยเก็บ body สูงสุด 254 tokens แล้ว pad=0 ให้ครบ 256 รองรับ empty body ด้วย CLS/SEP และตรวจ mask เป็น binary/right-padded ก่อนแปลง

Adapter โหลด HF safetensors, eval mode, output [N,1], sigmoid ครั้งเดียว ตรวจ IDs/mask/output โดยไม่ monkeypatch package

เหตุที่ใช้ adapter: built-in inf-pytorch ใช้ torch.load; calc_output_dims มี random IDs <65000 (เกิน vocab 30522) และอ่าน _outputs ที่ไม่ได้เติมใน worker ที่ตรวจ จึงไม่ใช้ probe นั้นกับโมเดลนี้

### ประวัติ error ก่อนแก้ (ไม่ใช่สถานะปัจจุบัน)

```text
Token parity failed before inference
input_rows_seen: 1 / 1361
audit_id: 0 (validation)
actual/expected shape: [1,256] ทั้งคู่
input_ids differing positions: 74
attention_mask differing positions: 2
actual active mask tokens: 72
HF expected active mask tokens: 74
```

Report: `edrxdr-model-output/morpheus-offline-check-20261008T192400Z-1478287/parity_report.json`

Single-row diagnostic ต่อมายืนยันว่า native tokens เท่ากับ HF tokens เมื่อตัด CLS/SEP ออก (`native_equals_hf_without_CLS_SEP=true`) ในแถวนั้น แม้เดิมส่ง add_special_tokens=True จึงเปลี่ยน native เป็น False อย่างชัดเจนและเพิ่ม framing เอง หลังแก้ผ่าน parity ครบชุด ไม่ได้อ้างว่าได้แก้ implementation ภายใน C++ library แล้ว

Vocab compatibility เดิมผ่าน 30,522 entries, mismatch 0 เป็นเพียง vocab equality ไม่ใช่ preprocessing parity

### Errors ก่อนหน้า

- DataFrame repr ใน source constructor → to_pandas → Numba CUDA context IndexError: ใช้ SourceFrames(list) safe repr และ Arrow transfer แล้ว ผ่านจุดนี้แล้ว
- รอบถัดมาขึ้น Invalid model output ซึ่งเดิมรวม shape/nonfinite ไว้ด้วยกัน ยังไม่ทราบสาเหตุเฉพาะของรอบนั้น
- เพิ่ม diagnostic shape/NaN/Inf/mask และ fail-fast token parity; หลังเพิ่ม special-token stage ผ่าน checks ทั้งหมด
- Warning memory policy/sys_nice ปรากฏร่วมด้วย แต่ไม่ได้พิสูจน์ว่าเป็นสาเหตุ ไม่ต้องเพิ่ม container capability เพื่อกลบ warning

## รับช่วงต่อ ตามลำดับ

1. อ่านรายงาน PASS ล่าสุดและตรวจ artifact hashes ก่อนเปลี่ยน code/checkpoint
2. ทำ raw-event-to-text offline integration ให้ใช้รูปแบบเดียวกับ build_context_dataset.py ปัจจุบัน parity test เริ่มจาก prebuilt text เท่านั้น
3. จัด model contract: required fields, missing-field behavior, tokenizer/framing/truncation, one logit/sigmoid, output schema และ version hashes
4. หากเปลี่ยน runtime/model/preprocessing ให้รัน parity อีกครั้งด้วยเกณฑ์เดิม ไม่ปิด assertions หรือใช้ nan_to_num เพื่อให้ผ่าน
5. ด้านคุณภาพ ต้องเพิ่มข้อมูล/บริบทสำหรับ package low/high และออกแบบ evaluation ก่อนฝึกใหม่ ยังมี rule 2901 ผิดทั้งหมด แม้ integration PASS
6. คง old-test quarantine และ reserved rules; ไม่ย้ายเข้า train เพื่อเพิ่มคะแนน
7. Kafka production, shadow deployment และ response ยังไม่เปิด ต้องมีเกณฑ์คุณภาพและแผนร่วมกับเจ้าของระบบก่อน

## คำสั่งอ้างอิง

อ่านรายงานล่าสุด ไม่ใช้ GPU:

```bash
docker run --rm --pull never --network none \
  --mount type=volume,src=edrxdr-model-output,dst=/models,readonly \
  --entrypoint /bin/cat edrxdr-morpheus-train:25.06 \
  /models/morpheus-offline-check-20261008T194814Z-1588236/parity_report.json
```

Reproduce เมื่อมีสิทธิ์ใช้ GPU:

```bash
cd ~/EDRXDR-Morpheus
bash -n training/run_morpheus_offline.sh
bash training/run_morpheus_offline.sh
```

Runner ระบุ checkpoint/dataset ที่แน่นอน ไม่เลือก latest อัตโนมัติ แต่ละรอบเขียน unique output directory

ก่อนส่งคืนเครื่อง: `nvidia-smi` รอบ PASS ล่าสุดจบกลับ shell และ runner ใช้ --rm แต่ยังไม่มีผล nvidia-smi หลังรอบ PASS อย่าหยุด process ของทีมอื่น ถ้างานของตนจบแล้วสามารถ `exit` ออกจาก SSH

## ขอบเขตการตรวจและการส่งต่อ

- Windows ตรวจ syntax, dataset safeguards, loss-weight formula และ safe-repr behavior แล้ว
- ผล training/evaluation ในตารางมาจากผู้ใช้รัน H100 จริง ไม่ใช่การทดสอบบน Windows
- Morpheus runtime parity PASS สำหรับ 1,361 inputs ที่ระบุเท่านั้น; ไม่มีการ deploy/เชื่อม Kafka และยังไม่ยืนยัน production readiness
- ชุดส่งต่อมี scripts/docs เท่านั้น ไม่รวม raw logs, model weights, images หรือ credentials
- Local ChatGPT project mirror ไม่ใช่ Git checkout ยังไม่ได้ commit/push ไป GitHub ใด ๆ ให้ผู้รับงานเพิ่ม training/ เข้า repo จริงผ่าน workflow ของทีม
- sources/ ใน local mirror เป็น read-only reference ไม่ได้แก้ไข
