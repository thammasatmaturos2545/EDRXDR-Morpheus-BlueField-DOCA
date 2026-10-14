"""Fail-closed live Morpheus severity result indexer.

Consumes morpheus-output and commits Kafka only after OpenSearch ACK.
No automated response is performed.
"""

import hashlib
import json
import math
import re
from datetime import datetime
import time

KAFKA_BROKER = "kafka:29092"
INPUT_TOPIC = "morpheus-output"
GROUP_ID = "edrxdr-indexer"

OPENSEARCH_URL = "http://opensearch:9200"

EXPECTED_SCHEMA = "live-severity-1"
EXPECTED_ENGINE = "nvidia-morpheus-context-severity-v1"
EXPECTED_MODEL = (
    "wazuh-severity-context-v2-balanced-"
    "20261008T190719Z-1398863"
)
EXPECTED_TEXT_CONTRACT = "wazuh-context-v2-raw-1"

HEX64 = re.compile(r"^[0-9a-f]{64}$")

ARTIFACT_FIELDS = (
    "checkpoint_weights_sha256",
    "adapter_sha256",
    "preprocessing_adapter_sha256",
    "raw_adapter_sha256",
    "text_builder_sha256",
)

FORBIDDEN_FIELDS = (
    "raw_event",
    "full_log",
    "text_input",
)


def strict_json(value):
    def reject(_):
        raise ValueError(
            "Non-finite JSON forbidden"
        )

    if isinstance(value, bytes):
        value = value.decode("utf-8")

    return json.loads(
        value,
        parse_constant=reject,
    )


def uint(value, name):
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
    ):
        raise ValueError(
            f"Invalid {name}"
        )

    return value


def hex64(value, name):
    if (
        not isinstance(value, str)
        or HEX64.fullmatch(value) is None
    ):
        raise ValueError(
            f"Invalid {name}"
        )

    return value


def timestamp(value):
    if (
        not isinstance(value, str)
        or not value.strip()
    ):
        raise ValueError(
            "Invalid scored_at_utc"
        )

    parsed = datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )

    if parsed.tzinfo is None:
        raise ValueError(
            "scored_at_utc requires timezone"
        )

    return parsed


def validate(event, key):
    if not isinstance(event, dict):
        raise ValueError(
            "Expected event object"
        )

    if event.get("schema_version") != EXPECTED_SCHEMA:
        raise ValueError(
            "Unexpected schema"
        )

    if event.get("source_type") != "wazuh":
        raise ValueError(
            "Expected Wazuh source"
        )

    if event.get("processing_mode") != "live":
        raise ValueError(
            "Expected live processing mode"
        )

    if event.get("analysis_engine") != EXPECTED_ENGINE:
        raise ValueError(
            "Unexpected analysis engine"
        )

    if event.get("model_name") != EXPECTED_MODEL:
        raise ValueError(
            "Unexpected model"
        )

    if (
        event.get("text_contract_version")
        != EXPECTED_TEXT_CONTRACT
    ):
        raise ValueError(
            "Unexpected text contract"
        )

    if event.get("production_ready") is not False:
        raise ValueError(
            "production_ready must remain false"
        )

    if (
        event.get(
            "automated_response_allowed"
        )
        is not False
    ):
        raise ValueError(
            "Automated response must remain disabled"
        )

    if any(
        field in event
        for field in FORBIDDEN_FIELDS
    ):
        raise ValueError(
            "Raw/private payload forbidden"
        )

    uid = hex64(
        event.get("event_uid"),
        "event_uid",
    )

    if key != uid.encode("ascii"):
        raise ValueError(
            "Kafka key/event_uid mismatch"
        )

    score = event.get(
        "high_severity_score"
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
            "Invalid high_severity_score"
        )

    threshold = event.get("threshold")

    if (
        isinstance(threshold, bool)
        or not isinstance(
            threshold,
            (int, float),
        )
        or float(threshold) != 0.5
    ):
        raise ValueError(
            "Unexpected threshold"
        )

    expected_label = (
        "high_severity"
        if float(score) >= 0.5
        else "low_severity"
    )

    if (
        event.get("predicted_label")
        != expected_label
    ):
        raise ValueError(
            "Prediction/score mismatch"
        )

    if event.get("source_topic") != "wazuh-alerts":
        raise ValueError(
            "Unexpected original source topic"
        )

    uint(
        event.get("source_partition"),
        "source_partition",
    )

    uint(
        event.get("source_offset"),
        "source_offset",
    )

    if event.get("input_topic") != "morpheus-input":
        raise ValueError(
            "Unexpected inference input topic"
        )

    uint(
        event.get("input_partition"),
        "input_partition",
    )

    uint(
        event.get("input_offset"),
        "input_offset",
    )

    timestamp(
        event.get("scored_at_utc")
    )

    artifacts = event.get(
        "artifact_hashes"
    )

    if not isinstance(
        artifacts,
        dict,
    ):
        raise ValueError(
            "Missing artifact hashes"
        )

    if set(artifacts) != set(
        ARTIFACT_FIELDS
    ):
        raise ValueError(
            "Unexpected artifact hash set"
        )

    for field in ARTIFACT_FIELDS:
        hex64(
            artifacts.get(field),
            field,
        )

    hex64(
        event.get(
            "vocab_hash_sha256"
        ),
        "vocab_hash_sha256",
    )

    hex64(
        event.get(
            "engine_sha256"
        ),
        "engine_sha256",
    )

    hex64(
        event.get(
            "worker_sha256"
        ),
        "worker_sha256",
    )

    return event


def document_id(event):
    weights = event[
        "artifact_hashes"
    ][
        "checkpoint_weights_sha256"
    ]

    identity = [
        event["event_uid"],
        weights,
        event["text_contract_version"],
        event["schema_version"],
        event["analysis_engine"],
    ]

    return hashlib.sha256(
        json.dumps(
            identity,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def index_name(event):
    value = timestamp(
        event["scored_at_utc"]
    )

    value = value.astimezone(
        __import__(
            "datetime"
        ).timezone.utc
    )

    return (
        "edrxdr-events-"
        + value.strftime("%Y.%m.%d")
    )


def project(event):
    fields = (
        "schema_version",
        "event_uid",
        "source_type",
        "processing_mode",
        "analysis_engine",
        "model_name",
        "text_contract_version",
        "high_severity_score",
        "predicted_label",
        "threshold",
        "wazuh_rule_id",
        "wazuh_rule_level",
        "source_topic",
        "source_partition",
        "source_offset",
        "input_topic",
        "input_partition",
        "input_offset",
        "scored_at_utc",
        "artifact_hashes",
        "vocab_hash_sha256",
        "engine_sha256",
        "worker_sha256",
        "production_ready",
        "automated_response_allowed",
    )

    return {
        field: event.get(field)
        for field in fields
    }


def wait_for_opensearch():
    import requests

    deadline = time.monotonic() + 60

    while time.monotonic() < deadline:
        try:
            response = requests.get(
                OPENSEARCH_URL,
                timeout=5,
            )

            if response.status_code == 200:
                return

        except requests.RequestException:
            pass

        time.sleep(2)

    raise RuntimeError(
        "OpenSearch unavailable"
    )


def write_document(event):
    import requests

    ident = document_id(event)
    index = index_name(event)
    document = project(event)

    response = requests.put(
        (
            f"{OPENSEARCH_URL}/"
            f"{index}/_doc/{ident}"
            "?refresh=wait_for"
        ),
        json=document,
        timeout=20,
    )

    if response.status_code not in (
        200,
        201,
    ):
        raise RuntimeError(
            "OpenSearch write failed: "
            + str(response.status_code)
        )

    result = response.json()

    shards = result.get("_shards")

    if (
        result.get("_id") != ident
        or result.get("_index") != index
        or not isinstance(
            shards,
            dict,
        )
        or shards.get("failed") != 0
        or not isinstance(
            shards.get("successful"),
            int,
        )
        or shards["successful"] < 1
    ):
        raise RuntimeError(
            "OpenSearch acknowledgement incomplete"
        )

    return index, ident


def main():
    from kafka import KafkaConsumer, TopicPartition
    from kafka.structs import OffsetAndMetadata

    print(
        "======================================"
    )
    print(
        " EDRXDR Fail-Closed Live Indexer"
    )
    print(
        "======================================"
    )
    print(
        "Kafka topic :",
        INPUT_TOPIC,
    )
    print(
        "OpenSearch  :",
        OPENSEARCH_URL,
    )

    wait_for_opensearch()

    consumer = KafkaConsumer(
        INPUT_TOPIC,
        bootstrap_servers=[
            KAFKA_BROKER
        ],
        group_id=GROUP_ID,
        enable_auto_commit=False,
        auto_offset_reset="latest",
        max_poll_records=1,
    )

    try:
        for message in consumer:
            event = strict_json(
                message.value
            )

            validate(
                event,
                message.key,
            )

            index, ident = (
                write_document(event)
            )

            partition = TopicPartition(
                message.topic,
                message.partition,
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
                json.dumps({
                    "kind":
                        "live_indexer",

                    "status":
                        "PASS",

                    "event_uid":
                        event[
                            "event_uid"
                        ],

                    "index":
                        index,

                    "document_id":
                        ident,

                    "kafka_offset_committed":
                        message.offset + 1,

                    "production_ready":
                        False,

                    "automated_response_allowed":
                        False,
                }),
                flush=True,
            )

    finally:
        consumer.close()


if __name__ == "__main__":
    main()
