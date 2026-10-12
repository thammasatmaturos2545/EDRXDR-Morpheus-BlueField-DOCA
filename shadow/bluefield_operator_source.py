"""Bounded source verification core. No Kafka adapter or replay capability.

The injected reader is trusted transport code, not an arbitrary plugin. Its calls
must obey the supplied timeout; this core cannot interrupt a blocking adapter.
"""
from copy import deepcopy
import time
import bluefield_operator_contract as c


def inspect_source(plan, envelope, evidence_id, reader, *, timeout_seconds=10,
                   clock=time.monotonic):
    """Read one exact record; return metadata only, never replay authorization.

    Reader interface: partitions(topic, remaining), watermarks(topic, partition,
    remaining), fetch_exact(topic, partition, offset, remaining), close().
    partitions returns None for missing topic, otherwise a set of integer IDs.
    fetch_exact returns None or {source: coordinates, value: original bytes}.
    Adapter must disable auto creation/commits, use no group and explicit seek.
    Caller owns reader lifecycle if input validation fails before any I/O.
    """
    plan, envelope = deepcopy(plan), deepcopy(envelope)
    c.validate_plan(plan, envelope, evidence_id)
    c.require(type(timeout_seconds) in (int, float) and
              0 < timeout_seconds <= 30, 'invalid_read_timeout')
    start = clock()
    deadline = start + timeout_seconds
    source = plan['source']

    def remaining():
        value = deadline - clock()
        c.require(0 < value <= timeout_seconds, 'source_read_timeout')
        return value

    def bounds():
        pair = reader.watermarks(source['topic'], source['partition'], remaining())
        remaining()
        c.require(type(pair) is tuple and len(pair) == 2 and
                  all(type(x) is int for x in pair) and
                  0 <= pair[0] <= pair[1] <= 2**63-1, 'invalid_watermarks')
        c.require(pair[0] <= source['offset'] < pair[1], 'source_unavailable')
        return pair

    try:
        parts = reader.partitions(source['topic'], remaining())
        remaining()
        c.require(parts is not None, 'source_topic_missing')
        c.require(type(parts) is set and all(type(x) is int and x >= 0 for x in parts),
                  'invalid_partition_metadata')
        c.require(source['partition'] in parts, 'source_partition_missing')
        low, high = bounds()
        record = reader.fetch_exact(source['topic'], source['partition'],
                                    source['offset'], remaining())
        remaining()
        c.require(record is not None, 'source_record_missing')
        c.exact(record, {'source', 'value'}, 'invalid_source_record')
        raw = c.verify_source(plan, record['source'], record['value'], low, high)
        # Retention/truncation can race with fetch: check again and fail closed.
        low, high = bounds()
        c.verify_source(plan, record['source'], raw, low, high)
        result = {'schema_version': 'bluefield-source-inspection-1',
                  'plan_sha256': plan['plan_sha256'], 'source': deepcopy(source),
                  'input_sha256': plan['input_sha256'], 'byte_count': len(raw),
                  'low_offset': low, 'high_offset': high,
                  'status': 'verified_at_read', 'replay_authorized': False,
                  'production_ready': False, 'automated_response_allowed': False}
    except c.Rejected:
        raise
    except Exception:
        raise c.Rejected('source_transport_failed') from None
    finally:
        try:
            reader.close()
        except Exception:
            raise c.Rejected('source_close_failed') from None
    return result
