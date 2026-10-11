"""Contracts for a bounded, display-only shadow pilot. No external dependencies."""
import hashlib
import json
import math
from datetime import datetime, timezone

SOURCE_TOPIC = "wazuh-alerts"
RAW_TOPIC = "shadow-wazuh-raw-v1"
OUTPUTS = {"severity": "shadow-severity-output-v1", "behavioral": "shadow-behavioral-output-v1"}
INDEXES = {"severity": "shadow-severity-v1", "behavioral": "shadow-behavioral-v1"}
GROUPS = {"capture": "edrxdr-shadow-copy-v1", "severity": "edrxdr-shadow-severity-v1",
          "behavioral": "edrxdr-shadow-behavioral-v1",
          "index-severity": "edrxdr-shadow-index-severity-v1",
          "index-behavioral": "edrxdr-shadow-index-behavioral-v1"}
TOPICS = {RAW_TOPIC, *OUTPUTS.values()}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def encode(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")


def strict_json(value):
    def reject(_):
        raise ValueError("Non-finite JSON forbidden")
    return json.loads(value, parse_constant=reject)


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def uid(raw):
    identity = [raw["manager"]["name"], raw["agent"]["id"], raw["id"]]
    if any(type(v) not in (str, int) or not str(v).strip() for v in identity):
        raise ValueError("Invalid identity")
    # Byte-for-byte compatible with the archived replay UID contract.
    return hashlib.sha256(json.dumps([str(v) for v in identity]).encode()).hexdigest()


def envelope(value, cluster, topic, partition, offset, timestamp_ms):
    if topic != SOURCE_TOPIC or not cluster:
        raise ValueError("Unexpected source")
    raw = strict_json(value)
    event_uid = uid(raw)
    if not isinstance(raw.get("rule"), dict):
        raise ValueError("Expected Wazuh rule")
    # Preserve the raw JSON bytes as a string, including whitespace/number spelling.
    return dict(schema_version="shadow-raw-1", processing_mode="shadow",
                event_uid=event_uid, raw_json=value.decode("utf-8"),
                raw_sha256=hashlib.sha256(value).hexdigest(),
                captured_at_utc=utc_now(), source=dict(cluster_id=cluster, topic=topic,
                partition=partition, offset=offset, timestamp_ms=timestamp_ms))


def unpack(event, key):
    if event.get("schema_version") != "shadow-raw-1" or event.get("processing_mode") != "shadow":
        raise ValueError("Wrong raw schema/mode")
    value = event["raw_json"].encode("utf-8")
    if hashlib.sha256(value).hexdigest() != event["raw_sha256"]:
        raise ValueError("Raw payload hash mismatch")
    raw = strict_json(value)
    if uid(raw) != event["event_uid"] or key != event["event_uid"].encode():
        raise ValueError("UID/key mismatch")
    source = event["source"]
    if source["topic"] != SOURCE_TOPIC or not source["cluster_id"]:
        raise ValueError("Unexpected original source")
    if any(type(source[k]) is not int or source[k] < 0 for k in ("partition", "offset")):
        raise ValueError("Invalid original coordinates")
    return raw


def publish_then_commit(producer, topic, key, value, commit):
    if topic not in TOPICS:
        raise ValueError("Destination outside shadow allowlist")
    delivered = []
    producer.produce(topic, key=key, value=encode(value),
                     on_delivery=lambda error, msg: delivered.append(error))
    remaining = producer.flush(35)
    if remaining or len(delivered) != 1 or delivered[0] is not None:
        raise RuntimeError("Delivery not confirmed; input must not be committed")
    commit()


def latency_ms(captured, scored):
    result = (datetime.fromisoformat(scored) - datetime.fromisoformat(captured)).total_seconds() * 1000
    if not math.isfinite(result) or result < 0:
        raise ValueError("Invalid clock ordering")
    return result


def result_fields(envelope_row, kind):
    now = utc_now()
    return dict(schema_version=f"shadow-{kind}-1", processing_mode="shadow",
                event_uid=envelope_row["event_uid"], source_type="wazuh",
                source=envelope_row["source"], raw_sha256=envelope_row["raw_sha256"],
                captured_at_utc=envelope_row["captured_at_utc"], scored_at_utc=now,
                capture_to_score_ms=latency_ms(envelope_row["captured_at_utc"], now),
                production_ready=False, automated_response_allowed=False)
