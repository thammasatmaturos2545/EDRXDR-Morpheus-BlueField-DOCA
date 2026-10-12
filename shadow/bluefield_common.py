"""Strict contracts for a bounded, archived BlueField shadow pilot.

This module has no Kafka/OpenSearch side effects.  It deliberately does not
share the Wazuh shadow occurrence contract because BlueField interface
telemetry is a different schema.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timezone

INPUT_TOPIC = "shadow-bluefield-input-v1"
INDEX = "shadow-bluefield-v1"
INDEX_GROUP = "edrxdr-shadow-bluefield-index-v1"

TARGET = "kafka:29092"
EXPECTED_CLUSTER_ID = "MkU3OEVBNTcwNTJENDM2Qk"

REPLAY_TOPICS = {
    "replay-wazuh-alerts",
    "replay-morpheus-input",
    "replay-morpheus-output",
    "replay-behavioral-input",
    "replay-behavioral-output",
}
FORBIDDEN_LIVE_TOPICS = {
    "bluefield-events",
    "wazuh-alerts",
    "morpheus-input",
    "morpheus-output",
}

REVIEW_SCHEMA = "bluefield-normalized-review-1"
SHADOW_SCHEMA = "shadow-bluefield-1"
REVIEW_NORMALIZED_SHA256 = (
    "868fb94d8cbf982084b99a3794622d801af15dd92110dd2109782c158e14d3f1"
)

COUNTERS = (
    "rx_packets",
    "tx_packets",
    "rx_bytes",
    "tx_bytes",
    "rx_errors",
    "tx_errors",
)
STATES = {
    "unknown",
    "notpresent",
    "down",
    "lowerlayerdown",
    "testing",
    "dormant",
    "up",
}
DELTA_STATES = {
    "first_sample",
    "interface_changed",
    "sample_gap",
    "unavailable",
    "baseline_unavailable",
    "counter_decreased",
    "computed",
}

REVIEW_FIELDS = {
    "schema_version",
    "processing_mode",
    "production_ready",
    "capture_scope",
    "timestamp",
    "event_type",
    "source_type",
    "measurement_scope",
    "ibdev",
    "interface",
    "operstate",
    "carrier",
    "read_errors",
    *COUNTERS,
    *("delta_" + c for c in COUNTERS),
    "delta_status",
    "sample_interval_seconds",
    "raw_event",
}

SHADOW_FIELDS = {
    "schema_version",
    "processing_mode",
    "evidence_mode",
    "historical",
    "production_ready",
    "automated_response_allowed",
    "source_type",
    "measurement_scope",
    "sample_uid",
    "input_sha256",
    "capture_scope_sha256",
    "timestamp",
    "ingested_at_utc",
    "source",
    "ibdev",
    "interface",
    "operstate",
    "carrier",
    "read_errors",
    *COUNTERS,
    *("delta_" + c for c in COUNTERS),
    "delta_status",
    "sample_interval_seconds",
}

HASH_RE = re.compile(r"[0-9a-f]{64}")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def encode(value) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


def strict_json(value):
    def reject(_):
        raise ValueError("Non-finite JSON forbidden")

    if isinstance(value, bytes):
        value = value.decode("utf-8")
    return json.loads(value, parse_constant=reject)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _timestamp(value) -> None:
    if not isinstance(value, str):
        raise ValueError("Timestamp required")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamp timezone required")


def _uint_or_null(value, field: str) -> None:
    if value is not None and (
        type(value) is not int or not 0 <= value <= 2**64 - 1
    ):
        raise ValueError(f"Invalid unsigned value: {field}")


def _measurements(row) -> None:
    if row["source_type"] != "bluefield":
        raise ValueError("Unexpected source type")
    if row["measurement_scope"] != "host_interface_counters":
        raise ValueError("Unexpected measurement scope")

    _timestamp(row["timestamp"])

    for field in ("ibdev",):
        if not isinstance(row[field], str) or not row[field] or len(row[field]) > 255:
            raise ValueError(f"Invalid {field}")

    interface = row["interface"]
    if interface is not None and (
        not isinstance(interface, str)
        or not interface
        or len(interface) > 255
        or "/" in interface
    ):
        raise ValueError("Invalid interface")

    operstate = row["operstate"]
    if operstate is not None and operstate not in STATES:
        raise ValueError("Invalid operstate")

    carrier = row["carrier"]
    if carrier is not None and (
        type(carrier) is not int or carrier not in (0, 1)
    ):
        raise ValueError("Invalid carrier")

    errors = row["read_errors"]
    if not isinstance(errors, dict) or any(
        not isinstance(k, str) or not isinstance(v, str) or not v
        for k, v in errors.items()
    ):
        raise ValueError("Invalid read_errors")

    allowed_error_fields = {"interface", "operstate", "carrier", *COUNTERS}
    if set(errors) - allowed_error_fields:
        raise ValueError("Unexpected read_errors field")

    for field in COUNTERS:
        _uint_or_null(row[field], field)

    status = row["delta_status"]
    if not isinstance(status, dict) or set(status) != set(COUNTERS):
        raise ValueError("Invalid delta_status")

    for field in COUNTERS:
        state = status[field]
        if state not in DELTA_STATES:
            raise ValueError("Invalid delta state")
        delta = row["delta_" + field]
        if state == "computed":
            if type(delta) is not int or not 0 <= delta <= 2**64 - 1:
                raise ValueError("Computed delta must be unsigned integer")
        elif delta is not None:
            raise ValueError("Unscored delta must remain null")

    interval = row["sample_interval_seconds"]
    if interval is not None and (
        type(interval) not in (int, float)
        or isinstance(interval, bool)
        or not math.isfinite(interval)
        or interval <= 0
    ):
        raise ValueError("Invalid sample interval")

    if interface is None and any(
        row[k] is not None for k in ("operstate", "carrier", *COUNTERS)
    ):
        raise ValueError("Unmapped interface cannot have readings")


def validate_review(row):
    if not isinstance(row, dict) or set(row) != REVIEW_FIELDS:
        raise ValueError("Unexpected/missing review fields")
    if row["schema_version"] != REVIEW_SCHEMA:
        raise ValueError("Unexpected review schema")
    if row["processing_mode"] != "offline_review":
        raise ValueError("Review row is not offline_review")
    if row["production_ready"] is not False:
        raise ValueError("Review row cannot be production ready")
    if not isinstance(row["capture_scope"], str) or not row["capture_scope"].strip():
        raise ValueError("Capture scope required")
    if row["event_type"] != "network_telemetry":
        raise ValueError("Unexpected event type")
    if not isinstance(row["raw_event"], dict):
        raise ValueError("raw_event required in archived review input")
    _measurements(row)
    return row


def _sample_uid(row, input_sha256: str) -> str:
    identity = [
        row["timestamp"],
        row["ibdev"],
        row["interface"],
        input_sha256,
    ]
    return hashlib.sha256(json.dumps(identity).encode("utf-8")).hexdigest()


def to_shadow(row, source, input_bytes: bytes, ingested_at_utc: str | None = None):
    validate_review(row)
    if not isinstance(source, dict) or set(source) != {
        "cluster_id",
        "topic",
        "partition",
        "offset",
    }:
        raise ValueError("Invalid Kafka source")
    if source["cluster_id"] != EXPECTED_CLUSTER_ID:
        raise ValueError("Unexpected replay cluster ID")
    if source["topic"] != INPUT_TOPIC:
        raise ValueError("Unexpected BlueField shadow topic")
    if type(source["partition"]) is not int or source["partition"] < 0:
        raise ValueError("Invalid source partition")
    if type(source["offset"]) is not int or source["offset"] < 0:
        raise ValueError("Invalid source offset")

    input_sha256 = sha256_bytes(input_bytes)
    result = {
        "schema_version": SHADOW_SCHEMA,
        "processing_mode": "shadow",
        "evidence_mode": "archived_normalized_replay",
        "historical": True,
        "production_ready": False,
        "automated_response_allowed": False,
        "source_type": "bluefield",
        "measurement_scope": row["measurement_scope"],
        "sample_uid": _sample_uid(row, input_sha256),
        "input_sha256": input_sha256,
        "capture_scope_sha256": sha256_bytes(
            row["capture_scope"].encode("utf-8")
        ),
        "timestamp": row["timestamp"],
        "ingested_at_utc": ingested_at_utc or utc_now(),
        "source": source,
        "ibdev": row["ibdev"],
        "interface": row["interface"],
        "operstate": row["operstate"],
        "carrier": row["carrier"],
        "read_errors": row["read_errors"],
        **{field: row[field] for field in COUNTERS},
        **{("delta_" + field): row["delta_" + field] for field in COUNTERS},
        "delta_status": row["delta_status"],
        "sample_interval_seconds": row["sample_interval_seconds"],
    }
    validate_shadow(result)
    return result


def validate_shadow(row):
    if not isinstance(row, dict) or set(row) != SHADOW_FIELDS:
        raise ValueError("Unexpected/missing BlueField shadow fields")
    if row["schema_version"] != SHADOW_SCHEMA:
        raise ValueError("Unexpected BlueField shadow schema")
    if row["processing_mode"] != "shadow":
        raise ValueError("Expected shadow processing mode")
    if row["evidence_mode"] != "archived_normalized_replay":
        raise ValueError("Unexpected evidence mode")
    if row["historical"] is not True:
        raise ValueError("Archived shadow sample must remain historical")
    if row["production_ready"] is not False:
        raise ValueError("Production-ready flag forbidden")
    if row["automated_response_allowed"] is not False:
        raise ValueError("Automated response forbidden")
    for field in ("sample_uid", "input_sha256", "capture_scope_sha256"):
        if not isinstance(row[field], str) or not HASH_RE.fullmatch(row[field]):
            raise ValueError(f"Invalid hash field: {field}")
    _timestamp(row["ingested_at_utc"])
    source = row["source"]
    if not isinstance(source, dict) or set(source) != {
        "cluster_id",
        "topic",
        "partition",
        "offset",
    }:
        raise ValueError("Invalid source coordinates")
    if source["cluster_id"] != EXPECTED_CLUSTER_ID:
        raise ValueError("Unexpected replay cluster")
    if source["topic"] != INPUT_TOPIC:
        raise ValueError("Unexpected input topic")
    for field in ("partition", "offset"):
        if type(source[field]) is not int or source[field] < 0:
            raise ValueError("Invalid source coordinate")
    _measurements(row)
    return row


def document_id(row) -> str:
    validate_shadow(row)
    identity = [
        row["schema_version"],
        row["sample_uid"],
        row["input_sha256"],
    ]
    return hashlib.sha256(json.dumps(identity).encode("utf-8")).hexdigest()


def index_mapping():
    properties = {
        "schema_version": {"type": "keyword"},
        "processing_mode": {"type": "keyword"},
        "evidence_mode": {"type": "keyword"},
        "historical": {"type": "boolean"},
        "production_ready": {"type": "boolean"},
        "automated_response_allowed": {"type": "boolean"},
        "source_type": {"type": "keyword"},
        "measurement_scope": {"type": "keyword"},
        "sample_uid": {"type": "keyword"},
        "input_sha256": {"type": "keyword"},
        "capture_scope_sha256": {"type": "keyword"},
        "timestamp": {"type": "date"},
        "ingested_at_utc": {"type": "date"},
        "ibdev": {"type": "keyword"},
        "interface": {"type": "keyword"},
        "operstate": {"type": "keyword"},
        "carrier": {"type": "byte", "coerce": False},
        "sample_interval_seconds": {"type": "double", "coerce": False},
        "read_errors": {"type": "object", "enabled": False},
        "source": {
            "type": "object",
            "dynamic": "strict",
            "properties": {
                "cluster_id": {"type": "keyword"},
                "topic": {"type": "keyword"},
                "partition": {"type": "integer"},
                "offset": {"type": "long"},
            },
        },
        "delta_status": {
            "type": "object",
            "dynamic": "strict",
            "properties": {
                field: {"type": "keyword"} for field in COUNTERS
            },
        },
    }
    for field in COUNTERS:
        properties[field] = {"type": "unsigned_long"}
        properties["delta_" + field] = {"type": "unsigned_long"}
    return {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
        },
        "mappings": {
            "dynamic": "strict",
            "properties": properties,
        },
    }
