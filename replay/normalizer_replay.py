"""Replay-only Wazuh normalizer. Never connects to production topics."""
import ast
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from kafka import KafkaConsumer, KafkaProducer
from kafka.structs import TopicPartition, OffsetAndMetadata

BROKER = "kafka:29092"
INPUT = "replay-wazuh-alerts"
OUTPUT = "replay-morpheus-input"
GROUP = "replay-normalizer-v1"


def load_normalizer():
    # Load only reviewed functions; do not execute original startup code.
    path = Path("/source/normalizer/normalizer.py")
    tree = ast.parse(path.read_text())
    names = {"utc_now", "safe_int", "normalize_wazuh"}
    functions = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in names
    ]
    if {node.name for node in functions} != names or len(functions) != 3:
        raise RuntimeError("Unexpected normalizer structure")
    module = ast.Module(body=functions, type_ignores=[])
    namespace = {"datetime": datetime, "timezone": timezone}
    exec(compile(module, str(path), "exec"), namespace)
    return namespace["normalize_wazuh"]


def main():
    normalize = load_normalizer()
    producer = KafkaProducer(
        bootstrap_servers=[BROKER],
        acks="all",
        retries=5,
        max_in_flight_requests_per_connection=1,
        value_serializer=lambda value: json.dumps(
            value, ensure_ascii=False, allow_nan=False
        ).encode("utf-8"),
    )
    consumer = KafkaConsumer(
        INPUT,
        bootstrap_servers=[BROKER],
        group_id=GROUP,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        max_poll_records=1,
    )
    try:
        for message in consumer:
            try:
                event = json.loads(message.value.decode("utf-8"))
                identity = [
                    event["manager"]["name"],
                    event["agent"]["id"],
                    event["id"],
                ]
                if any(
                    not isinstance(value, (str, int))
                    or isinstance(value, bool)
                    or not str(value).strip()
                    for value in identity
                ):
                    raise ValueError("Invalid event identity")
                identity = [str(value) for value in identity]
                event_uid = hashlib.sha256(
                    json.dumps(identity).encode()
                ).hexdigest()

                normalized = normalize(event)
                normalized["event_uid"] = event_uid
                normalized["pipeline_source"] = INPUT
                normalized["processing_mode"] = "replay"

                producer.send(
                    OUTPUT,
                    key=event_uid.encode(),
                    value=normalized,
                ).get(timeout=30)

                partition = TopicPartition(message.topic, message.partition)
                consumer.commit({
                    partition: OffsetAndMetadata(message.offset + 1, "", -1)
                })
                print(
                    f"ACK partition={message.partition} offset={message.offset}",
                    flush=True,
                )
            except Exception as error:
                print(
                    f"STOP partition={message.partition} "
                    f"offset={message.offset} "
                    f"error_type={type(error).__name__}",
                    flush=True,
                )
                raise SystemExit(1)
    finally:
        consumer.close()
        producer.close(timeout=10)


if __name__ == "__main__":
    main()
