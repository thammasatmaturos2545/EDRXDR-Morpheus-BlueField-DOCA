"""One-event replay worker; experimental severity scoring only."""
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from confluent_kafka import Consumer, Producer, TopicPartition
from raw_event_contract import event_text
from morpheus_replay_engine import score_texts

CHECKPOINT = Path(
    "/models/wazuh-severity-context-v2-balanced-20261008T190719Z-1398863"
)
REPORT = Path(
    "/models/morpheus-raw-offline-check-20261008T203523Z-1803526/parity_report.json"
)
INPUT = "replay-morpheus-input"
OUTPUT = "replay-morpheus-output"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    evidence = json.loads(REPORT.read_text())
    if evidence["status"] != "PASS" or evidence["issues"]:
        raise ValueError("Expected successful parity evidence")

    files = {
        "checkpoint_weights_sha256": CHECKPOINT / "model.safetensors",
        "adapter_sha256": Path("/scripts/morpheus_context_inference.py"),
        "preprocessing_adapter_sha256": Path("/scripts/morpheus_bert_special_tokens.py"),
        "raw_adapter_sha256": Path("/scripts/raw_event_contract.py"),
        "text_builder_sha256": Path("/scripts/build_context_dataset.py"),
    }
    hashes = {}
    for field, path in files.items():
        hashes[field] = digest(path)
        if hashes[field] != evidence[field]:
            raise ValueError("Artifact hash mismatch: " + field)

    vocab = Path("/opt/conda/envs/morpheus/lib/python3.12/site-packages/morpheus/data/bert-base-uncased-hash.txt")
    if not vocab.is_file():
        raise ValueError("Missing vocabulary hash file")

    consumer = Consumer({
        "bootstrap.servers": "kafka:29092",
        "group.id": "replay-inference-v1",
        "enable.auto.commit": False,
        "enable.auto.offset.store": False,
        "auto.offset.reset": "earliest",
    })
    producer = Producer({
        "bootstrap.servers": "kafka:29092",
        "enable.idempotence": True,
        "acks": "all",
        "delivery.timeout.ms": 30000,
    })

    try:
        # Replay topic has exactly one partition. Manual assignment avoids
        # a group rebalance while this finite GPU job runs.
        partition = TopicPartition(INPUT, 0)
        committed = consumer.committed([partition], timeout=15)[0]
        if committed.error:
            raise RuntimeError("Could not read committed offset")
        consumer.assign([committed])

        message = None
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            message = consumer.poll(1)
            if message is not None:
                if message.error():
                    raise RuntimeError("Kafka input error")
                break
        if message is None:
            raise RuntimeError("No replay event received")

        event = json.loads(message.value())
        if (event.get("source_type") != "wazuh"
                or event.get("processing_mode") != "replay"):
            raise ValueError("Expected replay Wazuh event")

        raw = event["raw_event"]
        identity = [raw["manager"]["name"], raw["agent"]["id"], raw["id"]]
        if any(
            not isinstance(value, (str, int)) or isinstance(value, bool)
            or not str(value).strip() for value in identity
        ):
            raise ValueError("Invalid event identity")
        uid = hashlib.sha256(
            json.dumps([str(value) for value in identity]).encode()
        ).hexdigest()
        if event["event_uid"] != uid or message.key() != uid.encode():
            raise ValueError("Event identity mismatch")

        text = event_text(raw)
        print("Artifacts and input: PASS; starting inference", flush=True)
        score = score_texts([text], CHECKPOINT, vocab)[0]

        output = {
            "schema_version": "replay-severity-1",
            "event_uid": uid,
            "source_type": "wazuh",
            "processing_mode": "replay",
            "model_name": CHECKPOINT.name,
            "text_contract_version": "wazuh-context-v2-raw-1",
            "high_severity_score": score,
            "predicted_label": "high_severity" if score >= 0.5 else "low_severity",
            "threshold": 0.5,
            "wazuh_rule_id": raw["rule"].get("id"),
            "wazuh_rule_level": raw["rule"].get("level"),
            "scored_at_utc": datetime.now(timezone.utc).isoformat(),
            "artifact_hashes": hashes,
            "vocab_hash_sha256": digest(vocab),
            "engine_sha256": digest("/replay/morpheus_replay_engine.py"),
            "worker_sha256": digest(__file__),
            "input_partition": message.partition(),
            "input_offset": message.offset(),
            "production_ready": False,
        }

        delivery = []
        producer.produce(
            OUTPUT,
            key=uid.encode(),
            value=json.dumps(output, allow_nan=False).encode(),
            on_delivery=lambda error, msg: delivery.append(error),
        )
        remaining = producer.flush(35)
        if remaining or len(delivery) != 1 or delivery[0] is not None:
            raise RuntimeError("Output delivery not confirmed")

        consumer.commit(
            offsets=[TopicPartition(INPUT, message.partition(), message.offset() + 1)],
            asynchronous=False,
        )
        print("Inference output delivered; input offset committed", flush=True)
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
