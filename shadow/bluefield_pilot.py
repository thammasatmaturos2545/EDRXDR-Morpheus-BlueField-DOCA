"""Manual bounded BlueField shadow transport/index pilot on replay infrastructure only."""
from __future__ import annotations

import argparse
import json
import os
import time
import traceback
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from bluefield_common import (
    EXPECTED_CLUSTER_ID,
    FORBIDDEN_LIVE_TOPICS,
    INDEX,
    INDEX_GROUP,
    INPUT_TOPIC,
    REPLAY_TOPICS,
    REVIEW_NORMALIZED_SHA256,
    TARGET,
    document_id,
    encode,
    index_mapping,
    sha256_bytes,
    strict_json,
    to_shadow,
    utc_now,
    validate_review,
    validate_shadow,
)

OS_URL = "http://opensearch:9200"
SOURCE_FILE = Path("/bluefield-evidence/normalized.jsonl")
SOURCE_REPORT = Path("/bluefield-evidence/report.json")
EXPECTED_RECORDS = 6


def report(kind, **data):
    print(
        json.dumps(
            {"kind": kind, "time_utc": utc_now(), **data},
            allow_nan=False,
        ),
        flush=True,
    )


def require_enabled():
    if os.environ.get("BLUEFIELD_SHADOW_RUN_ALLOWED") != "1":
        raise RuntimeError(
            "BlueField shadow mutation disabled; set "
            "BLUEFIELD_SHADOW_RUN_ALLOWED=1 explicitly"
        )


def request(path, body=None, method="GET"):
    allowed = (
        path in ("/_cluster/health", "/_cat/indices?format=json&h=index")
        or path == "/" + INDEX
        or path == "/" + INDEX + "/_mapping"
        or path.startswith("/" + INDEX + "/_doc/")
        or path.startswith("/" + INDEX + "/_search")
    )
    if not allowed:
        raise RuntimeError("OpenSearch endpoint outside BlueField shadow allowlist")
    req = Request(
        OS_URL + path,
        data=None if body is None else encode(body),
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urlopen(req, timeout=15) as response:
        return response.status, json.load(response)


def broker_metadata(require_input=False):
    from confluent_kafka.admin import AdminClient

    meta = AdminClient(
        {
            "bootstrap.servers": TARGET,
            "socket.timeout.ms": 10000,
        }
    ).list_topics(timeout=10)
    if meta.cluster_id != EXPECTED_CLUSTER_ID:
        raise RuntimeError("Unexpected replay Kafka cluster ID")
    endpoints = {(b.host, b.port) for b in meta.brokers.values()}
    if endpoints != {("kafka", 29092)}:
        raise RuntimeError("Unexpected replay Kafka listener")
    if not REPLAY_TOPICS.issubset(meta.topics):
        raise RuntimeError("Replay topic signature incomplete")
    if FORBIDDEN_LIVE_TOPICS.intersection(meta.topics):
        raise RuntimeError("Live/shared topic found on replay broker")
    if require_input:
        topic = meta.topics.get(INPUT_TOPIC)
        if topic is None or topic.error or len(topic.partitions) != 1:
            raise RuntimeError("BlueField shadow input topic unavailable")
    return meta


def source_rows():
    if not SOURCE_FILE.is_file() or not SOURCE_REPORT.is_file():
        raise RuntimeError("Pinned BlueField replay evidence missing")
    if sha256_bytes(SOURCE_FILE.read_bytes()) != REVIEW_NORMALIZED_SHA256:
        raise RuntimeError("Archived normalized evidence hash changed")
    evidence = strict_json(SOURCE_REPORT.read_bytes())
    if (
        evidence.get("status") != "PASS"
        or evidence.get("records") != EXPECTED_RECORDS
        or evidence.get("normalized_equals_archived") is not True
        or evidence.get("record_bytes_equal") is not True
    ):
        raise RuntimeError("Kafka PASS evidence contract not satisfied")
    values = [
        line
        for line in SOURCE_FILE.read_bytes().splitlines()
        if line.strip()
    ]
    if len(values) != EXPECTED_RECORDS:
        raise RuntimeError("Expected exactly six archived normalized records")
    rows = [validate_review(strict_json(value)) for value in values]
    if sum(row["carrier"] is None for row in rows) != 6:
        raise RuntimeError("Expected six null carrier values")
    if sum(row["delta_rx_bytes"] is None for row in rows) != 2:
        raise RuntimeError("Expected two first-sample null deltas")
    if sum(row["delta_rx_bytes"] == 0 for row in rows) != 4:
        raise RuntimeError("Expected four computed zero deltas")
    return values, rows


def topic_bounds():
    from confluent_kafka import Consumer, TopicPartition

    client = Consumer(
        {
            "bootstrap.servers": TARGET,
            "group.id": "edrxdr-shadow-bluefield-inspect-v1",
            "enable.auto.commit": False,
            "allow.auto.create.topics": False,
            "auto.offset.reset": "error",
        }
    )
    try:
        low, high = client.get_watermark_offsets(
            TopicPartition(INPUT_TOPIC, 0),
            timeout=10,
            cached=False,
        )
        return low, high
    finally:
        client.close()


def read_topic_exact():
    from confluent_kafka import Consumer, TopicPartition

    client = Consumer(
        {
            "bootstrap.servers": TARGET,
            "group.id": "edrxdr-shadow-bluefield-verify-input-v1",
            "enable.auto.commit": False,
            "allow.auto.create.topics": False,
            "auto.offset.reset": "error",
        }
    )
    rows = []
    try:
        client.assign([TopicPartition(INPUT_TOPIC, 0, 0)])
        deadline = time.monotonic() + 15
        while len(rows) < EXPECTED_RECORDS and time.monotonic() < deadline:
            message = client.poll(1)
            if message is None:
                continue
            if message.error():
                raise RuntimeError("Kafka verification poll failed")
            rows.append(message.value())
        if len(rows) != EXPECTED_RECORDS:
            raise RuntimeError("Could not read exactly six BlueField input records")
        return rows
    finally:
        client.close()


def preflight():
    values, _ = source_rows()
    meta = broker_metadata()
    _, health = request("/_cluster/health")
    if health.get("status") == "red" or health.get("timed_out"):
        raise RuntimeError("Replay OpenSearch unavailable")
    report(
        "bluefield_shadow_preflight",
        status="PASS",
        records=len(values),
        source_sha256=REVIEW_NORMALIZED_SHA256,
        target_cluster_id=meta.cluster_id,
        target_endpoint=TARGET,
        opensearch_status=health.get("status"),
        live_source_used=False,
        gpu_used=False,
        automated_response_allowed=False,
    )


def provision():
    require_enabled()
    meta = broker_metadata()
    from confluent_kafka.admin import AdminClient, NewTopic
    from confluent_kafka import KafkaError, KafkaException

    if INPUT_TOPIC not in meta.topics:
        admin = AdminClient({"bootstrap.servers": TARGET})
        future = admin.create_topics(
            [
                NewTopic(
                    INPUT_TOPIC,
                    num_partitions=1,
                    replication_factor=1,
                    config={
                        "retention.ms": "86400000",
                        "retention.bytes": "67108864",
                        "cleanup.policy": "delete",
                    },
                )
            ],
            request_timeout=15,
        )[INPUT_TOPIC]
        try:
            future.result()
        except KafkaException as error:
            if error.args[0].code() != KafkaError.TOPIC_ALREADY_EXISTS:
                raise

    broker_metadata(require_input=True)

    try:
        request("/" + INDEX)
        _, current = request("/" + INDEX + "/_mapping")
        mapping = current.get(INDEX, {}).get("mappings", {})
        if mapping.get("dynamic") != "strict":
            raise RuntimeError("Existing BlueField shadow index is not strict")
    except HTTPError as error:
        if error.code != 404:
            raise
        status, reply = request("/" + INDEX, index_mapping(), "PUT")
        if (
            status not in (200, 201)
            or reply.get("acknowledged") is not True
            or reply.get("shards_acknowledged") is not True
        ):
            raise RuntimeError("BlueField shadow index creation not acknowledged")

    report(
        "bluefield_shadow_provision",
        status="PASS",
        topic=INPUT_TOPIC,
        index=INDEX,
    )


def publish():
    require_enabled()
    broker_metadata(require_input=True)
    values, _ = source_rows()
    low, high = topic_bounds()

    if low != 0:
        raise RuntimeError("BlueField shadow topic retention gap detected")
    if high == EXPECTED_RECORDS:
        existing = read_topic_exact()
        if existing != values:
            raise RuntimeError("Existing BlueField topic bytes differ from pinned evidence")
        report(
            "bluefield_shadow_publish",
            status="PASS",
            records=EXPECTED_RECORDS,
            already_present=True,
        )
        return
    if high != 0:
        raise RuntimeError(
            "BlueField shadow topic is neither empty nor the exact six-record pilot"
        )

    from confluent_kafka import Producer

    producer = Producer(
        {
            "bootstrap.servers": TARGET,
            "enable.idempotence": True,
            "acks": "all",
            "delivery.timeout.ms": 30000,
        }
    )
    failures = []

    def delivered(error, _):
        if error is not None:
            failures.append(str(type(error).__name__))

    for value in values:
        producer.produce(
            INPUT_TOPIC,
            partition=0,
            key=sha256_bytes(value).encode("ascii"),
            value=value,
            on_delivery=delivered,
        )
    remaining = producer.flush(35)
    if remaining or failures:
        raise RuntimeError("BlueField shadow publish acknowledgement failed")

    low, high = topic_bounds()
    if (low, high) != (0, EXPECTED_RECORDS):
        raise RuntimeError("Unexpected BlueField shadow topic bounds after publish")
    if read_topic_exact() != values:
        raise RuntimeError("BlueField shadow topic byte verification failed")

    report(
        "bluefield_shadow_publish",
        status="PASS",
        records=EXPECTED_RECORDS,
        already_present=False,
    )


def index():
    require_enabled()
    meta = broker_metadata(require_input=True)
    request("/" + INDEX)

    from confluent_kafka import Consumer, TopicPartition, OFFSET_INVALID

    client = Consumer(
        {
            "bootstrap.servers": TARGET,
            "group.id": INDEX_GROUP,
            "enable.auto.commit": False,
            "enable.auto.offset.store": False,
            "allow.auto.create.topics": False,
            "auto.offset.reset": "error",
        }
    )
    tp = TopicPartition(INPUT_TOPIC, 0)
    try:
        saved = client.committed([tp], timeout=10)[0]
        low, high = client.get_watermark_offsets(tp, timeout=10, cached=False)
        start = low if saved.offset == OFFSET_INVALID else saved.offset
        if not low <= start <= high:
            raise RuntimeError("Indexer offset outside retention")
        if high != EXPECTED_RECORDS:
            raise RuntimeError("Expected exact six-record input topic")
        client.assign([TopicPartition(INPUT_TOPIC, 0, start)])

        remaining = high - start
        processed = 0
        deadline = time.monotonic() + 30

        while processed < remaining and time.monotonic() < deadline:
            message = client.poll(1)
            if message is None:
                continue
            if message.error():
                raise RuntimeError("BlueField indexer Kafka poll failed")
            if len(message.value() or b"") > 1024 * 1024:
                raise RuntimeError("BlueField pilot record exceeds 1 MiB")

            value = message.value()
            review = validate_review(strict_json(value))
            source = {
                "cluster_id": meta.cluster_id,
                "topic": message.topic(),
                "partition": message.partition(),
                "offset": message.offset(),
            }
            document = to_shadow(review, source, value)
            doc_id = document_id(document)

            status, reply = request(
                f"/{INDEX}/_doc/{doc_id}?refresh=wait_for",
                document,
                "PUT",
            )
            shards = reply.get("_shards") if isinstance(reply, dict) else None
            if (
                status not in (200, 201)
                or reply.get("_id") != doc_id
                or reply.get("_index") != INDEX
                or not isinstance(shards, dict)
                or shards.get("failed") != 0
                or type(shards.get("successful")) is not int
                or shards["successful"] < 1
            ):
                raise RuntimeError(
                    "OpenSearch acknowledgement failed; Kafka offset not committed"
                )

            committed = client.commit(
                offsets=[
                    TopicPartition(
                        message.topic(),
                        message.partition(),
                        message.offset() + 1,
                    )
                ],
                asynchronous=False,
            )
            if any(part.error for part in committed):
                raise RuntimeError("Kafka offset commit failed")
            processed += 1

        if processed != remaining:
            raise RuntimeError("Timed out before indexing bounded BlueField batch")

        report(
            "bluefield_shadow_index",
            status="PASS",
            processed=processed,
            start_offset=start,
            end_offset=high,
            index=INDEX,
        )
    finally:
        client.close()


def verify():
    broker_metadata(require_input=True)
    values, _ = source_rows()
    if read_topic_exact() != values:
        raise RuntimeError("BlueField Kafka input no longer matches pinned evidence")

    _, result = request(
        "/" + INDEX + "/_search",
        {
            "size": 20,
            "track_total_hits": True,
            "sort": [
                {"timestamp": {"order": "asc"}},
                {"ibdev": {"order": "asc"}},
            ],
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"schema_version": "shadow-bluefield-1"}},
                        {"term": {"processing_mode": "shadow"}},
                        {"term": {"historical": True}},
                        {"term": {"production_ready": False}},
                        {"term": {"automated_response_allowed": False}},
                    ]
                }
            },
        },
        "POST",
    )
    if (
        result.get("timed_out") is not False
        or result.get("_shards", {}).get("failed") != 0
        or result.get("hits", {}).get("total")
        != {"value": EXPECTED_RECORDS, "relation": "eq"}
    ):
        raise RuntimeError("Incomplete BlueField shadow verification search")

    hits = result["hits"]["hits"]
    documents = [validate_shadow(hit["_source"]) for hit in hits]
    if len({document_id(row) for row in documents}) != EXPECTED_RECORDS:
        raise RuntimeError("Duplicate BlueField shadow document identity")
    if sum(row["carrier"] is None for row in documents) != 6:
        raise RuntimeError("Carrier null semantics changed")
    if sum(row["rx_bytes"] == 0 for row in documents) != 6:
        raise RuntimeError("Counter zero semantics changed")
    if sum(row["delta_rx_bytes"] is None for row in documents) != 2:
        raise RuntimeError("First-sample null semantics changed")
    if sum(row["delta_rx_bytes"] == 0 for row in documents) != 4:
        raise RuntimeError("Computed zero semantics changed")
    if any(
        "raw_event" in row or "capture_scope" in row
        for row in documents
    ):
        raise RuntimeError("Private archived fields leaked into shadow index")

    report(
        "bluefield_shadow_verify",
        status="PASS",
        records=EXPECTED_RECORDS,
        carrier_null=6,
        counter_zero=6,
        first_sample_null=2,
        computed_zero=4,
        historical=True,
        live=False,
        production_ready=False,
        automated_response_allowed=False,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=["preflight", "provision", "publish", "index", "verify"],
    )
    args = parser.parse_args()

    try:
        globals()[args.action]()
    except BaseException as error:
        frames = traceback.extract_tb(error.__traceback__)
        report(
            "bluefield_shadow_failed",
            action=args.action,
            error_type=type(error).__name__,
            locations=[
                {
                    "file": Path(frame.filename).name,
                    "line": frame.lineno,
                }
                for frame in frames
            ],
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
