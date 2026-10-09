#!/usr/bin/env python3

import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path


TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_.:+-]*")


def load_jsonl(path):
    rows = []

    with Path(path).open(encoding="utf-8") as stream:
        for line_no, line in enumerate(stream, 1):
            if not line.strip():
                continue

            row = json.loads(line)
            row["_line"] = line_no
            rows.append(row)

    return rows


def tokenize(text):
    return {
        token.lower()
        for token in TOKEN_RE.findall(text or "")
        if len(token) >= 2
    }


def normalize_template(text):
    text = (text or "").lower()

    text = re.sub(
        r"\b\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\b",
        "<timestamp>",
        text,
    )

    text = re.sub(
        r"\b\d+(?:\.\d+){1,}(?:[-+~][a-z0-9_.:+~-]+)?\b",
        "<version>",
        text,
    )

    text = re.sub(
        r"\b\d+\b",
        "<n>",
        text,
    )

    return " ".join(text.split())


def jaccard(a, b):
    if not a and not b:
        return 1.0

    union = a | b

    if not union:
        return 0.0

    return len(a & b) / len(union)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--train",
        required=True,
    )

    parser.add_argument(
        "--validation",
        required=True,
    )

    parser.add_argument(
        "--rule",
        default="2901",
    )

    parser.add_argument(
        "--neighbors",
        type=int,
        default=15,
    )

    args = parser.parse_args()

    train = load_jsonl(args.train)
    validation = load_jsonl(args.validation)

    rule = str(args.rule)

    train_target = [
        row for row in train
        if str(row.get("rule_id")) == rule
    ]

    validation_target = [
        row for row in validation
        if str(row.get("rule_id")) == rule
    ]

    print("=" * 70)
    print("RULE ANALYSIS:", rule)
    print("=" * 70)

    print("\nDATASET COUNTS")
    print("train total      :", len(train))
    print("validation total :", len(validation))
    print("rule in train    :", len(train_target))
    print("rule in validation:", len(validation_target))

    print("\nRULE LABELS")

    for name, rows in (
        ("train", train_target),
        ("validation", validation_target),
    ):
        labels = Counter(
            row.get("weak_label")
            for row in rows
        )

        print(name, dict(labels))

    if not validation_target:
        raise SystemExit(
            "Rule not found in validation"
        )

    train_texts = {
        row.get("text_input", "")
        for row in train
    }

    exact_overlap = sum(
        row.get("text_input", "") in train_texts
        for row in validation_target
    )

    print("\nEXACT TEXT OVERLAP")
    print(
        f"{exact_overlap}/{len(validation_target)}"
    )

    # --------------------------------------------------
    # Template overlap
    # --------------------------------------------------

    template_labels = {}

    for row in train:
        template = normalize_template(
            row.get("text_input", "")
        )

        template_labels.setdefault(
            template,
            set()
        ).add(
            row.get("weak_label")
        )

    template_match = Counter()

    for row in validation_target:
        template = normalize_template(
            row.get("text_input", "")
        )

        labels = template_labels.get(
            template,
            set()
        )

        if not labels:
            template_match["none"] += 1

        elif labels == {"high_severity"}:
            template_match["high_only"] += 1

        elif labels == {"low_severity"}:
            template_match["low_only"] += 1

        else:
            template_match["mixed"] += 1

    print("\nNORMALIZED TEMPLATE OVERLAP")
    print(dict(template_match))

    # --------------------------------------------------
    # Token bias
    # --------------------------------------------------

    high_rows = [
        row for row in train
        if row.get("weak_label")
        == "high_severity"
    ]

    low_rows = [
        row for row in train
        if row.get("weak_label")
        == "low_severity"
    ]

    high_df = Counter()
    low_df = Counter()

    for row in high_rows:
        high_df.update(
            tokenize(
                row.get("text_input", "")
            )
        )

    for row in low_rows:
        low_df.update(
            tokenize(
                row.get("text_input", "")
            )
        )

    target_tokens = set()

    for row in validation_target:
        target_tokens |= tokenize(
            row.get("text_input", "")
        )

    token_scores = []

    for token in target_tokens:
        high_rate = (
            high_df[token] + 1
        ) / (
            len(high_rows) + 2
        )

        low_rate = (
            low_df[token] + 1
        ) / (
            len(low_rows) + 2
        )

        bias = math.log2(
            high_rate / low_rate
        )

        token_scores.append(
            (
                bias,
                token,
                high_df[token],
                low_df[token],
            )
        )

    token_scores.sort(
        reverse=True
    )

    print(
        "\nTOKENS IN RULE 2901 "
        "MOST ASSOCIATED WITH HIGH SEVERITY"
    )

    for bias, token, high, low in token_scores[:30]:
        print(
            f"{token:30} "
            f"log2_bias={bias:8.3f} "
            f"high_df={high:5} "
            f"low_df={low:5}"
        )

    # --------------------------------------------------
    # Nearest training examples
    # --------------------------------------------------

    train_tokenized = [
        (
            row,
            tokenize(
                row.get("text_input", "")
            ),
        )
        for row in train
    ]

    neighbors = []

    for target in validation_target:

        target_tokens = tokenize(
            target.get(
                "text_input",
                ""
            )
        )

        best = None

        for candidate, candidate_tokens in train_tokenized:

            score = jaccard(
                target_tokens,
                candidate_tokens,
            )

            if (
                best is None
                or score > best[0]
            ):
                best = (
                    score,
                    candidate,
                    target,
                )

        if best is not None:
            neighbors.append(best)

    neighbors.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    print("\nNEAREST TRAINING EXAMPLES")

    for score, candidate, target in \
            neighbors[:args.neighbors]:

        print("-" * 70)

        print(
            "similarity :",
            round(score, 4)
        )

        print(
            "train rule :",
            candidate.get("rule_id")
        )

        print(
            "train label:",
            candidate.get("weak_label")
        )

        print(
            "train text :",
            candidate.get(
                "text_input",
                ""
            )[:300]
        )

        print(
            "2901 text  :",
            target.get(
                "text_input",
                ""
            )[:300]
        )

    print("\nDONE")


if __name__ == "__main__":
    main()
