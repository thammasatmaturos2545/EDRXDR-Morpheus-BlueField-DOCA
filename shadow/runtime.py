"""Bounded Kafka operations. Source is consumed only; all producers use target."""
import contextlib
import json
import os
import time
from pathlib import Path

from common import GROUPS, RAW_TOPIC, SOURCE_TOPIC, TOPICS, digest, utc_now

SOURCE = "172.16.30.147:9092"
TARGET = "kafka:29092"
STORE = Path("/shadow-state")
EXPECTED_CLUSTER_ID = "MkU3OEVBNTcwNTJENDM2Qk"
LIVE_TOPICS = {"bluefield-events", "wazuh-alerts", "morpheus-input", "morpheus-output"}
REPLAY_TOPICS = {"replay-wazuh-alerts", "replay-morpheus-input", "replay-morpheus-output",
                 "replay-behavioral-input", "replay-behavioral-output"}


def validate_backend(broker, result):
    """Deployment checks for the two independently inspected brokers.

    Both were provisioned with the same cluster ID. That ID is pinned but is
    not a unique deployment identifier. Endpoint AND topic signature must match.
    Docker/storage separation was inspected on the VM; metadata is not an ACL.
    """
    if broker == SOURCE:
        endpoints, required, forbidden = {("172.16.30.147", 9092)}, LIVE_TOPICS, REPLAY_TOPICS | TOPICS
    elif broker == TARGET:
        endpoints, required, forbidden = {("kafka", 29092)}, REPLAY_TOPICS, LIVE_TOPICS
    else:
        raise RuntimeError("Unreviewed Kafka endpoint")
    if result.cluster_id != EXPECTED_CLUSTER_ID:
        raise RuntimeError("Unexpected Kafka cluster ID")
    if {(b.host, b.port) for b in result.brokers.values()} != endpoints:
        raise RuntimeError("Unexpected advertised listener")
    if not required.issubset(result.topics) or forbidden.intersection(result.topics):
        raise RuntimeError("Kafka deployment topic signature mismatch")
    if any(result.topics[name].error for name in required):
        raise RuntimeError("Kafka deployment topic metadata unavailable")


def verify_sources():
    manifest = json.loads(Path("/shadow/source-lock.json").read_text())
    for relative, expected in manifest["sha256"].items():
        if digest(Path("/base") / relative) != expected:
            raise ValueError("Reviewed source changed: " + relative)


@contextlib.contextmanager
def lock(name):
    # All pilot containers share this volume. No parallel jobs for one role/group.
    import fcntl
    STORE.mkdir(exist_ok=True)
    with (STORE / (name + ".lock")).open("a") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def report(kind, **data):
    value = dict(kind=kind, time_utc=utc_now(), **data)
    with (STORE / "audit.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps(value), flush=True)


def require_enabled():
    if os.environ.get("SHADOW_RUN_ALLOWED") != "1":
        raise RuntimeError("Pilot disabled; set SHADOW_RUN_ALLOWED=1 explicitly")


def metadata(broker, needed=()):
    from confluent_kafka.admin import AdminClient
    # Do not name a missing topic in a metadata request (avoid auto-creation).
    result = AdminClient({"bootstrap.servers": broker,
                          "socket.timeout.ms": 10000}).list_topics(timeout=10)
    if not result.cluster_id:
        raise RuntimeError("Missing cluster identity")
    for name in needed:
        if name not in result.topics or result.topics[name].error:
            raise RuntimeError("Missing/unavailable topic: " + name)
    validate_backend(broker, result)
    return result


def check_clusters():
    source = metadata(SOURCE, [SOURCE_TOPIC])
    target = metadata(TARGET)
    validate_backend(SOURCE, source)
    validate_backend(TARGET, target)
    return source, target


def producer():
    from confluent_kafka import Producer
    metadata(TARGET, TOPICS)
    return Producer({"bootstrap.servers": TARGET, "enable.idempotence": True,
                     "acks": "all", "delivery.timeout.ms": 30000})


def consumer(role, topic, capture=False):
    from confluent_kafka import Consumer, TopicPartition, OFFSET_INVALID
    if role not in GROUPS or (capture and (role != "capture" or topic != SOURCE_TOPIC)):
        raise ValueError("Invalid consumer role")
    if not capture and topic not in TOPICS:
        raise ValueError("Input outside shadow allowlist")
    broker = SOURCE if capture else TARGET
    meta = metadata(broker, [topic])
    client = Consumer({"bootstrap.servers": broker, "group.id": GROUPS[role],
                       "enable.auto.commit": False, "enable.auto.offset.store": False,
                       "allow.auto.create.topics": False, "auto.offset.reset": "error"})
    try:
        parts = [TopicPartition(topic, p) for p in sorted(meta.topics[topic].partitions)]
        saved = client.committed(parts, timeout=10)
        starts = []
        for p in saved:
            if p.error:
                raise RuntimeError("Could not read offset")
            low, high = client.get_watermark_offsets(p, timeout=10, cached=False)
            if p.offset == OFFSET_INVALID:
                p.offset = high if capture else low
            elif not low <= p.offset <= high:
                raise RuntimeError("Offset outside retention; manual investigation required")
            starts.append(dict(partition=p.partition, offset=p.offset, low=low, high=high))
        client.assign(saved)
        # Persist the starting boundary even when no new live event arrives.
        # Only this pilot's group is changed, never a live group's offset.
        committed = client.commit(offsets=saved, asynchronous=False)
        if any(p.error for p in committed):
            raise RuntimeError("Could not persist starting boundary")
        report("start", role=role, cluster_id=meta.cluster_id, topic=topic, partitions=starts)
        return client, meta.cluster_id
    except BaseException:
        client.close()
        raise


def commit(client, message):
    from confluent_kafka import TopicPartition
    result = client.commit(offsets=[TopicPartition(message.topic(), message.partition(),
                                                 message.offset() + 1)], asynchronous=False)
    if any(p.error for p in result):
        raise RuntimeError("Input commit failed; duplicate delivery is possible")


def collect(client, limit, seconds):
    if not 1 <= limit <= 100 or not 1 <= seconds <= 120:
        raise ValueError("Pilot limit: 1..100 events, collection window 1..120 seconds")
    deadline = time.monotonic() + seconds
    rows = []
    while len(rows) < limit and time.monotonic() < deadline:
        message = client.poll(min(1, max(0, deadline - time.monotonic())))
        if message is None:
            continue
        if message.error():
            raise RuntimeError("Kafka poll error")
        if len(message.value() or b"") > 1024 * 1024:
            raise ValueError("Pilot event exceeds 1 MiB limit")
        rows.append(message)
    return rows
