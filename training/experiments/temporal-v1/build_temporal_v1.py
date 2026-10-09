import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

SRC = Path(
    "/dataset/wazuh-context-v2-20261008T185539Z-1179365"
)

SOURCE = SRC / "wazuh-nlp-train.jsonl"
OUT = Path("/out")

BOUNDARY = date(2026, 10, 7)

DATE_RE = re.compile(
    r"^(\d{4})/([A-Za-z]{3})/ossec-alerts-(\d{2})\.json\.gz$"
)

MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4,
    "May": 5, "Jun": 6, "Jul": 7, "Aug": 8,
    "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


def sha256(path):
    h = hashlib.sha256()

    with Path(path).open("rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b""
        ):
            h.update(chunk)

    return h.hexdigest()


def source_date(row):
    m = DATE_RE.match(row["source_file"])

    if not m:
        raise ValueError(
            f"Cannot parse source file: {row['source_file']}"
        )

    return date(
        int(m.group(1)),
        MONTHS[m.group(2)],
        int(m.group(3)),
    )


def load(path):
    with Path(path).open(
        encoding="utf-8"
    ) as f:
        return [
            json.loads(x)
            for x in f
            if x.strip()
        ]


def write_jsonl(path, rows):
    with Path(path).open(
        "x",
        encoding="utf-8"
    ) as f:

        for row in rows:
            f.write(
                json.dumps(
                    row,
                    ensure_ascii=False
                ) + "\n"
            )


rows = load(SOURCE)

if len(rows) != 5232:
    raise RuntimeError(
        f"Expected 5232 source rows, got {len(rows)}"
    )


train = [
    r for r in rows
    if source_date(r) < BOUNDARY
]

dev_all = [
    r for r in rows
    if source_date(r) >= BOUNDARY
]


if len(train) != 3922:
    raise RuntimeError(
        f"Expected train=3922, got {len(train)}"
    )

if len(dev_all) != 1310:
    raise RuntimeError(
        f"Expected dev_all=1310, got {len(dev_all)}"
    )


# ------------------------------------------------------
# Identity leakage
# ------------------------------------------------------

train_ids = {
    r["event_id"]
    for r in train
}

dev_ids = {
    r["event_id"]
    for r in dev_all
}

if train_ids & dev_ids:
    raise RuntimeError(
        "Event identity leakage"
    )


# ------------------------------------------------------
# Exact-text overlap
# ------------------------------------------------------

train_texts = {
    r["text_input"]
    for r in train
}

overlap_rows = [
    r for r in dev_all
    if r["text_input"] in train_texts
]

if len(overlap_rows) != 4:
    raise RuntimeError(
        f"Expected 4 overlapping later rows, got {len(overlap_rows)}"
    )

dev_clean = [
    r for r in dev_all
    if r["text_input"] not in train_texts
]

if len(dev_clean) != 1306:
    raise RuntimeError(
        f"Expected dev_clean=1306, got {len(dev_clean)}"
    )


# ------------------------------------------------------
# Seen / unseen rules
# ------------------------------------------------------

train_rules = {
    str(r["rule_id"])
    for r in train
}

dev_seen = [
    r for r in dev_all
    if str(r["rule_id"]) in train_rules
]

dev_unseen = [
    r for r in dev_all
    if str(r["rule_id"]) not in train_rules
]

if len(dev_seen) != 1291:
    raise RuntimeError(
        f"Expected seen=1291, got {len(dev_seen)}"
    )

if len(dev_unseen) != 19:
    raise RuntimeError(
        f"Expected unseen=19, got {len(dev_unseen)}"
    )

unseen_rules = sorted({
    str(r["rule_id"])
    for r in dev_unseen
})

expected_unseen = [
    "19011",
    "503",
    "5901",
    "5902",
    "5904",
]

if unseen_rules != expected_unseen:
    raise RuntimeError(
        f"Unexpected unseen rules: {unseen_rules}"
    )


# ------------------------------------------------------
# Labels
# ------------------------------------------------------

def label_counts(rows):
    return dict(
        Counter(
            r["weak_label"]
            for r in rows
        )
    )


# ------------------------------------------------------
# Rule-label consistency
# ------------------------------------------------------

rule_labels = defaultdict(set)

for row in rows:
    rule_labels[
        str(row["rule_id"])
    ].add(
        row["weak_label"]
    )

conflicting_rules = {
    rule: sorted(labels)
    for rule, labels
    in rule_labels.items()
    if len(labels) > 1
}

if conflicting_rules:
    raise RuntimeError(
        f"Rule-label conflicts: {conflicting_rules}"
    )


# ------------------------------------------------------
# Write output
# ------------------------------------------------------

OUT.mkdir(
    parents=True,
    exist_ok=True
)

write_jsonl(
    OUT / "train.jsonl",
    train
)

write_jsonl(
    OUT / "dev-all.jsonl",
    dev_all
)

write_jsonl(
    OUT / "dev-clean.jsonl",
    dev_clean
)

write_jsonl(
    OUT / "dev-seen.jsonl",
    dev_seen
)

write_jsonl(
    OUT / "dev-unseen.jsonl",
    dev_unseen
)

write_jsonl(
    OUT / "exact-overlap.jsonl",
    overlap_rows
)


manifest = {
    "experiment": "wazuh-severity-temporal-v1",
    "status": "development-only",
    "production_ready": False,

    "source_dataset":
        "wazuh-context-v2-20261008T185539Z-1179365",

    "source_train_sha256":
        sha256(SOURCE),

    "source_manifest_sha256":
        sha256(SRC / "manifest.json"),

    "time_basis":
        "Wazuh UTC archive/event date",

    "boundary":
        "2026-10-07T00:00:00Z",

    "train_rows":
        len(train),

    "dev_all_rows":
        len(dev_all),

    "dev_clean_rows":
        len(dev_clean),

    "dev_seen_rows":
        len(dev_seen),

    "dev_unseen_rows":
        len(dev_unseen),

    "exact_overlap_later_rows":
        len(overlap_rows),

    "train_labels":
        label_counts(train),

    "dev_all_labels":
        label_counts(dev_all),

    "dev_clean_labels":
        label_counts(dev_clean),

    "dev_seen_labels":
        label_counts(dev_seen),

    "dev_unseen_labels":
        label_counts(dev_unseen),

    "unseen_rules":
        unseen_rules,

    "event_id_overlap":
        0,

    "rule_label_conflicts":
        0,

    "timezone_verification": {
        "boundary_crossing_candidates": 25,
        "source_date_equals_wazuh_utc":
            "25/25",
        "full_log_date_equals_asia_bangkok":
            "25/25",
        "partition_adjustment_required":
            False,
    },

    "notes": [
        "Only original v2 training split was used.",
        "Original validation was not used.",
        "Old-test quarantine was not used.",
        "Reserve-new-rules set was not used.",
        "dev-clean excludes four later exact-text overlaps.",
        "Unseen-rule metrics are exploratory because support is only 19 rows."
    ]
}


manifest_path = (
    OUT / "manifest.json"
)

manifest_path.write_text(
    json.dumps(
        manifest,
        indent=2
    ),
    encoding="utf-8"
)


print(
    json.dumps(
        manifest,
        indent=2
    )
)
