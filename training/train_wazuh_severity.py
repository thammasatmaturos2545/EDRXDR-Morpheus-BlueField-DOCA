"""Weakly supervised Wazuh severity baseline; not an independent threat detector."""
import argparse
import hashlib
import json
import math
import random
from pathlib import Path


def load_split(path, text_key, label_key, group_key):
    rows = []
    with open(path, encoding="utf-8") as stream:
        for line_no, line in enumerate(stream, 1):
            row = json.loads(line)
            if not isinstance(row.get(text_key), str) or not row[text_key].strip():
                raise ValueError(f"{path}:{line_no}: missing/nonempty string {text_key}")
            label = row.get(label_key)
            if isinstance(label, str):
                label = {"low_severity": 0, "high_severity": 1}.get(label, label)
            if type(label) not in (int, float) or label not in (0, 1):
                raise ValueError(f"{path}:{line_no}: {label_key} must be 0/1 or low_severity/high_severity")
            if group_key not in row or row[group_key] is None:
                raise ValueError(f"{path}:{line_no}: missing {group_key}")
            rows.append((row[text_key], float(label), str(row[group_key])))
    if not rows:
        raise ValueError(f"Empty split: {path}")
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-dir", default="/data")
    p.add_argument("--output-dir", required=True)
    p.add_argument("--text-key", default="text")
    p.add_argument("--label-key", default="label")
    p.add_argument("--group-key", default="rule_id")
    p.add_argument("--epochs", type=int, default=1)
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--max-length", type=int, default=256)
    p.add_argument("--learning-rate", type=float, default=2e-5)
    p.add_argument("--smoke", action="store_true")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()
    if args.epochs < 1 or args.batch_size < 1 or not 2 <= args.max_length <= 512:
        p.error("epochs/batch-size must be positive; max-length must be 2..512")
    paths = [Path(args.data_dir) / f"wazuh-nlp-{name}.jsonl" for name in ("train", "validation", "test")]
    splits = [load_split(path, args.text_key, args.label_key, args.group_key) for path in paths]
    if [len(s) for s in splits] != [4936, 1143, 1316]:
        raise ValueError(f"Unexpected split sizes: {[len(s) for s in splits]}")
    groups = [{r[2] for r in s} for s in splits]
    if any(groups[i] & groups[j] for i, j in ((0, 1), (0, 2), (1, 2))):
        raise ValueError("Group leakage across prepared splits")
    if {r[1] for r in splits[0]} != {0.0, 1.0}:
        raise ValueError("Training data must contain both classes")
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=False)
    import torch
    from torch.utils.data import DataLoader
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU required; no CPU fallback")
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased", local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        "bert-base-uncased", num_labels=1, local_files_only=True
    ).cuda()
    model.config.problem_type = "multi_label_classification"
    def collate(rows):
        encoded = tokenizer([r[0] for r in rows], padding="max_length", truncation=True,
                            max_length=args.max_length, return_tensors="pt")
        return {k: v.cuda() for k, v in encoded.items()}, torch.tensor([r[1] for r in rows], device="cuda")
    train = DataLoader(splits[0], batch_size=args.batch_size, shuffle=True, collate_fn=collate)
    validation_rows = splits[1][:64] if args.smoke else splits[1]
    validation = DataLoader(validation_rows, batch_size=args.batch_size, collate_fn=collate)
    loss_fn = torch.nn.BCEWithLogitsLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)
    steps = 0
    use_bf16 = torch.cuda.is_bf16_supported()
    def context():
        return torch.autocast("cuda", dtype=torch.bfloat16, enabled=use_bf16)
    def evaluate(loader):
        model.eval()
        total_loss = count = tp = fp = tn = fn = 0
        with torch.no_grad():
            for inputs, labels in loader:
                with context():
                    logits = model(**inputs).logits.squeeze(-1).float()
                    loss = loss_fn(logits, labels)
                predictions = torch.sigmoid(logits) >= 0.5
                positive = labels.bool()
                tp += int((predictions & positive).sum())
                fp += int((predictions & ~positive).sum())
                tn += int((~predictions & ~positive).sum())
                fn += int((~predictions & positive).sum())
                total_loss += float(loss) * len(labels)
                count += len(labels)
        return dict(loss=total_loss/count, n=count, threshold=0.5, tp=tp, fp=fp, tn=tn, fn=fn,
                    precision=tp/max(tp+fp, 1), recall=tp/max(tp+fn, 1), f1=2*tp/max(2*tp+fp+fn, 1))
    history = []
    for epoch in range(1 if args.smoke else args.epochs):
        model.train()
        for inputs, labels in train:
            optimizer.zero_grad(set_to_none=True)
            with context():
                logits = model(**inputs).logits.squeeze(-1).float()
                loss = loss_fn(logits, labels)
            if not math.isfinite(float(loss)):
                raise RuntimeError("Nonfinite training loss")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            steps += 1
            if steps % 10 == 0:
                print(json.dumps(dict(step=steps, train_loss=float(loss))), flush=True)
            if args.smoke and steps >= 10:
                break
        metrics = evaluate(validation)
        history.append(metrics)
        print(json.dumps(dict(epoch=epoch+1, validation=metrics)), flush=True)
    # Test is held out during development and smoke training.
    model.save_pretrained(output)
    tokenizer.save_pretrained(output)
    report = dict(model="wazuh-severity-nlp-v1", base_model="bert-base-uncased",
                  scope=__doc__, smoke=args.smoke, steps=steps, validation=history,
                  test_evaluated=False, device=torch.cuda.get_device_name(0), bf16=use_bf16,
                  args=vars(args), versions=dict(torch=torch.__version__),
                  data_sha256={path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},
                  score="sigmoid(single output logit); Wazuh high-severity proxy, not threat probability")
    (output / "training_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Saved to {output}", flush=True)


if __name__ == "__main__":
    main()
