"""Isolated BlueField Shadow recovery/resume test on replay infrastructure only.

This is a test harness, not a live service. It uses a unique Kafka topic,
consumer group and OpenSearch index derived from BLUEFIELD_RECOVERY_RUN_ID.
It never reads or writes the live bluefield-events topic.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
import traceback
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from bluefield_common import (
    EXPECTED_CLUSTER_ID,
    FORBIDDEN_LIVE_TOPICS,
    REPLAY_TOPICS,
    REVIEW_NORMALIZED_SHA256,
    TARGET,
    encode,
    strict_json,
    utc_now,
    validate_review,
)

OS_URL = "http://opensearch:9200"
SOURCE_FILE = Path("/bluefield-evidence/normalized.jsonl")
EXPECTED_RECORDS = 6
RUN_RE = re.compile(r"^[a-z0-9][a-z0-9-]{7,39}$")


def report(kind, **data):
    print(
        json.dumps(
            {"kind": kind, "time_utc": utc_now(), **data},
            allow_nan=False,
        ),
        flush=True,
    )


def require_enabled():
    if os.environ.get("BLUEFIELD_RECOVERY_RUN_ALLOWED") != "1":
        raise RuntimeError(
            "Recovery mutation disabled; set "
            "BLUEFIELD_RECOVERY_RUN_ALLOWED=1 explicitly"
        )


def names():
    run_id = os.environ.get("BLUEFIELD_RECOVERY_RUN_ID", "")
    if not RUN_RE.fullmatch(run_id):
        raise RuntimeError(
            "BLUEFIELD_RECOVERY_RUN_ID must be 8-40 lowercase "
            "letters/digits/hyphens"
        )
    topic = f"shadow-bluefield-recovery-{run_id}"
    index = f"shadow-bluefield-recovery-{run_id}"
    group = f"edrxdr-shadow-bluefield-recovery-{run_id}"
    return run_id, topic, index, group


def source_values():
    if not SOURCE_FILE.is_file():
        raise RuntimeError("Pinned BlueField normalized evidence missing")
    raw = SOURCE_FILE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != REVIEW_NORMALIZED_SHA256:
        raise RuntimeError("Archived normalized evidence hash changed")
    values = [line for line in raw.splitlines() if line.strip()]
    if len(values) != EXPECTED_RECORDS:
        raise RuntimeError("Expected exactly six archived records")
    rows = [validate_review(strict_json(value)) for value in values]
    if sum(row["carrier"] is None for row in rows) != 6:
        raise RuntimeError("Carrier null semantics changed")
    if sum(row["rx_bytes"] == 0 for row in rows) != 6:
        raise RuntimeError("RX zero semantics changed")
    if sum(row["delta_rx_bytes"] is None for row in rows) != 2:
        raise RuntimeError("First-sample null count changed")
    if sum(row["delta_rx_bytes"] == 0 for row in rows) != 4:
        raise RuntimeError("Computed zero count changed")
    return values, rows


def broker_metadata(topic=None):
    from confluent_kafka.admin import AdminClient

    meta = AdminClient(
        {
            "bootstrap.servers": TARGET,
            "socket.timeout.ms": 10000,
        }
    ).list_topics(timeout=10)
    if meta.cluster_id != EXPECTED_CLUSTER_ID:
        raise RuntimeError("Unexpected replay Kafka cluster ID")
    endpoints = {(broker.host, broker.port) for broker in meta.brokers.values()}
    if endpoints != {("kafka", 29092)}:
        raise RuntimeError("Unexpected replay Kafka listener")
    if not REPLAY_TOPICS.issubset(meta.topics):
        raise RuntimeError("Replay topic signature incomplete")
    if FORBIDDEN_LIVE_TOPICS.intersection(meta.topics):
        raise RuntimeError("Live/shared topic found on replay broker")
    if topic is not None and topic in meta.topics:
        metadata = meta.topics[topic]
        if metadata.error or len(metadata.partitions) != 1:
            raise RuntimeError("Recovery topic is not healthy single-partition")
    return meta


def request(index, path, body=None, method="GET"):
    allowed = (
        path == "/_cluster/health"
        or path == f"/{index}"
        or path.startswith(f"/{index}/_doc/")
        or path.startswith(f"/{index}/_search")
    )
    if not allowed:
        raise RuntimeError("OpenSearch endpoint outside recovery allowlist")
    req = Request(
        OS_URL + path,
        data=None if body is None else encode(body),
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urlopen(req, timeout=15) as response:
        return response.status, json.load(response)


def index_mapping():
    return {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
        },
        "mappings": {
            "dynamic": "strict",
            "properties": {
                "run_id": {"type": "keyword"},
                "processing_mode": {"type": "keyword"},
                "historical": {"type": "boolean"},
                "production_ready": {"type": "boolean"},
                "automated_response_allowed": {"type": "boolean"},
                "timestamp": {"type": "date"},
                "ibdev": {"type": "keyword"},
                "interface": {"type": "keyword"},
                "operstate": {"type": "keyword"},
                "carrier": {"type": "byte", "coerce": False},
                "rx_bytes": {"type": "unsigned_long"},
                "delta_rx_bytes": {"type": "unsigned_long"},
                "delta_status_rx_bytes": {"type": "keyword"},
                "sample_interval_seconds": {
                    "type": "double",
                    "coerce": False,
                },
                "input_sha256": {"type": "keyword"},
                "source": {
                    "type": "object",
                    "dynamic": "strict",
                    "properties": {
                        "topic": {"type": "keyword"},
                        "partition": {"type": "integer"},
                        "offset": {"type": "long"},
                    },
                },
            },
        },
    }


def topic_bounds(topic):
    from confluent_kafka import Consumer, TopicPartition

    client = Consumer(
        {
            "bootstrap.servers": TARGET,
            "group.id": "edrxdr-bluefield-recovery-inspect",
            "enable.auto.commit": False,
            "allow.auto.create.topics": False,
            "auto.offset.reset": "error",
        }
    )
    try:
        return client.get_watermark_offsets(
            TopicPartition(topic, 0),
            timeout=10,
            cached=False,
        )
    finally:
        client.close()


def committed_offset(topic, group):
    from confluent_kafka import Consumer, TopicPartition, OFFSET_INVALID

    client = Consumer(
        {
            "bootstrap.servers": TARGET,
            "group.id": group,
            "enable.auto.commit": False,
            "allow.auto.create.topics": False,
            "auto.offset.reset": "error",
        }
    )
    try:
        saved = client.committed(
            [TopicPartition(topic, 0)],
            timeout=10,
        )[0].offset
        return None if saved == OFFSET_INVALID else saved
    finally:
        client.close()


def count_docs(index):
    try:
        _, result = request(
            index,
            f"/{index}/_search",
            {
                "size": 0,
                "track_total_hits": True,
                "query": {"match_all": {}},
            },
            "POST",
        )
    except HTTPError as error:
        if error.code == 404:
            return None
        raise
    total = result.get("hits", {}).get("total")
    if (
        result.get("timed_out") is not False
        or result.get("_shards", {}).get("failed") != 0
        or not isinstance(total, dict)
        or total.get("relation") != "eq"
        or type(total.get("value")) is not int
    ):
        raise RuntimeError("Incomplete recovery index count")
    return total["value"]


def safe_doc(run_id, topic, message):
    value = message.value()
    row = validate_review(strict_json(value))
    input_sha256 = hashlib.sha256(value).hexdigest()
    identity = [
        run_id,
        topic,
        message.partition(),
        message.offset(),
        input_sha256,
    ]
    doc_id = hashlib.sha256(
        json.dumps(identity).encode("utf-8")
    ).hexdigest()
    doc = {
        "run_id": run_id,
        "processing_mode": "shadow_recovery_test",
        "historical": True,
        "production_ready": False,
        "automated_response_allowed": False,
        "timestamp": row["timestamp"],
        "ibdev": row["ibdev"],
        "interface": row["interface"],
        "operstate": row["operstate"],
        "carrier": row["carrier"],
        "rx_bytes": row["rx_bytes"],
        "delta_rx_bytes": row["delta_rx_bytes"],
        "delta_status_rx_bytes": row["delta_status"]["rx_bytes"],
        "sample_interval_seconds": row["sample_interval_seconds"],
        "input_sha256": input_sha256,
        "source": {
            "topic": topic,
            "partition": message.partition(),
            "offset": message.offset(),
        },
    }
    return doc_id, doc


def preflight():
    run_id, topic, index, group = names()
    source_values()
    meta = broker_metadata()
    _, health = request(index, "/_cluster/health")
    if health.get("timed_out") or health.get("status") == "red":
        raise RuntimeError("Replay OpenSearch unavailable")
    report(
        "bluefield_recovery_preflight",
        status="PASS",
        run_id=run_id,
        topic=topic,
        index=index,
        group=group,
        source_records=EXPECTED_RECORDS,
        source_sha256=REVIEW_NORMALIZED_SHA256,
        replay_cluster_id=meta.cluster_id,
        opensearch_status=health.get("status"),
        live_source_used=False,
        gpu_used=False,
        automated_response_allowed=False,
    )


def setup():
    require_enabled()
    run_id, topic, index, group = names()
    meta = broker_metadata()
    if topic in meta.topics:
        raise RuntimeError("Recovery topic already exists; choose a new run ID")
    if count_docs(index) is not None:
        raise RuntimeError("Recovery index already exists; choose a new run ID")
    if committed_offset(topic, group) is not None:
        raise RuntimeError("Recovery group already has committed state")

    from confluent_kafka.admin import AdminClient, NewTopic

    admin = AdminClient({"bootstrap.servers": TARGET})
    future = admin.create_topics(
        [
            NewTopic(
                topic,
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
    )[topic]
    future.result()

    status, reply = request(index, f"/{index}", index_mapping(), "PUT")
    if (
        status not in (200, 201)
        or reply.get("acknowledged") is not True
        or reply.get("shards_acknowledged") is not True
    ):
        raise RuntimeError("Recovery index creation not acknowledged")

    broker_metadata(topic)
    if topic_bounds(topic) != (0, 0):
        raise RuntimeError("Recovery topic not empty after setup")
    if count_docs(index) != 0:
        raise RuntimeError("Recovery index not empty after setup")

    report(
        "bluefield_recovery_setup",
        status="PASS",
        run_id=run_id,
        topic=topic,
        index=index,
        group=group,
    )


def publish():
    require_enabled()
    run_id, topic, index, group = names()
    broker_metadata(topic)
    values, _ = source_values()
    if topic_bounds(topic) != (0, 0):
        raise RuntimeError("Recovery topic must be empty before publish")

    from confluent_kafka import Producer

    failures = []
    producer = Producer(
        {
            "bootstrap.servers": TARGET,
            "enable.idempotence": True,
            "acks": "all",
            "delivery.timeout.ms": 30000,
        }
    )

    def delivered(error, _):
        if error is not None:
            failures.append(type(error).__name__)

    for value in values:
        producer.produce(
            topic,
            partition=0,
            key=hashlib.sha256(value).hexdigest().encode("ascii"),
            value=value,
            on_delivery=delivered,
        )
    remaining = producer.flush(35)
    if remaining or failures:
        raise RuntimeError("Recovery publish acknowledgement failed")
    if topic_bounds(topic) != (0, EXPECTED_RECORDS):
        raise RuntimeError("Expected six recovery topic records")

    report(
        "bluefield_recovery_publish",
        status="PASS",
        run_id=run_id,
        records=EXPECTED_RECORDS,
    )


def consume(limit):
    require_enabled()
    run_id, topic, index, group = names()
    broker_metadata(topic)

    from confluent_kafka import Consumer, TopicPartition, OFFSET_INVALID

    client = Consumer(
        {
            "bootstrap.servers": TARGET,
            "group.id": group,
            "enable.auto.commit": False,
            "enable.auto.offset.store": False,
            "allow.auto.create.topics": False,
            "auto.offset.reset": "error",
        }
    )
    tp = TopicPartition(topic, 0)
    try:
        saved = client.committed([tp], timeout=10)[0]
        low, high = client.get_watermark_offsets(
            tp,
            timeout=10,
            cached=False,
        )
        start = low if saved.offset == OFFSET_INVALID else saved.offset
        if (low, high) != (0, EXPECTED_RECORDS):
            raise RuntimeError("Recovery topic bounds are not 0..6")
        if not 0 <= start <= EXPECTED_RECORDS:
            raise RuntimeError("Committed recovery offset outside bounds")

        remaining = high - start
        target = remaining if limit is None else min(limit, remaining)
        client.assign([TopicPartition(topic, 0, start)])

        processed = 0
        deadline = time.monotonic() + 30

        while processed < target and time.monotonic() < deadline:
            message = client.poll(1)
            if message is None:
                continue
            if message.error():
                raise RuntimeError("Recovery Kafka poll failed")

            doc_id, doc = safe_doc(run_id, topic, message)
            status, reply = request(
                index,
                f"/{index}/_doc/{doc_id}?refresh=wait_for",
                doc,
                "PUT",
            )
            shards = reply.get("_shards") if isinstance(reply, dict) else None
            if (
                status not in (200, 201)
                or reply.get("_id") != doc_id
                or reply.get("_index") != index
                or not isinstance(shards, dict)
                or shards.get("failed") != 0
                or type(shards.get("successful")) is not int
                or shards["successful"] < 1
            ):
                raise RuntimeError(
                    "Recovery OpenSearch ACK failed; offset not committed"
                )

            committed = client.commit(
                offsets=[
                    TopicPartition(
                        topic,
                        0,
                        message.offset() + 1,
                    )
                ],
                asynchronous=False,
            )
            if any(part.error for part in committed):
                raise RuntimeError("Recovery Kafka commit failed")
            processed += 1

        if processed != target:
            raise RuntimeError("Recovery phase timed out")

        end_offset = committed_offset(topic, group)
        docs = count_docs(index)

        report(
            "bluefield_recovery_consume",
            status="PASS",
            run_id=run_id,
            start_offset=start,
            processed=processed,
            committed_offset=end_offset,
            log_end_offset=high,
            lag=high - (end_offset or 0),
            docs=docs,
        )
        return start, processed, end_offset, docs
    finally:
        client.close()


def phase1():
    start, processed, end_offset, docs = consume(3)
    if (start, processed, end_offset, docs) != (0, 3, 3, 3):
        raise RuntimeError(
            "Phase 1 expected start=0 processed=3 offset=3 docs=3"
        )


def phase2():
    start, processed, end_offset, docs = consume(None)
    if (start, processed, end_offset, docs) != (3, 3, 6, 6):
        raise RuntimeError(
            "Phase 2 expected start=3 processed=3 offset=6 docs=6"
        )


def rerun():
    start, processed, end_offset, docs = consume(None)
    if (start, processed, end_offset, docs) != (6, 0, 6, 6):
        raise RuntimeError(
            "Rerun expected start=6 processed=0 offset=6 docs=6"
        )


def verify():
    run_id, topic, index, group = names()
    broker_metadata(topic)
    if topic_bounds(topic) != (0, 6):
        raise RuntimeError("Unexpected final recovery topic bounds")
    if committed_offset(topic, group) != 6:
        raise RuntimeError("Recovery group did not finish at offset 6")

    _, result = request(
        index,
        f"/{index}/_search",
        {
            "size": 10,
            "track_total_hits": True,
            "sort": [{"source.offset": {"order": "asc"}}],
            "query": {"term": {"run_id": run_id}},
        },
        "POST",
    )
    if (
        result.get("timed_out") is not False
        or result.get("_shards", {}).get("failed") != 0
        or result.get("hits", {}).get("total")
        != {"value": 6, "relation": "eq"}
    ):
        raise RuntimeError("Incomplete recovery verification search")

    hits = result["hits"]["hits"]
    if len(hits) != 6 or len({hit["_id"] for hit in hits}) != 6:
        raise RuntimeError("Recovery duplicate/missing document identity")

    rows = [hit["_source"] for hit in hits]
    if [row["source"]["offset"] for row in rows] != list(range(6)):
        raise RuntimeError("Recovery source offsets are not 0..5")
    if sum(row["carrier"] is None for row in rows) != 6:
        raise RuntimeError("Recovery carrier null semantics changed")
    if sum(row["rx_bytes"] == 0 for row in rows) != 6:
        raise RuntimeError("Recovery zero counter semantics changed")
    if sum(row["delta_rx_bytes"] is None for row in rows) != 2:
        raise RuntimeError("Recovery first-sample null semantics changed")
    if sum(row["delta_rx_bytes"] == 0 for row in rows) != 4:
        raise RuntimeError("Recovery computed zero semantics changed")
    if any(
        row["production_ready"] is not False
        or row["automated_response_allowed"] is not False
        or row["historical"] is not True
        for row in rows
    ):
        raise RuntimeError("Recovery safety flags changed")

    report(
        "bluefield_recovery_verify",
        status="PASS",
        run_id=run_id,
        records=6,
        committed_offset=6,
        log_end_offset=6,
        lag=0,
        unique_documents=6,
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
        choices=[
            "preflight",
            "setup",
            "publish",
            "phase1",
            "phase2",
            "rerun",
            "verify",
        ],
    )
    args = parser.parse_args()
    try:
        globals()[args.action]()
    except BaseException as error:
        frames = traceback.extract_tb(error.__traceback__)
        report(
            "bluefield_recovery_failed",
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
