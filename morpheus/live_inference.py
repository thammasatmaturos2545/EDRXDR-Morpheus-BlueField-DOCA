"""Bounded live Wazuh severity inference using the verified Morpheus model.

This worker is intentionally gated and bounded.  It does not perform automated
response and its score is a Wazuh high-severity proxy, not attack probability.
"""

import argparse
import hashlib
import json
import math
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path


CHECKPOINT = Path(
    "/models/wazuh-severity-context-v2-balanced-20261008T190719Z-1398863"
)

REPORT = Path(
    "/models/morpheus-raw-offline-check-20261008T203523Z-1803526/"
    "parity_report.json"
)

VOCAB = Path(
    "/opt/conda/envs/morpheus/lib/python3.12/site-packages/"
    "morpheus/data/bert-base-uncased-hash.txt"
)

BROKER = "kafka:29092"
INPUT = "morpheus-input"
OUTPUT = "morpheus-output"
GROUP = "edrxdr-live-morpheus-severity-v1"

THRESHOLD = 0.5

UID = re.compile(r"^[0-9a-f]{64}$")


def digest(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def strict_json(value):
    def reject(_):
        raise ValueError(
            "Non-finite JSON is forbidden"
        )

    return json.loads(
        value,
        parse_constant=reject,
    )


def canonical_wazuh_uid(raw):
    if not isinstance(raw, dict):
        raise ValueError(
            "raw_event must be an object"
        )

    manager = raw.get("manager")
    agent = raw.get("agent")

    if (
        not isinstance(manager, dict)
        or not isinstance(agent, dict)
    ):
        raise ValueError(
            "Missing Wazuh identity objects"
        )

    values = [
        manager.get("name"),
        agent.get("id"),
        raw.get("id"),
    ]

    parts = []

    for value in values:
        if (
            isinstance(value, bool)
            or not isinstance(
                value,
                (str, int),
            )
        ):
            raise ValueError(
                "Invalid Wazuh identity"
            )

        value = str(value).strip()

        if not value:
            raise ValueError(
                "Missing Wazuh identity"
            )

        size = len(
            value.encode("utf-8")
        )

        parts.append(
            f"{size}:{value}"
        )

    canonical = (
        "wazuh-v1|"
        + "|".join(parts)
    )

    return hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()


def validate_input(event, key):
    if not isinstance(event, dict):
        raise ValueError(
            "Expected event object"
        )

    if event.get("source_type") != "wazuh":
        raise ValueError(
            "Expected Wazuh source"
        )

    uid = event.get("event_uid")

    if (
        not isinstance(uid, str)
        or UID.fullmatch(uid) is None
    ):
        raise ValueError(
            "Invalid event_uid"
        )

    if key != uid.encode("ascii"):
        raise ValueError(
            "Kafka key/event_uid mismatch"
        )

    if event.get(
        "source_topic"
    ) != "wazuh-alerts":
        raise ValueError(
            "Unexpected original topic"
        )

    for field in (
        "source_partition",
        "source_offset",
    ):
        value = event.get(field)

        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
        ):
            raise ValueError(
                f"Invalid {field}"
            )

    raw = event.get("raw_event")

    expected_uid = canonical_wazuh_uid(
        raw
    )

    if expected_uid != uid:
        raise ValueError(
            "raw_event/event_uid mismatch"
        )

    return raw, uid


def build_output(
    event,
    key,
    score,
    input_partition,
    input_offset,
    *,
    model_name,
    artifact_hashes,
    vocab_hash_sha256,
    engine_sha256,
    worker_sha256,
    scored_at_utc,
):
    raw, uid = validate_input(
        event,
        key,
    )

    if (
        isinstance(score, bool)
        or not isinstance(
            score,
            (int, float),
        )
        or not math.isfinite(
            float(score)
        )
        or not 0 <= float(score) <= 1
    ):
        raise ValueError(
            "Invalid inference score"
        )

    for name, value in (
        (
            "input_partition",
            input_partition,
        ),
        (
            "input_offset",
            input_offset,
        ),
    ):
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
        ):
            raise ValueError(
                f"Invalid {name}"
            )

    score = float(score)

    return {
        "schema_version":
            "live-severity-1",

        "event_uid":
            uid,

        "source_type":
            "wazuh",

        "processing_mode":
            "live",

        "analysis_engine":
            "nvidia-morpheus-context-severity-v1",

        "model_name":
            model_name,

        "text_contract_version":
            "wazuh-context-v2-raw-1",

        "high_severity_score":
            score,

        "predicted_label":
            (
                "high_severity"
                if score >= THRESHOLD
                else "low_severity"
            ),

        "threshold":
            THRESHOLD,

        "wazuh_rule_id":
            (raw.get("rule") or {}).get(
                "id"
            ),

        "wazuh_rule_level":
            (raw.get("rule") or {}).get(
                "level"
            ),

        # Original Wazuh/Kafka provenance.
        "source_topic":
            event["source_topic"],

        "source_partition":
            event["source_partition"],

        "source_offset":
            event["source_offset"],

        # AI worker input provenance.
        "input_topic":
            INPUT,

        "input_partition":
            input_partition,

        "input_offset":
            input_offset,

        "scored_at_utc":
            scored_at_utc,

        "artifact_hashes":
            artifact_hashes,

        "vocab_hash_sha256":
            vocab_hash_sha256,

        "engine_sha256":
            engine_sha256,

        "worker_sha256":
            worker_sha256,

        "production_ready":
            False,

        "automated_response_allowed":
            False,
    }


def verify_artifacts():
    evidence = strict_json(
        REPORT.read_text()
    )

    if (
        evidence.get("status") != "PASS"
        or evidence.get("issues")
    ):
        raise ValueError(
            "Successful parity evidence required"
        )

    files = {
        "checkpoint_weights_sha256":
            CHECKPOINT
            / "model.safetensors",

        "adapter_sha256":
            Path(
                "/scripts/"
                "morpheus_context_inference.py"
            ),

        "preprocessing_adapter_sha256":
            Path(
                "/scripts/"
                "morpheus_bert_special_tokens.py"
            ),

        "raw_adapter_sha256":
            Path(
                "/scripts/"
                "raw_event_contract.py"
            ),

        "text_builder_sha256":
            Path(
                "/scripts/"
                "build_context_dataset.py"
            ),
    }

    hashes = {}

    for field, path in files.items():
        actual = digest(path)

        if actual != evidence.get(field):
            raise ValueError(
                "Artifact hash mismatch: "
                + field
            )

        hashes[field] = actual

    if not VOCAB.is_file():
        raise ValueError(
            "Missing Morpheus vocabulary hash"
        )

    return hashes


def require_run_permission():
    if os.environ.get(
        "LIVE_INFERENCE_RUN_ALLOWED"
    ) != "1":
        raise RuntimeError(
            "Live inference execution "
            "not explicitly allowed"
        )


def main():
    parser = argparse.ArgumentParser(
        description=__doc__
    )

    parser.add_argument(
        "--max-events",
        type=int,
        default=1,
    )

    parser.add_argument(
        "--seconds",
        type=int,
        default=120,
    )

    args = parser.parse_args()

    if (
        args.max_events < 1
        or args.max_events > 32
        or args.seconds < 1
        or args.seconds > 600
    ):
        parser.error(
            "max-events must be 1..32; "
            "seconds must be 1..600"
        )

    require_run_permission()

    hashes = verify_artifacts()

    # Heavy/GPU modules are imported only after all
    # source and artifact safety checks pass.
    from confluent_kafka import (
        Consumer,
        Producer,
        TopicPartition,
    )

    from raw_event_contract import (
        event_text,
    )

    from morpheus_replay_engine import (
        score_texts,
    )

    consumer = Consumer({
        "bootstrap.servers":
            BROKER,

        "group.id":
            GROUP,

        "enable.auto.commit":
            False,

        "enable.auto.offset.store":
            False,

        # A new live group must not backfill
        # historical retained traffic.
        "auto.offset.reset":
            "latest",
    })

    producer = Producer({
        "bootstrap.servers":
            BROKER,

        "enable.idempotence":
            True,

        "acks":
            "all",

        "delivery.timeout.ms":
            30000,
    })

    processed = 0
    deadline = (
        time.monotonic()
        + args.seconds
    )

    consumer.subscribe([INPUT])

    try:
        while (
            processed < args.max_events
            and time.monotonic()
            < deadline
        ):
            message = consumer.poll(1)

            if message is None:
                continue

            if message.error():
                raise RuntimeError(
                    "Kafka input error"
                )

            event = strict_json(
                message.value()
            )

            raw, uid = validate_input(
                event,
                message.key(),
            )

            text = event_text(raw)

            print(
                "Identity/artifacts PASS; "
                "starting Morpheus GPU inference",
                flush=True,
            )

            score = score_texts(
                [text],
                CHECKPOINT,
                VOCAB,
            )[0]

            output = build_output(
                event,
                message.key(),
                score,
                message.partition(),
                message.offset(),
                model_name=
                    CHECKPOINT.name,
                artifact_hashes=
                    hashes,
                vocab_hash_sha256=
                    digest(VOCAB),
                engine_sha256=
                    digest(
                        "/replay/"
                        "morpheus_replay_engine.py"
                    ),
                worker_sha256=
                    digest(__file__),
                scored_at_utc=
                    datetime.now(
                        timezone.utc
                    ).isoformat(),
            )

            delivery = []

            producer.produce(
                OUTPUT,
                key=uid.encode(
                    "ascii"
                ),
                value=json.dumps(
                    output,
                    allow_nan=False,
                ).encode("utf-8"),
                on_delivery=lambda
                    error, msg:
                    delivery.append(
                        error
                    ),
            )

            remaining = producer.flush(
                35
            )

            if (
                remaining
                or len(delivery) != 1
                or delivery[0]
                is not None
            ):
                raise RuntimeError(
                    "Inference output "
                    "delivery not confirmed"
                )

            # Commit input only after output ACK.
            consumer.commit(
                offsets=[
                    TopicPartition(
                        INPUT,
                        message.partition(),
                        message.offset() + 1,
                    )
                ],
                asynchronous=False,
            )

            processed += 1

            print(
                json.dumps({
                    "kind":
                        "live_morpheus_inference",

                    "event_uid":
                        uid,

                    "status":
                        "PASS",

                    "score":
                        score,

                    "label":
                        output[
                            "predicted_label"
                        ],

                    "processed":
                        processed,

                    "production_ready":
                        False,

                    "automated_response_allowed":
                        False,
                }),
                flush=True,
            )

    finally:
        consumer.close()

    if processed == 0:
        raise RuntimeError(
            "No new live inference event "
            "received within bounded window"
        )


if __name__ == "__main__":
    main()
