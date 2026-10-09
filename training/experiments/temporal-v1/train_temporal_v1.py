"""Temporal development experiment for Wazuh severity proxy. Not production-ready."""

import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

DATA = Path("/data")
OUTPUT = Path("/output")

SEED = 42
BATCH_SIZE = 8
MAX_LENGTH = 256
LR = 2e-5
THRESHOLD = 0.5


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_jsonl(path):
    with path.open(encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


def balanced_rule_weights(rows):
    # Exact weighting logic from train_context_v2.py
    counts = Counter(str(row["rule_id"]) for row in rows)

    rule_labels = {}

    for row in rows:
        rule = str(row["rule_id"])
        label = row["weak_label"]

        if rule in rule_labels and rule_labels[rule] != label:
            raise ValueError(
                "Rule weighting requires consistent label within each rule"
            )

        rule_labels[rule] = label

    weights = {}

    for label in set(rule_labels.values()):
        members = [
            rule
            for rule in counts
            if rule_labels[rule] == label
        ]

        largest = max(
            counts[rule]
            for rule in members
        )

        raw = {
            rule: min(
                1 / math.sqrt(counts[rule]),
                5 / math.sqrt(largest),
            )
            for rule in members
        }

        mass = sum(
            counts[rule]
            for rule in members
        )

        mean = sum(
            counts[rule] * raw[rule]
            for rule in members
        ) / mass

        weights.update({
            rule: raw[rule] / mean
            for rule in members
        })

    return weights


def metric_counts(rows):
    tp = fp = tn = fn = 0

    for row in rows:
        actual = row["actual"]
        predicted = row["score"] >= THRESHOLD

        if actual and predicted:
            tp += 1
        elif actual and not predicted:
            fn += 1
        elif not actual and predicted:
            fp += 1
        else:
            tn += 1

    return {
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
    }


def safe_div(a, b):
    return None if b == 0 else a / b


def summarize(rows):
    counts = metric_counts(rows)

    tp = counts["tp"]
    fp = counts["fp"]
    tn = counts["tn"]
    fn = counts["fn"]

    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    specificity = safe_div(tn, tn + fp)

    f1 = (
        None
        if precision is None
        or recall is None
        or precision + recall == 0
        else 2 * precision * recall / (precision + recall)
    )

    fpr = safe_div(fp, fp + tn)

    return {
        **counts,
        "n": len(rows),
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "f1": f1,
        "fpr": fpr,
    }


def score_summary(rows):
    if not rows:
        return None

    import numpy as np

    scores = np.asarray(
        [x["score"] for x in rows],
        dtype=np.float64,
    )

    return {
        "min": float(scores.min()),
        "p05": float(np.percentile(scores, 5)),
        "median": float(np.median(scores)),
        "mean": float(scores.mean()),
        "p95": float(np.percentile(scores, 95)),
        "max": float(scores.max()),
    }


manifest = json.loads(
    (DATA / "manifest.json").read_text(
        encoding="utf-8"
    )
)

if manifest["experiment"] != "wazuh-severity-temporal-v1":
    raise RuntimeError("Unexpected temporal dataset")

expected = {
    "train.jsonl": 3922,
    "dev-all.jsonl": 1310,
    "dev-clean.jsonl": 1306,
    "dev-seen.jsonl": 1291,
    "dev-unseen.jsonl": 19,
}

splits = {}

for filename, count in expected.items():
    rows = load_jsonl(DATA / filename)

    if len(rows) != count:
        raise RuntimeError(
            f"{filename}: expected {count}, got {len(rows)}"
        )

    splits[filename] = rows


train_rows = splits["train.jsonl"]

# ---------------------------------------------------------
# Dataset validation
# ---------------------------------------------------------

train_ids = {
    x["event_id"]
    for x in train_rows
}

for name in [
    "dev-all.jsonl",
    "dev-clean.jsonl",
    "dev-seen.jsonl",
    "dev-unseen.jsonl",
]:
    overlap = train_ids & {
        x["event_id"]
        for x in splits[name]
    }

    if overlap:
        raise RuntimeError(
            f"Event overlap with {name}: {len(overlap)}"
        )


train_texts = {
    x["text_input"]
    for x in train_rows
}

clean_overlap = train_texts & {
    x["text_input"]
    for x in splits["dev-clean.jsonl"]
}

if clean_overlap:
    raise RuntimeError(
        f"dev-clean text overlap: {len(clean_overlap)}"
    )


rule_labels = defaultdict(set)

for row in train_rows:
    rule_labels[str(row["rule_id"])].add(
        row["weak_label"]
    )

if any(len(v) != 1 for v in rule_labels.values()):
    raise RuntimeError("Train rule-label conflict")


rule_weights = balanced_rule_weights(
    train_rows
)

# ---------------------------------------------------------
# Libraries / GPU
# ---------------------------------------------------------

import torch
import transformers

from torch.utils.data import DataLoader
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
)

if not torch.cuda.is_available():
    raise RuntimeError("CUDA GPU required")


random.seed(SEED)
torch.manual_seed(SEED)
torch.cuda.manual_seed_all(SEED)


print("=" * 72)
print("TEMPORAL V1 — RULE BALANCED")
print("=" * 72)

print("GPU            :", torch.cuda.get_device_name(0))
print("Train          :", len(train_rows))
print("Dev-All        :", len(splits["dev-all.jsonl"]))
print("Dev-Clean      :", len(splits["dev-clean.jsonl"]))
print("Dev-Seen       :", len(splits["dev-seen.jsonl"]))
print("Dev-Unseen     :", len(splits["dev-unseen.jsonl"]))
print("Seed           :", SEED)


tokenizer = AutoTokenizer.from_pretrained(
    "bert-base-uncased",
    local_files_only=True,
)


# ---------------------------------------------------------
# Truncation audit
# ---------------------------------------------------------

truncation = {}

for name, rows in splits.items():
    too_long = Counter()

    for start in range(0, len(rows), 64):
        batch = rows[start:start + 64]

        ids = tokenizer(
            [r["text_input"] for r in batch],
            truncation=False,
            padding=False,
            verbose=False,
        )["input_ids"]

        for row, tokens in zip(batch, ids):
            if len(tokens) > MAX_LENGTH:
                too_long[
                    str(row["rule_id"])
                ] += 1

    truncation[name] = dict(too_long)


print(
    json.dumps(
        {"truncated_rows_by_rule": truncation},
        indent=2,
    ),
    flush=True,
)


# ---------------------------------------------------------
# Model
# ---------------------------------------------------------

model = AutoModelForSequenceClassification.from_pretrained(
    "bert-base-uncased",
    num_labels=1,
    local_files_only=True,
).cuda()

model.config.problem_type = (
    "multi_label_classification"
)

model.config.id2label = {
    0: "high_severity"
}

model.config.label2id = {
    "high_severity": 0
}

use_bf16 = torch.cuda.is_bf16_supported()


def collate(batch):
    inputs = tokenizer(
        [r["text_input"] for r in batch],
        padding="max_length",
        truncation=True,
        max_length=MAX_LENGTH,
        return_tensors="pt",
    ).to("cuda")

    labels = torch.tensor(
        [
            r["weak_label"] == "high_severity"
            for r in batch
        ],
        dtype=torch.float32,
        device="cuda",
    )

    groups = [
        str(r["rule_id"])
        for r in batch
    ]

    return inputs, labels, groups


train_loader = DataLoader(
    train_rows,
    batch_size=BATCH_SIZE,
    shuffle=True,
    collate_fn=collate,
)

optimizer = torch.optim.AdamW(
    model.parameters(),
    lr=LR,
)


# ---------------------------------------------------------
# Train exactly 1 epoch
# ---------------------------------------------------------

model.train()

steps = 0
train_loss = 0.0
train_count = 0

print("\nTRAINING")

for inputs, labels, groups in train_loader:
    optimizer.zero_grad(
        set_to_none=True
    )

    with torch.autocast(
        "cuda",
        dtype=torch.bfloat16,
        enabled=use_bf16,
    ):
        logits = model(
            **inputs
        ).logits.squeeze(-1).float()

        sample_weights = torch.tensor(
            [
                rule_weights[g]
                for g in groups
            ],
            device="cuda",
        )

        row_loss = (
            torch.nn.functional
            .binary_cross_entropy_with_logits(
                logits,
                labels,
                reduction="none",
            )
        )

        loss = (
            row_loss * sample_weights
        ).mean()

    if not math.isfinite(loss.item()):
        raise RuntimeError(
            "Nonfinite training loss"
        )

    loss.backward()

    torch.nn.utils.clip_grad_norm_(
        model.parameters(),
        1.0,
        error_if_nonfinite=True,
    )

    optimizer.step()

    steps += 1
    train_loss += (
        loss.item() * len(labels)
    )
    train_count += len(labels)

    if steps % 50 == 0:
        print(
            json.dumps({
                "step": steps,
                "loss": loss.item(),
            }),
            flush=True,
        )


train_mean_loss = (
    train_loss / train_count
)

print(
    "Train mean loss:",
    train_mean_loss
)


# ---------------------------------------------------------
# Evaluation
# ---------------------------------------------------------

model.eval()


def evaluate(rows):
    results = []

    loader = DataLoader(
        rows,
        batch_size=64,
        shuffle=False,
        collate_fn=collate,
    )

    with torch.no_grad():
        for inputs, labels, groups in loader:

            with torch.autocast(
                "cuda",
                dtype=torch.bfloat16,
                enabled=use_bf16,
            ):
                logits = model(
                    **inputs
                ).logits.squeeze(-1)

            scores = torch.sigmoid(
                logits.float()
            ).cpu().tolist()

            actuals = labels.bool().cpu().tolist()

            for score, actual, rule in zip(
                scores,
                actuals,
                groups,
            ):
                results.append({
                    "rule_id": rule,
                    "actual": bool(actual),
                    "score": float(score),
                })

    return results


evaluation = {}

for key in [
    "dev-all.jsonl",
    "dev-clean.jsonl",
    "dev-seen.jsonl",
    "dev-unseen.jsonl",
]:

    print("\nEvaluating:", key)

    results = evaluate(
        splits[key]
    )

    by_rule_rows = defaultdict(list)

    for row in results:
        by_rule_rows[
            row["rule_id"]
        ].append(row)

    evaluation[key] = {
        "metrics": summarize(results),
        "scores": score_summary(results),
        "by_rule": {
            rule: {
                "metrics": summarize(r),
                "scores": score_summary(r),
            }
            for rule, r
            in sorted(by_rule_rows.items())
        },
    }


torch.cuda.synchronize()


# ---------------------------------------------------------
# Save development checkpoint
# ---------------------------------------------------------

OUTPUT.mkdir(
    parents=True,
    exist_ok=False,
)

model.save_pretrained(
    OUTPUT / "model"
)

tokenizer.save_pretrained(
    OUTPUT / "model"
)


report = {
    "experiment":
        "wazuh-severity-temporal-v1",

    "status":
        "development-only",

    "production_ready":
        False,

    "variant":
        "temporal-v1-rule-balanced-loss",

    "base_model":
        "bert-base-uncased",

    "seed":
        SEED,

    "epochs_completed":
        1,

    "batch_size":
        BATCH_SIZE,

    "max_length":
        MAX_LENGTH,

    "learning_rate":
        LR,

    "threshold":
        THRESHOLD,

    "rule_balanced_loss":
        True,

    "steps":
        steps,

    "train_mean_loss":
        train_mean_loss,

    "bf16":
        use_bf16,

    "device":
        torch.cuda.get_device_name(0),

    "versions": {
        "torch":
            torch.__version__,

        "transformers":
            transformers.__version__,
    },

    "dataset_manifest_sha256":
        file_hash(
            DATA / "manifest.json"
        ),

    "truncated_rows_by_rule":
        truncation,

    "evaluation":
        evaluation,

    "score_definition":
        (
            "sigmoid(single logit); "
            "Wazuh high-severity proxy, "
            "not threat probability"
        ),

    "holdouts_evaluated":
        False,

    "notes": [
        "Only original v2 training split was used.",
        "Original validation not evaluated.",
        "Old-test quarantine not evaluated.",
        "Reserve 479 not evaluated.",
        "Unseen temporal support is only 19 rows.",
        "dev-clean removes four exact-text overlaps."
    ],
}


(OUTPUT / "training_report.json").write_text(
    json.dumps(
        report,
        indent=2
    ),
    encoding="utf-8",
)

(OUTPUT / "dataset_manifest.json").write_text(
    json.dumps(
        manifest,
        indent=2
    ),
    encoding="utf-8",
)

(OUTPUT / "RUN_COMPLETE").write_text(
    "temporal-v1 development training complete\n",
    encoding="utf-8",
)


print("\n" + "=" * 72)
print("RESULTS")
print("=" * 72)

for name, result in evaluation.items():
    print(
        "\n",
        name,
        json.dumps(
            result["metrics"],
            indent=2
        )
    )


print(
    "\nSaved:",
    OUTPUT
)
