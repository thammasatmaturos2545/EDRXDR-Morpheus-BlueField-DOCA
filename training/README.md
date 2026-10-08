> Current status: see [LATEST_STATUS.md](LATEST_STATUS.md). Raw integration passed on H100; model quality gates have not passed.

**งานต่อ:** [NEXT_STEPS_TH.md](NEXT_STEPS_TH.md) — raw-event integration พร้อมทดสอบบน H100; ยังไม่มีผล GPU ใหม่

# EDRXDR-Morpheus — training and offline inference

**เริ่มอ่าน [HANDOFF.md](HANDOFF.md) สำหรับสถานะล่าสุดและวิธีรับช่วงต่อ (9 ตุลาคม 2026 เวลาไทย)**

v1/v2/v2b ฝึกสำเร็จ และ Morpheus offline integration **PASS ครบ 1,361 inputs** เมื่อ 9 ต.ค. 2026 เวลา 02:48 น. คะแนนต่างจาก Hugging Face สูงสุด 0.0 แต่คุณภาพโมเดลยังไม่พร้อม production อ่านผลและข้อจำกัดใน HANDOFF

| Files | Purpose |
|---|---|
| `build_context_dataset.py` | Dataset v2, manifests, held-out rule separation |
| `train_context_v2.py`, `run_context_v2.sh` | v2 and v2b rule-weighted loss experiments |
| `morpheus_context_inference.py` | Project-local HF safetensors adapter for Morpheus |
| `morpheus_bert_special_tokens.py` | Add verified CLS/SEP framing, truncate body to 254, pad to 256 |
| `check_morpheus_offline.py`, `run_morpheus_offline.sh` | Strict token/mask/score/row comparison; PASS on the documented 1,361 inputs |
| `train_wazuh_severity.py`, `run_training.sh` | Original v1 experiment |

ไม่มี raw logs, credentials, model weights หรือ Docker images ในชุดเอกสารและสคริปต์นี้ อ่านตำแหน่ง volumes และรายงานใน HANDOFF ก่อนรัน ห้ามถือว่าการฝึกสำเร็จหมายถึงพร้อม deploy

## Original v1 reference

Weakly supervised binary Wazuh severity baseline. Labels come from the existing
Wazuh severity mapping: this is not an independent threat detector and the score
is not a calibrated threat probability. Do not change the label mapping silently.

Copy this small `training/` directory to `~/EDRXDR-Morpheus/` on the reserved H100
host. No model or dataset copies belong in `/home`. The runner uses existing Docker
volumes, read-only dataset mounts, offline Hugging Face loading, and GPU 0 only.
Confirm GPU 0 is allocated to your reservation before running. No packages,
drivers, CUDA, DOCA, Kafka connections, or infrastructure changes are required.

Required JSONL fields default to `text` (nonempty string), `label` (numeric 0/1),
and `rule_id` (group). If prepared fields differ, set `TEXT_KEY`, `LABEL_KEY`, and
`GROUP_KEY` to their actual names. Nested fields are not supported. Inspect only
the field names rather than printing event contents:

```bash
docker run --rm --pull never --network none \
  --mount type=bind,src="$PWD/morpheus/data",dst=/data,readonly \
  --entrypoint /opt/conda/envs/morpheus/bin/python \
  edrxdr-morpheus-train:25.06 -c \
  'import json; print(sorted(json.loads(open("/data/wazuh-nlp-train.jsonl").readline()).keys()))'
TEXT_KEY=text_input LABEL_KEY=weak_label GROUP_KEY=rule_id \
bash training/run_training.sh smoke
```

Smoke mode performs 10 optimizer steps and evaluates the first 64 validation
rows solely to check execution. These metrics are not model quality estimates.
Expect an initial warning that BERT's classifier head is newly initialized.
Full mode: `TEXT_KEY=text_input LABEL_KEY=weak_label GROUP_KEY=rule_id bash training/run_training.sh train` (one epoch, complete validation).
Run only when sufficient reservation time remains; no duration is guaranteed.
Stop the foreground container with Ctrl+C if needed. Incomplete runs are not
usable checkpoints. Every run writes a unique output folder.

Architecture: bert-base-uncased, one logit, explicit BCEWithLogitsLoss, AdamW,
batch size 8, fixed length 256, learning rate 2e-5, seed 42, BF16 when supported.
Both classes are required; split counts and group disjointness are checked before
training. The original grouped splits are preserved. The test split is validated
but never scored in this development script. Saved files include Hugging Face
model/tokenizer and a report with split hashes, parameters, and validation metrics.

Check `training_report.json` for `smoke: false` before using a trained artifact.
The report includes the GPU name and training steps. Smoke checkpoints must not
be deployed. Output stays in `edrxdr-model-output`; cache stays in `edrxdr-hf-cache`.
The volume's actual host location follows Docker's configured data root.

Vocabulary compatibility was previously checked (30522 entries, 0 mismatches).
This does not establish full Morpheus preprocessing parity: casing, special tokens,
padding, truncation/windowing, and tensor inputs still need integration checks.
The saved checkpoint is not yet a Morpheus/Triton export. Apply sigmoid exactly
once during future inference and validate tensor/preprocessing parity before use.
