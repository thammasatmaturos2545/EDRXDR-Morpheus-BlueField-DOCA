"""Index display-only behavioral replay result into isolated OpenSearch index."""

import hashlib
import json
import math
import re
import time
from urllib.request import Request, urlopen

from kafka import KafkaConsumer, TopicPartition
from kafka.structs import OffsetAndMetadata


TOPIC = "replay-behavioral-output"
INDEX = "replay-behavioral-v1"
URL = "http://opensearch:9200"


HASH_RE = re.compile(
    r"[0-9a-f]{64}"
)


def valid_number(value):
    return (
        not isinstance(value, bool)
        and isinstance(
            value,
            (int, float),
        )
        and math.isfinite(value)
    )


def validate(event, key):
    if (
        event.get("schema_version")
        != "replay-behavioral-1"
    ):
        raise ValueError(
            "Unexpected schema"
        )

    if (
        event.get("processing_mode")
        != "replay"
    ):
        raise ValueError(
            "Expected replay mode"
        )

    if (
        event.get("source_type")
        != "wazuh"
    ):
        raise ValueError(
            "Expected Wazuh source"
        )

    if (
        event.get("model_version")
        != "behavioral-v1.4"
    ):
        raise ValueError(
            "Unexpected model version"
        )

    if (
        event.get("production_ready")
        is not False
    ):
        raise ValueError(
            "Expected development output"
        )

    if (
        event.get(
            "automated_response_allowed"
        )
        is not False
    ):
        raise ValueError(
            "Automated response must be disabled"
        )

    forbidden = {
        "raw_event",
        "full_log",
        "text_input",
        "command",
    }

    if any(
        field in event
        for field in forbidden
    ):
        raise ValueError(
            "Raw or command text forbidden in behavioral index"
        )

    uid = event["event_uid"]

    if (
        not isinstance(uid, str)
        or not HASH_RE.fullmatch(uid)
    ):
        raise ValueError(
            "Invalid event UID"
        )

    if key != uid.encode():
        raise ValueError(
            "Kafka key mismatch"
        )

    manifest_hash = event[
        "runtime_manifest_sha256"
    ]

    if (
        not isinstance(
            manifest_hash,
            str,
        )
        or not HASH_RE.fullmatch(
            manifest_hash
        )
    ):
        raise ValueError(
            "Invalid runtime manifest hash"
        )

    model_hash = event.get(
        "model_sha256"
    )

    if (
        model_hash is not None
        and (
            not isinstance(
                model_hash,
                str,
            )
            or not HASH_RE.fullmatch(
                model_hash
            )
        )
    ):
        raise ValueError(
            "Invalid model hash"
        )

    routing = event[
        "routing_status"
    ]

    if routing not in {
        "local_model",
        "fallback_supported",
        "limited_history",
        "novel_cohort",
    }:
        raise ValueError(
            "Invalid routing status"
        )

    state = event[
        "analysis_state"
    ]

    allowed_states = {
        "baseline_consistent",
        "behavioral_anomaly",
        "behavioral_anomaly+semantic_novelty",
        "semantic_novelty",
        "fallback_supported",
        "limited_history",
        "novel_cohort",
        "insufficient_feature_diversity",
        "no_temporal_dev_evidence",
    }

    if state not in allowed_states:
        raise ValueError(
            "Invalid analysis state"
        )

    if not isinstance(
        event["semantic_novelty"],
        bool,
    ):
        raise ValueError(
            "Invalid semantic novelty flag"
        )

    command_class = event[
        "command_class"
    ]

    if (
        not isinstance(
            command_class,
            str,
        )
        or not command_class.strip()
        or len(command_class) > 128
    ):
        raise ValueError(
            "Invalid command class"
        )

    for field in (
        "train_cohort_support",
        "command_class_train_support",
        "package_argument_count",
    ):
        value = event[field]

        if (
            isinstance(value, bool)
            or not isinstance(
                value,
                int,
            )
            or value < 0
        ):
            raise ValueError(
                f"Invalid {field}"
            )

    error = event.get(
        "ae_reconstruction_error"
    )

    threshold = event.get(
        "ae_threshold"
    )

    ratio = event.get(
        "ae_ratio"
    )

    anomaly = event.get(
        "ae_anomaly"
    )

    if error is None:
        if any(
            value is not None
            for value in (
                threshold,
                ratio,
                anomaly,
            )
        ):
            raise ValueError(
                "Partial AE result"
            )

    else:
        if not (
            valid_number(error)
            and valid_number(threshold)
            and valid_number(ratio)
        ):
            raise ValueError(
                "Invalid AE values"
            )

        if (
            error < 0
            or threshold <= 0
            or ratio < 0
        ):
            raise ValueError(
                "Invalid AE range"
            )

        if not isinstance(
            anomaly,
            bool,
        ):
            raise ValueError(
                "Invalid AE anomaly flag"
            )

        expected = (
            error > threshold
        )

        if anomaly != expected:
            raise ValueError(
                "AE decision mismatch"
            )

        expected_ratio = (
            error / threshold
        )

        if not math.isclose(
            ratio,
            expected_ratio,
            rel_tol=1e-6,
            abs_tol=1e-9,
        ):
            raise ValueError(
                "AE ratio mismatch"
            )

    identity = [
        uid,
        manifest_hash,
        event["model_version"],
        event["schema_version"],
    ]

    return hashlib.sha256(
        json.dumps(
            identity
        ).encode()
    ).hexdigest()


def main():
    consumer = KafkaConsumer(
        bootstrap_servers=[
            "kafka:29092"
        ],

        group_id=
            "replay-behavioral-indexer-v1",

        enable_auto_commit=False,

        auto_offset_reset=
            "earliest",

        max_poll_records=1,
    )

    try:
        partition = TopicPartition(
            TOPIC,
            0,
        )

        consumer.assign(
            [partition]
        )

        offset = consumer.committed(
            partition
        )

        if offset is None:
            consumer.seek_to_beginning(
                partition
            )

        else:
            consumer.seek(
                partition,
                offset,
            )

        message = None

        deadline = (
            time.monotonic()
            + 30
        )

        while (
            time.monotonic()
            < deadline
            and message is None
        ):
            batches = consumer.poll(
                timeout_ms=1000,
                max_records=1,
            )

            for records in (
                batches.values()
            ):
                if records:
                    message = records[0]
                    break

        if message is None:
            raise RuntimeError(
                "No behavioral replay result received"
            )

        event = json.loads(
            message.value
        )

        document_id = validate(
            event,
            message.key,
        )

        fields = (
            "schema_version",
            "event_uid",
            "source_type",
            "processing_mode",
            "model_version",
            "analysis_state",
            "routing_status",
            "train_cohort_support",
            "ae_reconstruction_error",
            "ae_threshold",
            "ae_ratio",
            "ae_anomaly",
            "semantic_novelty",
            "command_class",
            "command_class_train_support",
            "package_argument_count",
            "wazuh_rule_id",
            "wazuh_rule_level",
            "scored_at_utc",
            "runtime_manifest_sha256",
            "model_sha256",
            "input_partition",
            "input_offset",
            "production_ready",
            "automated_response_allowed",
        )

        document = {
            field: event[field]
            for field in fields
        }

        request = Request(
            (
                f"{URL}/{INDEX}"
                f"/_doc/{document_id}"
                "?refresh=wait_for"
            ),
            data=json.dumps(
                document,
                allow_nan=False,
            ).encode(),
            headers={
                "Content-Type":
                    "application/json"
            },
            method="PUT",
        )

        with urlopen(
            request,
            timeout=30,
        ) as response:
            status = response.status
            result = json.load(
                response
            )

        if (
            status not in (200, 201)
            or result.get("_id")
            != document_id
        ):
            raise RuntimeError(
                "Index acknowledgement mismatch"
            )

        if (
            result.get(
                "_shards",
                {},
            ).get(
                "failed",
                0,
            )
        ):
            raise RuntimeError(
                "Index shard failure"
            )

        consumer.commit({
            partition:
                OffsetAndMetadata(
                    message.offset + 1,
                    "",
                    -1,
                )
        })

        print(
            "Behavioral OpenSearch write: PASS",
            flush=True,
        )

        print(
            "Index:",
            INDEX,
            flush=True,
        )

        print(
            "Document ID:",
            document_id,
            flush=True,
        )

        print(
            "analysis_state:",
            event["analysis_state"],
            flush=True,
        )

    finally:
        consumer.close()


if __name__ == "__main__":
    main()
