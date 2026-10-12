"""Isolated fail-closed tests for the BlueField Shadow commit boundary.

Two scenarios are exercised on replay infrastructure only:

1) poison: a strict-schema-invalid Kafka record must fail validation and the
   consumer group must remain pinned before that record across a fresh
   process retry.
2) osfail: a valid record is sent to an intentionally incompatible isolated
   OpenSearch index. The write must fail and Kafka must not commit. After the
   isolated index is repaired, a fresh process must consume the same record,
   index it successfully, and only then commit.

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
    if os.environ.get("BLUEFIELD_FAILURE_RUN_ALLOWED") != "1":
        raise RuntimeError(
            "Failure-test mutation disabled; set "
            "BLUEFIELD_FAILURE_RUN_ALLOWED=1 explicitly"
        )


def resources():
    run_id = os.environ.get("BLUEFIELD_FAILURE_RUN_ID", "")
    if not RUN_RE.fullmatch(run_id):
        raise RuntimeError(
            "BLUEFIELD_FAILURE_RUN_ID must be 8-40 lowercase "
            "letters/digits/hyphens"
        )
    return {
        "run_id": run_id,
        "poison_topic": f"shadow-bluefield-failure-poison-{run_id}",
        "poison_group": f"edrxdr-shadow-bluefield-failure-poison-{run_id}",
        "poison_index": f"shadow-bluefield-failure-poison-{run_id}",
        "osfail_topic": f"shadow-bluefield-failure-osfail-{run_id}",
        "osfail_group": f"edrxdr-shadow-bluefield-failure-osfail-{run_id}",
        "osfail_index": f"shadow-bluefield-failure-osfail-{run_id}",
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
        raise RuntimeError("OpenSearch endpoint outside failure-test allowlist")
    req = Request(
        OS_URL + path,
        data=None if body is None else encode(body),
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urlopen(req, timeout=15) as response:
        if response.length == 0:
            return response.status, {}
        return response.status, json.load(response)


def good_mapping():
    return {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
        },
        "mappings": {
            "dynamic": "strict",
            "properties": {
                "run_id": {"type": "keyword"},
                "scenario": {"type": "keyword"},
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


def deliberately_bad_mapping():
    mapping = good_mapping()
    # The document always contains rx_bytes. Omitting it from a strict
    # mapping causes an isolated mapper_parsing_exception without touching
    # the shared/replay OpenSearch service itself.
    del mapping["mappings"]["properties"]["rx_bytes"]
    return mapping


def topic_bounds(topic):
    from confluent_kafka import Consumer, TopicPartition

    client = Consumer(
        {
            "bootstrap.servers": TARGET,
            "group.id": "edrxdr-bluefield-failure-inspect",
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


def safe_doc(run_id, scenario, topic, message):
    value = message.value()
    row = validate_review(strict_json(value))
    digest = hashlib.sha256(value).hexdigest()
    identity = [
        run_id,
        scenario,
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
        "scenario": scenario,
        "processing_mode": "shadow_failure_test",
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


def preflight():
    r = resources()
    values, rows = source_values()
    poisoned_value(values[1])
    meta = broker_metadata()
    _, health = request(r["poison_index"], "/_cluster/health")
    if health.get("timed_out") or health.get("status") == "red":
        raise RuntimeError("Replay OpenSearch unavailable")
    if rows[0]["carrier"] is not None or rows[0]["rx_bytes"] != 0:
        raise RuntimeError("Pinned first-row semantics changed")
    report(
        "bluefield_failure_preflight",
        status="PASS",
        run_id=r["run_id"],
        source_records=6,
        source_sha256=REVIEW_NORMALIZED_SHA256,
        replay_cluster_id=meta.cluster_id,
        opensearch_status=health.get("status"),
        poison_fixture_rejected=True,
        live_source_used=False,
        gpu_used=False,
        automated_response_allowed=False,
    )


def setup():
    require_enabled()
    r = resources()
    meta = broker_metadata()

    for topic in (r["poison_topic"], r["osfail_topic"]):
        if topic in meta.topics:
            raise RuntimeError(
                f"Isolated topic already exists; choose a new run ID: {topic}"
            )
    for index in (r["poison_index"], r["osfail_index"]):
        if count_docs(index) is not None:
            raise RuntimeError(
                f"Isolated index already exists; choose a new run ID: {index}"
            )

    from confluent_kafka.admin import AdminClient

    admin = AdminClient({"bootstrap.servers": TARGET})
    create_topic(admin, r["poison_topic"])
    create_topic(admin, r["osfail_topic"])
    create_index(r["poison_index"], good_mapping())
    create_index(r["osfail_index"], deliberately_bad_mapping())

    broker_metadata((r["poison_topic"], r["osfail_topic"]))

    if topic_bounds(r["poison_topic"]) != (0, 0):
        raise RuntimeError("Poison topic not empty after setup")
    if topic_bounds(r["osfail_topic"]) != (0, 0):
        raise RuntimeError("OS-failure topic not empty after setup")
    if count_docs(r["poison_index"]) != 0:
        raise RuntimeError("Poison index not empty after setup")
    if count_docs(r["osfail_index"]) != 0:
        raise RuntimeError("OS-failure index not empty after setup")
    if committed_offset(r["poison_topic"], r["poison_group"]) is not None:
        raise RuntimeError("Poison group unexpectedly has committed state")
    if committed_offset(r["osfail_topic"], r["osfail_group"]) is not None:
        raise RuntimeError("OS-failure group unexpectedly has committed state")

    report(
        "bluefield_failure_setup",
        status="PASS",
        run_id=r["run_id"],
        poison_topic=r["poison_topic"],
        poison_index=r["poison_index"],
        osfail_topic=r["osfail_topic"],
        osfail_index=r["osfail_index"],
    )


def publish():
    require_enabled()
    r = resources()
    broker_metadata((r["poison_topic"], r["osfail_topic"]))
    values, _ = source_values()

    if topic_bounds(r["poison_topic"]) != (0, 0):
        raise RuntimeError("Poison topic must be empty before publish")
    if topic_bounds(r["osfail_topic"]) != (0, 0):
        raise RuntimeError("OS-failure topic must be empty before publish")

    poison_values = [values[0], poisoned_value(values[1]), values[2]]
    osfail_values = [values[0]]

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

    for topic, items in (
        (r["poison_topic"], poison_values),
        (r["osfail_topic"], osfail_values),
    ):
        for value in items:
            producer.produce(
                topic,
                partition=0,
                key=hashlib.sha256(value).hexdigest().encode("ascii"),
                value=value,
                on_delivery=delivered,
            )

    remaining = producer.flush(35)
    if remaining or failures:
        raise RuntimeError("Failure-test publish acknowledgement failed")

    if topic_bounds(r["poison_topic"]) != (0, 3):
        raise RuntimeError("Expected three poison-scenario records")
    if topic_bounds(r["osfail_topic"]) != (0, 1):
        raise RuntimeError("Expected one OS-failure record")

    report(
        "bluefield_failure_publish",
        status="PASS",
        run_id=r["run_id"],
        poison_records=3,
        osfail_records=1,
    )


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
    start = low if saved == OFFSET_INVALID else saved
    client.assign([TopicPartition(topic, 0, start)])
    deadline = time.monotonic() + 15
    message = None
    while message is None and time.monotonic() < deadline:
        current = client.poll(1)
        if current is None:
            continue
        if current.error():
            client.close()
            raise RuntimeError("Failure-test Kafka poll failed")
        message = current
    if message is None:
        client.close()
        raise RuntimeError("Failure-test Kafka poll timed out")
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
        raise RuntimeError("Failure-test Kafka commit failed")


def poison_first():
    require_enabled()
    r = resources()
    broker_metadata((r["poison_topic"],))
    client, message, start, high = poll_at_commit(
        r["poison_topic"], r["poison_group"]
    )
    try:
        if (start, high, message.offset()) != (0, 3, 0):
            raise RuntimeError("Poison phase expected first record at offset 0")
        doc_id, doc = safe_doc(
            r["run_id"], "poison", r["poison_topic"], message
        )
        status, reply = request(
            r["poison_index"],
            f"/{r['poison_index']}/_doc/{doc_id}?refresh=wait_for",
            doc,
            "PUT",
        )
        shards = reply.get("_shards") if isinstance(reply, dict) else None
        if (
            status not in (200, 201)
            or reply.get("_id") != doc_id
            or reply.get("_index") != r["poison_index"]
            or not isinstance(shards, dict)
            or shards.get("failed") != 0
            or type(shards.get("successful")) is not int
            or shards["successful"] < 1
        ):
            raise RuntimeError("Poison phase first OpenSearch ACK failed")
        commit_after_ack(client, message)
    finally:
        client.close()

    if committed_offset(r["poison_topic"], r["poison_group"]) != 1:
        raise RuntimeError("Poison group did not commit exactly offset 1")
    if count_docs(r["poison_index"]) != 1:
        raise RuntimeError("Poison index should contain exactly one document")

    report(
        "bluefield_failure_poison_first",
        status="PASS",
        start_offset=0,
        committed_offset=1,
        log_end_offset=3,
        lag=2,
        docs=1,
    )


def poison_attempt(kind):
    require_enabled()
    r = resources()
    broker_metadata((r["poison_topic"],))
    client, message, start, high = poll_at_commit(
        r["poison_topic"], r["poison_group"]
    )
    try:
        if (start, high, message.offset()) != (1, 3, 1):
            raise RuntimeError(
                "Poison retry must remain pinned at source offset 1"
            )
        try:
            safe_doc(
                r["run_id"], "poison", r["poison_topic"], message
            )
        except ValueError:
            pass
        else:
            raise RuntimeError("Poison record unexpectedly passed validation")
        # Deliberately no commit after validation failure.
    finally:
        client.close()

    offset = committed_offset(r["poison_topic"], r["poison_group"])
    docs = count_docs(r["poison_index"])
    if offset != 1 or docs != 1:
        raise RuntimeError(
            "Poison validation failure advanced offset or wrote a document"
        )

    report(
        "bluefield_failure_poison_attempt",
        status="PASS",
        attempt=kind,
        expected_failure="strict_validation",
        source_offset=1,
        committed_offset=offset,
        log_end_offset=3,
        lag=2,
        docs=docs,
        third_record_not_processed=True,
    )


def poison_attempt1():
    poison_attempt("first_process")


def poison_retry():
    poison_attempt("fresh_process_retry")


def poison_verify():
    r = resources()
    broker_metadata((r["poison_topic"],))
    offset = committed_offset(r["poison_topic"], r["poison_group"])
    docs = count_docs(r["poison_index"])
    if offset != 1 or docs != 1 or topic_bounds(r["poison_topic"]) != (0, 3):
        raise RuntimeError("Poison fail-closed state changed")
    report(
        "bluefield_failure_poison_verify",
        status="PASS",
        committed_offset=1,
        log_end_offset=3,
        lag=2,
        docs=1,
        poison_offset=1,
        retry_still_pinned=True,
        later_valid_record_not_skipped=True,
    )


def osfail_attempt():
    require_enabled()
    r = resources()
    broker_metadata((r["osfail_topic"],))
    client, message, start, high = poll_at_commit(
        r["osfail_topic"], r["osfail_group"]
    )
    try:
        if (start, high, message.offset()) != (0, 1, 0):
            raise RuntimeError("OS-failure phase expected offset 0")
        doc_id, doc = safe_doc(
            r["run_id"], "osfail", r["osfail_topic"], message
        )
        try:
            request(
                r["osfail_index"],
                f"/{r['osfail_index']}/_doc/{doc_id}?refresh=wait_for",
                doc,
                "PUT",
            )
        except HTTPError as error:
            if error.code not in (400, 409):
                raise
        else:
            raise RuntimeError(
                "Intentionally incompatible OpenSearch mapping did not reject"
            )
        # Deliberately no commit after OpenSearch rejection.
    finally:
        client.close()

    offset = committed_offset(r["osfail_topic"], r["osfail_group"])
    docs = count_docs(r["osfail_index"])
    if offset is not None or docs != 0:
        raise RuntimeError(
            "OpenSearch failure advanced Kafka offset or stored a document"
        )

    report(
        "bluefield_failure_osfail_attempt",
        status="PASS",
        expected_failure="opensearch_mapping_rejection",
        source_offset=0,
        committed_offset=None,
        log_end_offset=1,
        lag=1,
        docs=0,
    )


def osfail_repair():
    require_enabled()
    r = resources()
    if committed_offset(r["osfail_topic"], r["osfail_group"]) is not None:
        raise RuntimeError("Cannot repair after unexpected Kafka commit")
    if count_docs(r["osfail_index"]) != 0:
        raise RuntimeError("Cannot repair non-empty failure index")

    status, reply = request(
        r["osfail_index"],
        f"/{r['osfail_index']}",
        None,
        "DELETE",
    )
    if status not in (200, 202) or reply.get("acknowledged") is not True:
        raise RuntimeError("Isolated bad index deletion not acknowledged")

    create_index(r["osfail_index"], good_mapping())
    if count_docs(r["osfail_index"]) != 0:
        raise RuntimeError("Repaired isolated index is not empty")

    report(
        "bluefield_failure_osfail_repair",
        status="PASS",
        index=r["osfail_index"],
        committed_offset=None,
        docs=0,
    )


def osfail_resume():
    require_enabled()
    r = resources()
    broker_metadata((r["osfail_topic"],))
    client, message, start, high = poll_at_commit(
        r["osfail_topic"], r["osfail_group"]
    )
    try:
        if (start, high, message.offset()) != (0, 1, 0):
            raise RuntimeError(
                "OS-failure recovery must retry the same source offset 0"
            )
        doc_id, doc = safe_doc(
            r["run_id"], "osfail", r["osfail_topic"], message
        )
        status, reply = request(
            r["osfail_index"],
            f"/{r['osfail_index']}/_doc/{doc_id}?refresh=wait_for",
            doc,
            "PUT",
        )
        shards = reply.get("_shards") if isinstance(reply, dict) else None
        if (
            status not in (200, 201)
            or reply.get("_id") != doc_id
            or reply.get("_index") != r["osfail_index"]
            or not isinstance(shards, dict)
            or shards.get("failed") != 0
            or type(shards.get("successful")) is not int
            or shards["successful"] < 1
        ):
            raise RuntimeError("Repaired OpenSearch write not acknowledged")
        commit_after_ack(client, message)
    finally:
        client.close()

    offset = committed_offset(r["osfail_topic"], r["osfail_group"])
    docs = count_docs(r["osfail_index"])
    if offset != 1 or docs != 1:
        raise RuntimeError("OS-failure recovery did not finish at 1/1")

    report(
        "bluefield_failure_osfail_resume",
        status="PASS",
        retried_source_offset=0,
        committed_offset=1,
        log_end_offset=1,
        lag=0,
        docs=1,
    )


def osfail_verify():
    r = resources()
    broker_metadata((r["osfail_topic"],))
    if committed_offset(r["osfail_topic"], r["osfail_group"]) != 1:
        raise RuntimeError("OS-failure group did not finish at offset 1")
    if topic_bounds(r["osfail_topic"]) != (0, 1):
        raise RuntimeError("OS-failure topic bounds changed")

    _, result = request(
        r["osfail_index"],
        f"/{r['osfail_index']}/_search",
        {
            "size": 10,
            "track_total_hits": True,
            "query": {"term": {"run_id": r["run_id"]}},
        },
        "POST",
    )
    if (
        result.get("timed_out") is not False
        or result.get("_shards", {}).get("failed") != 0
        or result.get("hits", {}).get("total")
        != {"value": 1, "relation": "eq"}
    ):
        raise RuntimeError("Incomplete OS-failure recovery verification")

    row = result["hits"]["hits"][0]["_source"]
    if (
        row["carrier"] is not None
        or row["rx_bytes"] != 0
        or row["delta_rx_bytes"] is not None
        or row["historical"] is not True
        or row["production_ready"] is not False
        or row["automated_response_allowed"] is not False
    ):
        raise RuntimeError("OS-failure recovered document semantics changed")

    report(
        "bluefield_failure_osfail_verify",
        status="PASS",
        committed_offset=1,
        log_end_offset=1,
        lag=0,
        docs=1,
        carrier_null=1,
        counter_zero=1,
        first_sample_null=1,
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
            "poison-first",
            "poison-attempt",
            "poison-retry",
            "poison-verify",
            "osfail-attempt",
            "osfail-repair",
            "osfail-resume",
            "osfail-verify",
        ],
    )
    args = parser.parse_args()

    dispatch = {
        "preflight": preflight,
        "setup": setup,
        "publish": publish,
        "poison-first": poison_first,
        "poison-attempt": poison_attempt1,
        "poison-retry": poison_retry,
        "poison-verify": poison_verify,
        "osfail-attempt": osfail_attempt,
        "osfail-repair": osfail_repair,
        "osfail-resume": osfail_resume,
        "osfail-verify": osfail_verify,
    }

    try:
        dispatch[args.action]()
    except BaseException as error:
        frames = traceback.extract_tb(error.__traceback__)
        report(
            "bluefield_failure_failed",
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
