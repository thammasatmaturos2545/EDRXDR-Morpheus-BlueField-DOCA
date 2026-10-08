"""Experimental Wazuh-context severity baseline; not an independent threat detector."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import random


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_dataset(root):
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("experiment") != "wazuh-severity-context-v2-candidate":
        raise ValueError("Unexpected dataset experiment")
    if manifest.get("input_fields") != ["rule.description", "full_log"]:
        raise ValueError("Unexpected input fields")
    rows = {}
    texts = {}
    for split in ("train", "validation"):
        path = root / f"wazuh-nlp-{split}.jsonl"
        if file_hash(path) != manifest["output_sha256"][path.name]:
            raise ValueError(f"Hash mismatch: {split}")
        with path.open(encoding="utf-8") as stream:
            rows[split] = [json.loads(line) for line in stream]
        if not rows[split] or len(rows[split]) != manifest["counts"][split]:
            raise ValueError(f"Count mismatch: {split}")
        counts = Counter()
        labels_by_text = defaultdict(set)
        seen_ids = set()
        for row in rows[split]:
            text = row["text_input"]
            if not isinstance(text, str) or not text.strip():
                raise ValueError("Empty/non-string text")
            label = row["weak_label"]
            level = row["rule_level"]
            if type(level) is not int or not 0 <= level <= 15:
                raise ValueError("Invalid level metadata")
            if label != ("high_severity" if level >= 7 else "low_severity"):
                raise ValueError("Label/level disagreement")
            if row["event_id"] in seen_ids:
                raise ValueError("Duplicate event identity")
            seen_ids.add(row["event_id"])
            counts[str(row["rule_id"])] += 1
            labels_by_text[text].add(label)
        if dict(counts) != manifest["rules"][split]:
            raise ValueError("Rule count mismatch")
        if any(len(v) > 1 for v in labels_by_text.values()):
            raise ValueError("Conflicting labels for identical text")
        if {r["weak_label"] for r in rows[split]} != {"low_severity", "high_severity"}:
            raise ValueError("Both classes required")
        texts[split] = set(labels_by_text)
    if texts["train"] & texts["validation"]:
        raise ValueError("Exact text overlap across splits")
    if {r["event_id"] for r in rows["train"]} & {r["event_id"] for r in rows["validation"]}:
        raise ValueError("Event overlap across splits")
    # Reserved groups are checked from metadata only; no held-out text is loaded.
    rule_sets = [set(manifest["rules"][name]) for name in
                 ("train", "validation", "quarantine_old_test", "reserve_new_rules")]
    for i in range(len(rule_sets)):
        for j in range(i):
            if rule_sets[i] & rule_sets[j]:
                raise ValueError("Rules cross train/validation/quarantine/reserve boundaries")
    return manifest, rows


def summarize(counts):
    tp, fp, tn, fn = (counts[k] for k in ("tp", "fp", "tn", "fn"))
    return dict(**counts, n=tp+fp+tn+fn,
                precision=tp / max(tp+fp, 1), recall=tp / max(tp+fn, 1),
                specificity=tn / max(tn+fp, 1), f1=2*tp / max(2*tp+fp+fn, 1))


def balanced_rule_weights(rows):
    """Training-only inverse-sqrt rule weights, capped at 5:1 within each label.

    Normalize each label's average weight to one to preserve class mass.
    Rare rules get limited influence, rather than unbounded inverse-frequency weights.
    """
    counts = Counter(str(row["rule_id"]) for row in rows)
    rule_labels = {}
    for row in rows:
        rule, label = str(row["rule_id"]), row["weak_label"]
        if rule in rule_labels and rule_labels[rule] != label:
            raise ValueError("Rule weighting requires a consistent label within each rule")
        rule_labels[rule] = label
    weights = {}
    for label in set(rule_labels.values()):
        members = [rule for rule in counts if rule_labels[rule] == label]
        largest = max(counts[rule] for rule in members)
        raw = {rule: min(1 / math.sqrt(counts[rule]), 5 / math.sqrt(largest)) for rule in members}
        mass = sum(counts[rule] for rule in members)
        mean = sum(counts[rule] * raw[rule] for rule in members) / mass
        weights.update({rule: raw[rule] / mean for rule in members})
    return weights


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--experimental-data", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--rule-balanced-loss", action="store_true")
    args = parser.parse_args()
    if not args.experimental_data:
        parser.error("Use --experimental-data for this candidate; it is not production-ready")
    manifest, rows = check_dataset(args.data_dir)
    rule_weights = balanced_rule_weights(rows["train"]) if args.rule_balanced_loss else {
        str(row["rule_id"]): 1.0 for row in rows["train"]
    }
    if args.output_dir.exists():
        raise ValueError("Output already exists; choose a new run directory")
    import torch
    import transformers
    from torch.utils.data import DataLoader
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU required")
    random.seed(42)
    torch.manual_seed(42)
    torch.cuda.manual_seed_all(42)
    tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased", local_files_only=True)
    truncation = {}
    for split, data in rows.items():
        too_long = Counter()
        for start in range(0, len(data), 64):
            batch = data[start:start+64]
            ids = tokenizer([r["text_input"] for r in batch], truncation=False,
                            padding=False, verbose=False)["input_ids"]
            for row, tokens in zip(batch, ids):
                if len(tokens) > 256:
                    too_long[str(row["rule_id"])] += 1
        truncation[split] = dict(too_long)
    print(json.dumps({"truncated_rows_by_rule": truncation}), flush=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        "bert-base-uncased", num_labels=1, local_files_only=True
    ).cuda()
    model.config.problem_type = "multi_label_classification"
    model.config.id2label = {0: "high_severity"}
    model.config.label2id = {"high_severity": 0}
    use_bf16 = torch.cuda.is_bf16_supported()
    def collate(batch):
        inputs = tokenizer([r["text_input"] for r in batch], padding="max_length",
                           truncation=True, max_length=256, return_tensors="pt").to("cuda")
        labels = torch.tensor([r["weak_label"] == "high_severity" for r in batch],
                              dtype=torch.float32, device="cuda")
        return inputs, labels, [str(r["rule_id"]) for r in batch]
    train = DataLoader(rows["train"], batch_size=8, shuffle=True, collate_fn=collate)
    validation_rows = rows["validation"][:64] if args.smoke else rows["validation"]
    validation = DataLoader(validation_rows, batch_size=8, shuffle=False, collate_fn=collate)
    loss_fn = torch.nn.BCEWithLogitsLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-5)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    model.train()
    train_loss = train_count = steps = 0
    for inputs, labels, groups in train:
        optimizer.zero_grad(set_to_none=True)
        with torch.autocast("cuda", dtype=torch.bfloat16, enabled=use_bf16):
            logits = model(**inputs).logits.squeeze(-1).float()
            if args.rule_balanced_loss:
                sample_weights = torch.tensor([rule_weights[g] for g in groups], device="cuda")
                per_row_loss = torch.nn.functional.binary_cross_entropy_with_logits(logits, labels, reduction="none")
                loss = (per_row_loss * sample_weights).mean()
            else:
                loss = loss_fn(logits, labels)
        if not math.isfinite(loss.item()):
            raise RuntimeError("Nonfinite training loss")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0, error_if_nonfinite=True)
        optimizer.step()
        steps += 1
        train_loss += loss.item() * len(labels)
        train_count += len(labels)
        if steps % 10 == 0:
            print(json.dumps({"step": steps, "train_loss": loss.item()}), flush=True)
        if args.smoke and steps >= 10:
            break
    model.eval()
    counts = defaultdict(lambda: dict(tp=0, fp=0, tn=0, fn=0))
    validation_loss = 0
    with torch.no_grad():
        for inputs, labels, groups in validation:
            with torch.autocast("cuda", dtype=torch.bfloat16, enabled=use_bf16):
                logits = model(**inputs).logits.squeeze(-1).float()
                loss = loss_fn(logits, labels)
            if not math.isfinite(loss.item()):
                raise RuntimeError("Nonfinite validation loss")
            validation_loss += loss.item() * len(labels)
            for predicted, actual, group in zip((logits >= 0).tolist(), labels.bool().tolist(), groups):
                key = ("tp" if predicted else "fn") if actual else ("fp" if predicted else "tn")
                counts[group][key] += 1
    totals = {k: sum(v[k] for v in counts.values()) for k in ("tp", "fp", "tn", "fn")}
    metrics = dict(**summarize(totals), threshold=0.5,
                   loss=validation_loss/len(validation_rows), by_rule=dict(counts))
    print(json.dumps({"steps": steps, "validation": metrics}, indent=2), flush=True)
    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    report = dict(experiment="wazuh-severity-context-v2", scope=__doc__, status="experimental",
                  variant="v2b-rule-balanced-loss" if args.rule_balanced_loss else "v2-unweighted",
                  rule_balanced_loss=args.rule_balanced_loss, training_rule_weights=rule_weights,
                  base_model="bert-base-uncased", smoke=args.smoke, epochs_completed=0 if args.smoke else 1,
                  seed=42, batch_size=8, max_length=256, learning_rate=2e-5, steps=steps,
                  train_mean_loss=train_loss/train_count, validation=metrics,
                  truncated_rows_by_rule=truncation, bf16=use_bf16, device=torch.cuda.get_device_name(0),
                  versions={"torch": torch.__version__, "transformers": transformers.__version__},
                  dataset=str(args.data_dir), dataset_manifest_sha256=file_hash(args.data_dir/"manifest.json"),
                  trainer_sha256=file_hash(Path(__file__)), test_evaluated=False,
                  dataset_ready_flag_overridden_for_experiment=not manifest.get("ready_for_training", False),
                  score="sigmoid(single logit); Wazuh high-severity proxy, not threat probability",
                  limitations=["All 17 training examples of rule 533 are truncated at 256 tokens in the audited dataset",
                               "Validation is expanded development data, not a direct v1 comparison",
                               "Wazuh rule descriptions are teacher-provided context; this is not independent detection"])
    (args.output_dir/"training_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (args.output_dir/"dataset_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (args.output_dir/"RUN_COMPLETE").write_text("experimental training completed\n", encoding="utf-8")
    print("Saved:", args.output_dir, flush=True)


if __name__ == "__main__":
    main()
