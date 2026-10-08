"""Build a reproducible Wazuh-context severity experiment, never an attack ground truth."""
import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path):
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def context_text(event):
    """Only these two fields become model input; no raw-object serialization."""
    description = event["rule"].get("description") or ""
    log = event.get("full_log") or ""
    if not isinstance(description, str) or not isinstance(log, str):
        raise ValueError("Expected string description/full_log")
    description, log = description.strip(), log.strip()
    if not description and not log:
        raise ValueError("Event has neither description nor full_log")
    return f"Description: {description or '[missing]'}\nLog: {log or '[missing]'}"


def build(snapshot, previous, output):
    if output.exists():
        raise ValueError("Output already exists; choose a new run directory")
    owners = {}
    previous_hashes = {}
    for split in ("train", "validation", "test"):
        path = previous / f"wazuh-nlp-{split}.jsonl"
        previous_hashes[path.name] = sha256(path)
        for row in read_jsonl(path):
            rule = str(row["rule_id"])
            if rule in owners and owners[rule] != split:
                raise ValueError(f"Previous rule crosses splits: {rule}")
            owners[rule] = split

    files = sorted(snapshot.rglob("*.json.gz"))
    if not files:
        raise ValueError("No archived JSONL files found")
    buckets = {name: [] for name in ("train", "validation", "quarantine_old_test", "reserve_new_rules")}
    counts = {name: Counter() for name in buckets}
    labels = {name: Counter() for name in buckets}
    seen = {}
    raw_rows = duplicates = 0
    sources = {}
    for path in files:
        relative = str(path.relative_to(snapshot)).replace("\\", "/")
        sources[relative] = sha256(path)
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                raw_rows += 1
                event = json.loads(line)
                identity = [event["manager"]["name"], event["agent"]["id"], event["id"]]
                if any(value is None or str(value) == "" for value in identity):
                    raise ValueError(f"Missing event identity at {relative}:{line_number}")
                identity = [str(value) for value in identity]
                key = tuple(identity)
                payload_hash = hashlib.sha256(json.dumps(event, sort_keys=True).encode()).hexdigest()
                if key in seen:
                    if seen[key] != payload_hash:
                        raise ValueError(f"Conflicting event identity at {relative}:{line_number}")
                    duplicates += 1
                    continue
                seen[key] = payload_hash
                event_id = hashlib.sha256(json.dumps(identity).encode()).hexdigest()
                rule = str(event["rule"]["id"])
                level = event["rule"]["level"]
                if type(level) is not int or not 0 <= level <= 15:
                    raise ValueError(f"Invalid rule level at {relative}:{line_number}")
                # Explicit experimental definition, consistent with observed v1 labels.
                label = "high_severity" if level >= 7 else "low_severity"
                owner = owners.get(rule)
                bucket = {"train": "train", "validation": "validation", "test": "quarantine_old_test"}.get(
                    owner, "reserve_new_rules"
                )
                row = dict(event_id=event_id, rule_id=rule, source_file=relative, source_line=line_number)
                if bucket in ("train", "validation"):
                    row.update(text_input=context_text(event), weak_label=label,
                               text_source="rule_description+full_log", rule_level=level)
                # Reserved/quarantined files contain only source pointers, never training text.
                buckets[bucket].append(row)
                counts[bucket][rule] += 1
                labels[bucket][label] += 1

    for split in ("train", "validation"):
        if len(labels[split]) != 2:
            raise ValueError(f"{split} must contain both labels")
    text_labels = {}
    text_sets = {}
    for split in ("train", "validation"):
        grouped = defaultdict(set)
        for row in buckets[split]:
            grouped[row["text_input"]].add(row["weak_label"])
        text_labels[split] = sum(len(v) > 1 for v in grouped.values())
        text_sets[split] = set(grouped)
    overlap = len(text_sets["train"] & text_sets["validation"])
    manifest = dict(
        schema_version=1, experiment="wazuh-severity-context-v2-candidate",
        scope="Weakly supervised Wazuh severity; description is supplied by Wazuh rules, not independent attack evidence",
        label_definition="high_severity iff rule.level >= 7; else low_severity",
        input_fields=["rule.description", "full_log"],
        split_policy="Keep old rule memberships; quarantine old-test rules; reserve all new rules",
        snapshot=str(snapshot), source_sha256=sources, previous_split_sha256=previous_hashes,
        builder_sha256=sha256(Path(__file__)), raw_rows=raw_rows, duplicates_removed=duplicates,
        counts={key: len(value) for key, value in buckets.items()},
        rules={key: dict(value) for key, value in counts.items()},
        labels={key: dict(value) for key, value in labels.items()},
        conflicting_texts=text_labels, train_validation_exact_text_overlap=overlap,
        ready_for_training=False,
        readiness_note="Candidate only: review feature leakage, conflicts, overlap and tokenizer truncation before training",
        evaluation_note="Expanded validation is development data, not directly comparable to v1; no fresh test evaluation performed",
    )
    output.mkdir(parents=True, exist_ok=False)
    output_hashes = {}
    for bucket, rows in buckets.items():
        filename = f"wazuh-nlp-{bucket}.jsonl" if bucket in ("train", "validation") else f"{bucket}-index.jsonl"
        path = output / filename
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            for row in rows:
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
        output_hashes[filename] = sha256(path)
    manifest["output_sha256"] = output_hashes
    with (output / "manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--previous", type=Path, default=Path("/previous"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build(args.snapshot, args.previous, args.output)
    print(json.dumps({key: report[key] for key in (
        "counts", "labels", "conflicting_texts", "train_validation_exact_text_overlap", "ready_for_training"
    )}, indent=2))
    print("Saved:", args.output)


if __name__ == "__main__":
    main()
