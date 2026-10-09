"""Index one replay score; commit Kafka only after OpenSearch acknowledges."""
import hashlib
import json
import math
import re
import time
from urllib.request import Request, urlopen

from kafka import KafkaConsumer, TopicPartition
from kafka.structs import OffsetAndMetadata

TOPIC = "replay-morpheus-output"
INDEX = "replay-severity-v1"
URL = "http://opensearch:9200"


def validate(event, key):
    if event.get("schema_version") != "replay-severity-1":
        raise ValueError("Unexpected schema")
    if event.get("processing_mode") != "replay":
        raise ValueError("Expected replay mode")
    if event.get("source_type") != "wazuh":
        raise ValueError("Expected Wazuh source")
    if event.get("production_ready") is not False:
        raise ValueError("Expected experimental output")
    if any(field in event for field in ("raw_event", "full_log", "text_input")):
        raise ValueError("Raw text forbidden in score index")

    uid = event["event_uid"]
    if not isinstance(uid, str) or not re.fullmatch(r"[0-9a-f]{64}", uid):
        raise ValueError("Invalid event UID")
    if key != uid.encode():
        raise ValueError("Kafka key mismatch")

    score = event["high_severity_score"]
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        raise ValueError("Invalid score type")
    if not math.isfinite(score) or not 0 <= score <= 1:
        raise ValueError("Invalid score")
    if event["threshold"] != 0.5:
        raise ValueError("Unexpected threshold")
    expected = "high_severity" if score >= 0.5 else "low_severity"
    if event["predicted_label"] != expected:
        raise ValueError("Decision mismatch")

    weights = event["artifact_hashes"]["checkpoint_weights_sha256"]
    if not isinstance(weights, str) or not re.fullmatch(r"[0-9a-f]{64}", weights):
        raise ValueError("Invalid model hash")

    identity = [
        uid, weights, event["text_contract_version"], event["schema_version"]
    ]
    return hashlib.sha256(json.dumps(identity).encode()).hexdigest()


def main():
    consumer = KafkaConsumer(
        bootstrap_servers=["kafka:29092"],
        group_id="replay-indexer-v1",
        enable_auto_commit=False,
        auto_offset_reset="earliest",
        max_poll_records=1,
    )
    try:
        partition = TopicPartition(TOPIC, 0)
        consumer.assign([partition])
        offset = consumer.committed(partition)
        if offset is None:
            consumer.seek_to_beginning(partition)
        else:
            consumer.seek(partition, offset)

        message = None
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and message is None:
            batches = consumer.poll(timeout_ms=1000, max_records=1)
            for records in batches.values():
                if records:
                    message = records[0]
                    break
        if message is None:
            raise RuntimeError("No replay score received")

        event = json.loads(message.value)
        document_id = validate(event, message.key)
        fields = (
            "schema_version", "event_uid", "source_type", "processing_mode",
            "model_name", "text_contract_version", "high_severity_score",
            "predicted_label", "threshold", "wazuh_rule_id",
            "wazuh_rule_level", "scored_at_utc", "artifact_hashes",
            "vocab_hash_sha256", "engine_sha256", "worker_sha256",
            "input_partition", "input_offset", "production_ready",
        )
        document = {field: event[field] for field in fields}
        request = Request(
            f"{URL}/{INDEX}/_doc/{document_id}?refresh=wait_for",
            data=json.dumps(document, allow_nan=False).encode(),
            headers={"Content-Type": "application/json"},
            method="PUT",
        )
        with urlopen(request, timeout=30) as response:
            status = response.status
            result = json.load(response)
        if status not in (200, 201) or result.get("_id") != document_id:
            raise RuntimeError("Index acknowledgement mismatch")
        if result.get("_shards", {}).get("failed", 0):
            raise RuntimeError("Index shard failure")

        consumer.commit({
            partition: OffsetAndMetadata(message.offset + 1, "", -1)
        })
        print("OpenSearch write: PASS", flush=True)
        print("Index:", INDEX, flush=True)
        print("Document ID:", document_id, flush=True)
        print("Kafka offset committed:", message.offset + 1, flush=True)
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
