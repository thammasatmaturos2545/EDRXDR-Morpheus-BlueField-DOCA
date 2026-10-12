"""Isolated BlueField Shadow quarantine/DLQ policy test on replay infrastructure only.

Flow under test:
  valid source record -> valid index ACK -> commit source offset
  poison source record -> strict validation failure
                       -> quarantine index ACK
                       -> quarantine Kafka ACK
                       -> commit source offset
  later valid record   -> valid index ACK -> commit source offset

A failure-injection step deliberately gives the quarantine index an
incompatible strict mapping. The poison record must then remain uncommitted.
After repairing only that isolated index, a fresh process retries the same
poison source offset and quarantines it successfully.

This harness never reads/writes the live ``bluefield-events`` topic and
never starts ``edrxdr-bluefield.service``.
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
    if os.environ.get("BLUEFIELD_QUARANTINE_RUN_ALLOWED") != "1":
        raise RuntimeError(
            "Quarantine-test mutation disabled; set "
            "BLUEFIELD_QUARANTINE_RUN_ALLOWED=1 explicitly"
        )


def resources():
    run_id = os.environ.get("BLUEFIELD_QUARANTINE_RUN_ID", "")
    if not RUN_RE.fullmatch(run_id):
        raise RuntimeError(
            "BLUEFIELD_QUARANTINE_RUN_ID must be 8-40 lowercase "
            "letters/digits/hyphens"
        )
    return {
        "run_id": run_id,
        "input_topic": f"shadow-bluefield-quarantine-input-{run_id}",
        "quarantine_topic": f"shadow-bluefield-quarantine-dlq-{run_id}",
        "group": f"edrxdr-shadow-bluefield-quarantine-{run_id}",
        "valid_index": f"shadow-bluefield-quarantine-valid-{run_id}",
        "quarantine_index": f"shadow-bluefield-quarantine-dlq-{run_id}",
    }


def source_values():
    if not SOURCE_FILE.is_file():
        raise RuntimeError("Pinned BlueField normalized evidence missing")
    raw = SOURCE_FILE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != REVIEW_NORMALIZED_SHA256:
        raise RuntimeError("Archived normalized evidence hash changed")
    values = [line for line in raw.splitlines() if line.strip()]
    if len(values) != 6:
        raise RuntimeError("Expected exactly six archived records")
    rows = [validate_review(strict_json(value)) for value in values]
    return values, rows


def poisoned_value(value: bytes) -> bytes:
    row = strict_json(value)
    row["carrier"] = 2
    bad = encode(row)
    try:
        validate_review(strict_json(bad))
    except ValueError:
        return bad
    raise RuntimeError("Poison fixture unexpectedly passed strict validation")


def broker_metadata(required_topics=()):
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

    for topic in required_topics:
        current = meta.topics.get(topic)
        if current is None or current.error or len(current.partitions) != 1:
            raise RuntimeError(f"Required isolated topic unavailable: {topic}")
    return meta


def request(index, path, body=None, method="GET"):
    allowed = (
        path == "/_cluster/health"
        or path == f"/{index}"
        or path.startswith(f"/{index}/_doc/")
        or path.startswith(f"/{index}/_search")
    )
    if not allowed:
        raise RuntimeError("OpenSearch endpoint outside quarantine allowlist")

    req = Request(
        OS_URL + path,
        data=None if body is None else encode(body),
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urlopen(req, timeout=15) as response:
        return response.status, json.load(response)


def valid_mapping():
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


def quarantine_mapping():
    return {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
        },
        "mappings": {
            "dynamic": "strict",
            "properties": {
                "schema_version": {"type": "keyword"},
                "processing_mode": {"type": "keyword"},
                "run_id": {"type": "keyword"},
                "reason_code": {"type": "keyword"},
                "error_type": {"type": "keyword"},
                "validation_stage": {"type": "keyword"},
                "input_sha256": {"type": "keyword"},
                "quarantined_at_utc": {"type": "date"},
                "historical": {"type": "boolean"},
                "production_ready": {"type": "boolean"},
                "automated_response_allowed": {"type": "boolean"},
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


def bad_quarantine_mapping():
    mapping = quarantine_mapping()
    # Every quarantine envelope contains input_sha256. Removing it from a
    # strict mapping gives us a deterministic isolated write failure.
    del mapping["mappings"]["properties"]["input_sha256"]
    return mapping


def topic_bounds(topic):
    from confluent_kafka import Consumer, TopicPartition

    client = Consumer(
        {
            "bootstrap.servers": TARGET,
            "group.id": "edrxdr-bluefield-quarantine-inspect",
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
        offset = client.committed(
            [TopicPartition(topic, 0)],
            timeout=10,
        )[0].offset
        return None if offset == OFFSET_INVALID else offset
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
        raise RuntimeError("Incomplete isolated index count")
    return total["value"]


def create_topic(admin, topic):
    from confluent_kafka.admin import NewTopic

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


def create_index(index, mapping):
    status, reply = request(index, f"/{index}", mapping, "PUT")
    if (
        status not in (200, 201)
        or reply.get("acknowledged") is not True
        or reply.get("shards_acknowledged") is not True
    ):
        raise RuntimeError(f"Index creation not acknowledged: {index}")


def poll_at_commit(topic, group):
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
    saved = client.committed([tp], timeout=10)[0].offset
    low, high = client.get_watermark_offsets(tp, timeout=10, cached=False)
    start = low if saved == OFFSET_INVALID else saved.offset if hasattr(saved, "offset") else saved
    # confluent-kafka committed() above returns TopicPartition; keep this
    # defensive branch explicit because version differences can expose
    # either object/offset access patterns.
    if not isinstance(start, int):
        start = saved
    client.assign([TopicPartition(topic, 0, start)])

    deadline = time.monotonic() + 15
    message = None
    while message is None and time.monotonic() < deadline:
        current = client.poll(1)
        if current is None:
            continue
        if current.error():
            client.close()
            raise RuntimeError("Quarantine-test Kafka poll failed")
        message = current

    if message is None:
        client.close()
        raise RuntimeError("Quarantine-test Kafka poll timed out")
    return client, message, start, high


def commit_after_ack(client, message):
    from confluent_kafka import TopicPartition

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
        raise RuntimeError("Quarantine-test Kafka commit failed")


def valid_doc(run_id, topic, message):
    value = message.value()
    row = validate_review(strict_json(value))
    digest = hashlib.sha256(value).hexdigest()
    identity = [
        run_id,
        "valid",
        topic,
        message.partition(),
        message.offset(),
        digest,
    ]
    doc_id = hashlib.sha256(
        json.dumps(identity).encode("utf-8")
    ).hexdigest()
    doc = {
        "run_id": run_id,
        "processing_mode": "shadow_quarantine_test",
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
        "input_sha256": digest,
        "source": {
            "topic": topic,
            "partition": message.partition(),
            "offset": message.offset(),
        },
    }
    return doc_id, doc


def quarantine_envelope(run_id, topic, message, error):
    value = message.value() or b""
    digest = hashlib.sha256(value).hexdigest()
    envelope = {
        "schema_version": "bluefield-quarantine-1",
        "processing_mode": "shadow_quarantine",
        "run_id": run_id,
        "reason_code": "strict_validation_failed",
        "error_type": type(error).__name__,
        "validation_stage": "validate_review",
        "input_sha256": digest,
        "quarantined_at_utc": utc_now(),
        "historical": True,
        "production_ready": False,
        "automated_response_allowed": False,
        "source": {
            "topic": topic,
            "partition": message.partition(),
            "offset": message.offset(),
        },
    }
    identity = [
        run_id,
        topic,
        message.partition(),
        message.offset(),
        digest,
    ]
    doc_id = hashlib.sha256(
        json.dumps(identity).encode("utf-8")
    ).hexdigest()
    return doc_id, envelope


def write_doc(index, doc_id, doc):
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
        raise RuntimeError("OpenSearch acknowledgement failed")


def produce_quarantine(topic, key, envelope):
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

    producer.produce(
        topic,
        partition=0,
        key=key.encode("ascii"),
        value=encode(envelope),
        on_delivery=delivered,
    )
    remaining = producer.flush(35)
    if remaining or failures:
        raise RuntimeError("Quarantine Kafka acknowledgement failed")


def read_topic_exact(topic):
    from confluent_kafka import Consumer, TopicPartition

    low, high = topic_bounds(topic)
    client = Consumer(
        {
            "bootstrap.servers": TARGET,
            "group.id": "edrxdr-bluefield-quarantine-verify",
            "enable.auto.commit": False,
            "allow.auto.create.topics": False,
            "auto.offset.reset": "error",
        }
    )
    values = []
    try:
        client.assign([TopicPartition(topic, 0, low)])
        deadline = time.monotonic() + 15
        while len(values) < high - low and time.monotonic() < deadline:
            message = client.poll(1)
            if message is None:
                continue
            if message.error():
                raise RuntimeError("Quarantine verification poll failed")
            values.append(message.value())
    finally:
        client.close()
    if len(values) != high - low:
        raise RuntimeError("Could not read complete quarantine topic")
    return values


def preflight():
    r = resources()
    values, rows = source_values()
    poison = poisoned_value(values[1])
    try:
        validate_review(strict_json(poison))
    except ValueError:
        pass
    else:
        raise RuntimeError("Poison fixture unexpectedly valid")

    meta = broker_metadata()
    _, health = request(r["valid_index"], "/_cluster/health")
    if health.get("timed_out") or health.get("status") == "red":
        raise RuntimeError("Replay OpenSearch unavailable")
    if rows[0]["carrier"] is not None or rows[0]["rx_bytes"] != 0:
        raise RuntimeError("Pinned first-row semantics changed")

    report(
        "bluefield_quarantine_preflight",
        status="PASS",
        run_id=r["run_id"],
        source_records=6,
        source_sha256=REVIEW_NORMALIZED_SHA256,
        replay_cluster_id=meta.cluster_id,
        opensearch_status=health.get("status"),
        poison_fixture_rejected=True,
        raw_payload_stored_in_quarantine=False,
        live_source_used=False,
        gpu_used=False,
        automated_response_allowed=False,
    )


def setup():
    require_enabled()
    r = resources()
    meta = broker_metadata()

    for topic in (r["input_topic"], r["quarantine_topic"]):
        if topic in meta.topics:
            raise RuntimeError(
                f"Isolated topic already exists; choose a new run ID: {topic}"
            )
    for index in (r["valid_index"], r["quarantine_index"]):
        if count_docs(index) is not None:
            raise RuntimeError(
                f"Isolated index already exists; choose a new run ID: {index}"
            )
    if committed_offset(r["input_topic"], r["group"]) is not None:
        raise RuntimeError("Isolated input group unexpectedly has state")

    from confluent_kafka.admin import AdminClient

    admin = AdminClient({"bootstrap.servers": TARGET})
    create_topic(admin, r["input_topic"])
    create_topic(admin, r["quarantine_topic"])
    create_index(r["valid_index"], valid_mapping())
    create_index(r["quarantine_index"], bad_quarantine_mapping())

    broker_metadata((r["input_topic"], r["quarantine_topic"]))

    if topic_bounds(r["input_topic"]) != (0, 0):
        raise RuntimeError("Input topic not empty after setup")
    if topic_bounds(r["quarantine_topic"]) != (0, 0):
        raise RuntimeError("Quarantine topic not empty after setup")
    if count_docs(r["valid_index"]) != 0:
        raise RuntimeError("Valid index not empty after setup")
    if count_docs(r["quarantine_index"]) != 0:
        raise RuntimeError("Quarantine index not empty after setup")

    report(
        "bluefield_quarantine_setup",
        status="PASS",
        run_id=r["run_id"],
        input_topic=r["input_topic"],
        quarantine_topic=r["quarantine_topic"],
        valid_index=r["valid_index"],
        quarantine_index=r["quarantine_index"],
    )


def publish():
    require_enabled()
    r = resources()
    broker_metadata((r["input_topic"], r["quarantine_topic"]))
    values, _ = source_values()

    if topic_bounds(r["input_topic"]) != (0, 0):
        raise RuntimeError("Input topic must be empty before publish")
    if topic_bounds(r["quarantine_topic"]) != (0, 0):
        raise RuntimeError("Quarantine topic must be empty before publish")

    items = [values[0], poisoned_value(values[1]), values[2]]

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

    for value in items:
        producer.produce(
            r["input_topic"],
            partition=0,
            key=hashlib.sha256(value).hexdigest().encode("ascii"),
            value=value,
            on_delivery=delivered,
        )

    remaining = producer.flush(35)
    if remaining or failures:
        raise RuntimeError("Input publish acknowledgement failed")
    if topic_bounds(r["input_topic"]) != (0, 3):
        raise RuntimeError("Expected exactly three input records")

    report(
        "bluefield_quarantine_publish",
        status="PASS",
        run_id=r["run_id"],
        input_records=3,
        quarantine_records=0,
    )


def valid_first():
    require_enabled()
    r = resources()
    client, message, start, high = poll_at_commit(
        r["input_topic"], r["group"]
    )
    try:
        if (start, high, message.offset()) != (0, 3, 0):
            raise RuntimeError("Expected first valid record at source offset 0")
        doc_id, doc = valid_doc(
            r["run_id"], r["input_topic"], message
        )
        write_doc(r["valid_index"], doc_id, doc)
        commit_after_ack(client, message)
    finally:
        client.close()

    if committed_offset(r["input_topic"], r["group"]) != 1:
        raise RuntimeError("Input group did not commit offset 1")
    if count_docs(r["valid_index"]) != 1:
        raise RuntimeError("Valid index should contain one document")

    report(
        "bluefield_quarantine_valid_first",
        status="PASS",
        committed_offset=1,
        log_end_offset=3,
        lag=2,
        valid_docs=1,
        quarantine_docs=0,
        quarantine_topic_records=0,
    )


def quarantine_fail():
    require_enabled()
    r = resources()
    client, message, start, high = poll_at_commit(
        r["input_topic"], r["group"]
    )
    try:
        if (start, high, message.offset()) != (1, 3, 1):
            raise RuntimeError("Expected poison record at source offset 1")
        try:
            validate_review(strict_json(message.value()))
        except ValueError as error:
            doc_id, envelope = quarantine_envelope(
                r["run_id"], r["input_topic"], message, error
            )
        else:
            raise RuntimeError("Poison record unexpectedly passed validation")

        try:
            write_doc(r["quarantine_index"], doc_id, envelope)
        except HTTPError as error:
            if error.code not in (400, 409):
                raise
        else:
            raise RuntimeError(
                "Intentionally incompatible quarantine mapping did not reject"
            )
        # No quarantine-topic publish and no source commit after failure.
    finally:
        client.close()

    offset = committed_offset(r["input_topic"], r["group"])
    if offset != 1:
        raise RuntimeError("Failed quarantine write advanced source offset")
    if count_docs(r["quarantine_index"]) != 0:
        raise RuntimeError("Failed quarantine write stored a document")
    if topic_bounds(r["quarantine_topic"]) != (0, 0):
        raise RuntimeError("Failed quarantine write emitted a DLQ message")

    report(
        "bluefield_quarantine_fail",
        status="PASS",
        expected_failure="quarantine_index_mapping_rejection",
        poison_source_offset=1,
        committed_offset=1,
        log_end_offset=3,
        lag=2,
        valid_docs=1,
        quarantine_docs=0,
        quarantine_topic_records=0,
    )


def repair():
    require_enabled()
    r = resources()

    if committed_offset(r["input_topic"], r["group"]) != 1:
        raise RuntimeError("Cannot repair after unexpected source commit")
    if count_docs(r["quarantine_index"]) != 0:
        raise RuntimeError("Cannot repair non-empty quarantine index")
    if topic_bounds(r["quarantine_topic"]) != (0, 0):
        raise RuntimeError("Cannot repair after quarantine topic mutation")

    status, reply = request(
        r["quarantine_index"],
        f"/{r['quarantine_index']}",
        None,
        "DELETE",
    )
    if status not in (200, 202) or reply.get("acknowledged") is not True:
        raise RuntimeError("Bad quarantine index deletion not acknowledged")

    create_index(r["quarantine_index"], quarantine_mapping())

    if count_docs(r["quarantine_index"]) != 0:
        raise RuntimeError("Repaired quarantine index is not empty")

    report(
        "bluefield_quarantine_repair",
        status="PASS",
        committed_offset=1,
        quarantine_docs=0,
        quarantine_topic_records=0,
    )


def quarantine_resume():
    require_enabled()
    r = resources()
    client, message, start, high = poll_at_commit(
        r["input_topic"], r["group"]
    )
    try:
        if (start, high, message.offset()) != (1, 3, 1):
            raise RuntimeError(
                "Fresh process must retry poison source offset 1"
            )
        try:
            validate_review(strict_json(message.value()))
        except ValueError as error:
            doc_id, envelope = quarantine_envelope(
                r["run_id"], r["input_topic"], message, error
            )
        else:
            raise RuntimeError("Poison record unexpectedly passed validation")

        # Source offset may advance only after BOTH quarantine sinks ACK.
        write_doc(r["quarantine_index"], doc_id, envelope)
        produce_quarantine(r["quarantine_topic"], doc_id, envelope)

        if count_docs(r["quarantine_index"]) != 1:
            raise RuntimeError("Quarantine index ACK not visible")
        if topic_bounds(r["quarantine_topic"]) != (0, 1):
            raise RuntimeError("Quarantine Kafka ACK not visible")

        commit_after_ack(client, message)
    finally:
        client.close()

    offset = committed_offset(r["input_topic"], r["group"])
    if offset != 2:
        raise RuntimeError("Source group did not commit poison offset to 2")

    report(
        "bluefield_quarantine_resume",
        status="PASS",
        retried_poison_source_offset=1,
        committed_offset=2,
        log_end_offset=3,
        lag=1,
        valid_docs=1,
        quarantine_docs=1,
        quarantine_topic_records=1,
    )


def valid_final():
    require_enabled()
    r = resources()
    client, message, start, high = poll_at_commit(
        r["input_topic"], r["group"]
    )
    try:
        if (start, high, message.offset()) != (2, 3, 2):
            raise RuntimeError("Expected final valid record at source offset 2")
        doc_id, doc = valid_doc(
            r["run_id"], r["input_topic"], message
        )
        write_doc(r["valid_index"], doc_id, doc)
        commit_after_ack(client, message)
    finally:
        client.close()

    offset = committed_offset(r["input_topic"], r["group"])
    if offset != 3:
        raise RuntimeError("Final valid record did not commit offset 3")
    if count_docs(r["valid_index"]) != 2:
        raise RuntimeError("Valid index should contain exactly two documents")

    report(
        "bluefield_quarantine_valid_final",
        status="PASS",
        committed_offset=3,
        log_end_offset=3,
        lag=0,
        valid_docs=2,
        quarantine_docs=1,
        quarantine_topic_records=1,
    )


def verify():
    r = resources()
    broker_metadata((r["input_topic"], r["quarantine_topic"]))

    if topic_bounds(r["input_topic"]) != (0, 3):
        raise RuntimeError("Input topic bounds changed")
    if topic_bounds(r["quarantine_topic"]) != (0, 1):
        raise RuntimeError("Quarantine topic should contain exactly one record")
    if committed_offset(r["input_topic"], r["group"]) != 3:
        raise RuntimeError("Input consumer group did not finish at offset 3")
    if count_docs(r["valid_index"]) != 2:
        raise RuntimeError("Expected exactly two valid documents")
    if count_docs(r["quarantine_index"]) != 1:
        raise RuntimeError("Expected exactly one quarantine document")

    _, valid = request(
        r["valid_index"],
        f"/{r['valid_index']}/_search",
        {
            "size": 10,
            "track_total_hits": True,
            "sort": [{"source.offset": {"order": "asc"}}],
            "query": {"term": {"run_id": r["run_id"]}},
        },
        "POST",
    )
    if (
        valid.get("timed_out") is not False
        or valid.get("_shards", {}).get("failed") != 0
        or valid.get("hits", {}).get("total")
        != {"value": 2, "relation": "eq"}
    ):
        raise RuntimeError("Incomplete valid-index verification")

    valid_rows = [hit["_source"] for hit in valid["hits"]["hits"]]
    if [row["source"]["offset"] for row in valid_rows] != [0, 2]:
        raise RuntimeError("Valid source offsets should be 0 and 2")

    _, quarantined = request(
        r["quarantine_index"],
        f"/{r['quarantine_index']}/_search",
        {
            "size": 10,
            "track_total_hits": True,
            "query": {"term": {"run_id": r["run_id"]}},
        },
        "POST",
    )
    if (
        quarantined.get("timed_out") is not False
        or quarantined.get("_shards", {}).get("failed") != 0
        or quarantined.get("hits", {}).get("total")
        != {"value": 1, "relation": "eq"}
    ):
        raise RuntimeError("Incomplete quarantine-index verification")

    q = quarantined["hits"]["hits"][0]["_source"]
    expected_fields = {
        "schema_version",
        "processing_mode",
        "run_id",
        "reason_code",
        "error_type",
        "validation_stage",
        "input_sha256",
        "quarantined_at_utc",
        "historical",
        "production_ready",
        "automated_response_allowed",
        "source",
    }
    if set(q) != expected_fields:
        raise RuntimeError("Quarantine envelope contains unexpected fields")
    if q["source"]["offset"] != 1:
        raise RuntimeError("Quarantine source offset should be 1")
    if (
        q["schema_version"] != "bluefield-quarantine-1"
        or q["reason_code"] != "strict_validation_failed"
        or q["validation_stage"] != "validate_review"
        or q["historical"] is not True
        or q["production_ready"] is not False
        or q["automated_response_allowed"] is not False
    ):
        raise RuntimeError("Quarantine safety envelope changed")

    topic_values = read_topic_exact(r["quarantine_topic"])
    if len(topic_values) != 1:
        raise RuntimeError("Expected one quarantine Kafka value")
    q_topic = strict_json(topic_values[0])
    if q_topic != q:
        raise RuntimeError(
            "Quarantine Kafka envelope differs from indexed envelope"
        )
    if "raw_event" in q or "capture_scope" in q:
        raise RuntimeError("Private archived fields leaked into quarantine")
    text = json.dumps(q, ensure_ascii=False)
    if '"carrier": 2' in text or '"carrier":2' in text:
        raise RuntimeError("Poison raw field leaked into quarantine envelope")

    report(
        "bluefield_quarantine_verify",
        status="PASS",
        input_records=3,
        committed_offset=3,
        log_end_offset=3,
        lag=0,
        valid_docs=2,
        valid_source_offsets=[0, 2],
        quarantine_docs=1,
        quarantine_topic_records=1,
        quarantine_source_offset=1,
        raw_payload_stored=False,
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
            "valid-first",
            "quarantine-fail",
            "repair",
            "quarantine-resume",
            "valid-final",
            "verify",
        ],
    )
    args = parser.parse_args()

    dispatch = {
        "preflight": preflight,
        "setup": setup,
        "publish": publish,
        "valid-first": valid_first,
        "quarantine-fail": quarantine_fail,
        "repair": repair,
        "quarantine-resume": quarantine_resume,
        "valid-final": valid_final,
        "verify": verify,
    }

    try:
        dispatch[args.action]()
    except BaseException as error:
        frames = traceback.extract_tb(error.__traceback__)
        report(
            "bluefield_quarantine_failed",
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
