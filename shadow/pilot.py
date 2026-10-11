"""Explicit finite pilot commands; no daemon, no production writes, no training."""
import argparse
import json
import os
import time
import traceback
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from common import (INDEXES, OUTPUTS, RAW_TOPIC, TOPICS, SOURCE_TOPIC, encode,
                    envelope, publish_then_commit, strict_json, unpack, digest)
import runtime as rt

OS_URL = "http://opensearch:9200"


def request(path, body=None, method="GET"):
    req = Request(OS_URL + path, data=None if body is None else encode(body),
                  method=method, headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=15) as response:
        return response.status, json.load(response)


def provision():
    """Only named shadow topics/indexes on the experimental backend."""
    from confluent_kafka.admin import AdminClient, NewTopic
    from confluent_kafka import KafkaException, KafkaError
    meta = rt.metadata(rt.TARGET)
    if {(b.host, b.port) for b in meta.brokers.values()} != {("kafka", 29092)}:
        raise ValueError("Unexpected experimental broker")
    admin = AdminClient({"bootstrap.servers": rt.TARGET})
    for topic in sorted(TOPICS):
        if topic in meta.topics:
            if len(meta.topics[topic].partitions) != 1:
                raise ValueError("Pilot requires one destination partition")
            continue
        future = admin.create_topics([NewTopic(topic, num_partitions=1, replication_factor=1,
                                    config={"retention.ms": "86400000", "retention.bytes": "67108864"})],
                                    request_timeout=15)[topic]
        try:
            future.result()
        except KafkaException as error:
            if error.args[0].code() != KafkaError.TOPIC_ALREADY_EXISTS:
                raise
    for index in INDEXES.values():
        try:
            request("/" + index)
        except HTTPError as error:
            if error.code != 404:
                raise
            status, reply = request("/" + index, {
                "settings": {"number_of_shards": 1, "number_of_replicas": 0},
                "mappings": {"properties": {
                    "event_uid": {"type": "keyword"},
                    "processing_mode": {"type": "keyword"},
                    "schema_version": {"type": "keyword"},
                    "scored_at_utc": {"type": "date"},
                    "captured_at_utc": {"type": "date"},
                    "capture_to_score_ms": {"type": "double"},
                    "wazuh_rule_id": {"type": "keyword"},
                    "wazuh_rule_level": {"type": "integer"},
                    "analysis_state": {"type": "keyword"},
                    "routing_status": {"type": "keyword"},
                    "high_severity_score": {"type": "double"},
                    "ae_ratio": {"type": "double"},
                    "ae_reconstruction_error": {"type": "double"},
                    "ae_threshold": {"type": "double"},
                }},
            }, "PUT")
            if not reply.get("acknowledged"):
                raise RuntimeError("Index creation not acknowledged")
    rt.report("provision", topics=sorted(TOPICS), indexes=list(INDEXES.values()))


def preflight():
    from scoring import CHECKPOINT, PARITY
    source, target = rt.check_clusters()
    # Read files and hashes, never load pickle models or use a GPU in preflight.
    for file in (CHECKPOINT / "RUN_COMPLETE", PARITY):
        if not file.is_file():
            raise ValueError("Missing model artifact")
    model_root = Path("/models/morpheus-behavioral-v1-4-dev")
    manifest = strict_json((model_root / "runtime_manifest.json").read_bytes())
    if manifest["production_ready"] is not False or manifest["automated_response_allowed"] is not False:
        raise ValueError("Behavioral safety flags invalid")
    for cfg in manifest["runtime_cohorts"]:
        if not cfg.get("runtime_enabled"):
            continue
        path = (model_root / "models" / cfg["model_file"]).resolve()
        if not path.is_relative_to(model_root.resolve()) or digest(path) != cfg["model_sha256"]:
            raise ValueError("Behavioral model file/hash mismatch")
    _, health = request("/_cluster/health")
    if health["status"] == "red" or health.get("timed_out"):
        raise RuntimeError("Experimental OpenSearch unhealthy")
    rt.report("preflight", status="PASS", source_cluster_id=source.cluster_id,
              target_cluster_id=target.cluster_id, opensearch_status=health["status"],
              source_endpoint=rt.SOURCE, target_endpoint=rt.TARGET,
              deployment_check="pinned_listeners_and_topic_signatures",
              shared_cluster_id=source.cluster_id == target.cluster_id,
              shadow_topics_present=sorted(TOPICS & set(target.topics)),
              behavioral_manifest_sha256=digest(model_root / "runtime_manifest.json"),
              gpu_used=False, offsets_changed=False)


def capture(args):
    rt.check_clusters()
    producer = rt.producer()  # Verify target before touching even shadow source offsets.
    consumer, cluster = rt.consumer("capture", SOURCE_TOPIC, capture=True)
    count = 0
    try:
        for message in rt.collect(consumer, args.limit, args.seconds):
            timestamp = message.timestamp()[1]
            item = envelope(message.value(), cluster, message.topic(), message.partition(),
                            message.offset(), timestamp if timestamp >= 0 else None)
            publish_then_commit(producer, RAW_TOPIC, item["event_uid"].encode(), item,
                                lambda: rt.commit(consumer, message))
            count += 1
            time.sleep(0.1)  # At most 10 publishes/second in this small pilot.
        rt.report("capture_complete", copied=count)
    finally:
        consumer.close()


def score(args):
    from validation import validate
    import scoring
    if args.kind == "severity" and os.environ.get("SHADOW_GPU_ALLOWED") != "1":
        raise RuntimeError("GPU run requires an active reservation and SHADOW_GPU_ALLOWED=1")
    producer = rt.producer()
    consumer, _ = rt.consumer(args.kind, RAW_TOPIC)
    try:
        rows = rt.collect(consumer, args.limit, args.seconds)
        if not rows:
            rt.report("score_complete", model=args.kind, scored=0)
            return
        envelopes = [strict_json(row.value()) for row in rows]
        raws = [unpack(item, row.key()) for item, row in zip(envelopes, rows)]
        started = time.monotonic()
        outputs = getattr(scoring, args.kind)(envelopes, raws)
        if len(outputs) != len(rows):
            raise RuntimeError("Output count mismatch")
        # Validate the complete batch before publishing any output.
        for output, row in zip(outputs, rows):
            validate(args.kind, output, row.key())
        for output, row in zip(outputs, rows):
            publish_then_commit(producer, OUTPUTS[args.kind], row.key(), output,
                                lambda: rt.commit(consumer, row))
        rt.report("score_complete", model=args.kind, scored=len(rows),
                  batch_seconds=time.monotonic() - started,
                  ae_scored=sum(o.get("ae_scored", False) for o in outputs) if args.kind == "behavioral" else None,
                  novelty=sum(o.get("semantic_novelty", False) for o in outputs) if args.kind == "behavioral" else None,
                  false_positive_candidates=sum(o.get("false_positive_candidate") is True for o in outputs) if args.kind == "severity" else None)
    finally:
        consumer.close()


def index(args):
    from validation import validate
    destination = INDEXES[args.kind]
    request("/" + destination)  # Missing index is a failure, not implicit creation.
    consumer, _ = rt.consumer("index-" + args.kind, OUTPUTS[args.kind])
    try:
        rows = rt.collect(consumer, args.limit, args.seconds)
        for row in rows:
            event = strict_json(row.value())
            document = validate(args.kind, event, row.key())
            status, result = request(f"/{destination}/_doc/{document}?refresh=wait_for", event, "PUT")
            shards = result.get("_shards") if isinstance(result, dict) else None
            if (status not in (200, 201) or not isinstance(result, dict)
                    or result.get("_id") != document or result.get("_index") != destination
                    or not isinstance(shards, dict) or type(shards.get("failed")) is not int
                    or shards["failed"] != 0 or type(shards.get("successful")) is not int
                    or shards["successful"] < 1):
                raise RuntimeError("Index acknowledgement failed")
            rt.commit(consumer, row)
        rt.report("index_complete", index=destination, processed=len(rows))
    finally:
        consumer.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["preflight", "provision", "capture", "score", "index"])
    parser.add_argument("--kind", choices=["severity", "behavioral"])
    parser.add_argument("--limit", type=int, default=32)
    parser.add_argument("--seconds", type=int, default=15)
    args = parser.parse_args()
    if args.action in {"score", "index"} and not args.kind:
        parser.error("--kind required")
    if not 1 <= args.limit <= 100 or not 1 <= args.seconds <= 120:
        parser.error("Allowed: --limit 1..100, --seconds 1..120")
    rt.verify_sources()
    if args.action != "preflight":
        rt.require_enabled()
    role = args.action + ("-" + args.kind if args.kind else "")
    with rt.lock(role):
        try:
            if args.action in {"preflight", "provision"}:
                globals()[args.action]()
            else:
                globals()[args.action](args)
        except BaseException as error:
            # Never print exception text that could contain raw event content.
            frames = traceback.extract_tb(error.__traceback__)
            rt.report("failed", role=role, error_type=type(error).__name__,
                      locations=[dict(file=Path(f.filename).name, line=f.lineno) for f in frames])
            raise SystemExit(1) from None


if __name__ == "__main__":
    main()
