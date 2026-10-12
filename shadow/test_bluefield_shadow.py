"""CPU-only tests for the archived BlueField shadow contract."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "shadow"))

import bluefield_common as common


FIXTURE = (
    ROOT
    / "experiments"
    / "bluefield-kafka-runs"
    / "20261012T141233Z-beaccd98dc"
    / "normalized.jsonl"
)


def rows():
    data = FIXTURE.read_bytes()
    if hashlib.sha256(data).hexdigest() != common.REVIEW_NORMALIZED_SHA256:
        raise RuntimeError("Fixture hash changed")
    return [
        common.validate_review(common.strict_json(line))
        for line in data.splitlines()
        if line.strip()
    ]


class BlueFieldShadowContract(unittest.TestCase):
    def test_fixture_semantics(self):
        items = rows()
        self.assertEqual(len(items), 6)
        self.assertEqual(sum(x["carrier"] is None for x in items), 6)
        self.assertEqual(sum(x["rx_bytes"] == 0 for x in items), 6)
        self.assertEqual(sum(x["delta_rx_bytes"] is None for x in items), 2)
        self.assertEqual(sum(x["delta_rx_bytes"] == 0 for x in items), 4)

    def test_shadow_projection_is_display_only_and_strips_private_fields(self):
        row = rows()[0]
        value = common.encode(row)
        source = {
            "cluster_id": common.EXPECTED_CLUSTER_ID,
            "topic": common.INPUT_TOPIC,
            "partition": 0,
            "offset": 0,
        }
        out = common.to_shadow(
            row,
            source,
            value,
            "2026-10-12T00:00:00+00:00",
        )
        self.assertEqual(out["processing_mode"], "shadow")
        self.assertTrue(out["historical"])
        self.assertFalse(out["production_ready"])
        self.assertFalse(out["automated_response_allowed"])
        self.assertIsNone(out["carrier"])
        self.assertEqual(out["rx_bytes"], 0)
        self.assertIsNone(out["delta_rx_bytes"])
        self.assertNotIn("raw_event", out)
        self.assertNotIn("capture_scope", out)

    def test_zero_delta_stays_zero(self):
        row = rows()[2]
        value = common.encode(row)
        out = common.to_shadow(
            row,
            {
                "cluster_id": common.EXPECTED_CLUSTER_ID,
                "topic": common.INPUT_TOPIC,
                "partition": 0,
                "offset": 2,
            },
            value,
            "2026-10-12T00:00:00+00:00",
        )
        self.assertEqual(out["delta_rx_bytes"], 0)
        self.assertEqual(out["sample_interval_seconds"], 2.0)

    def test_document_id_is_stable_across_ingestion_time(self):
        row = rows()[2]
        value = common.encode(row)
        source = {
            "cluster_id": common.EXPECTED_CLUSTER_ID,
            "topic": common.INPUT_TOPIC,
            "partition": 0,
            "offset": 2,
        }
        first = common.to_shadow(
            row, source, value, "2026-10-12T00:00:00+00:00"
        )
        second = common.to_shadow(
            row, source, value, "2026-10-13T00:00:00+00:00"
        )
        self.assertEqual(
            common.document_id(first),
            common.document_id(second),
        )

    def test_wrong_modes_and_safety_flags_fail_closed(self):
        row = rows()[0]
        for field, value in (
            ("processing_mode", "live"),
            ("production_ready", True),
            ("automated_response_allowed", True),
            ("historical", False),
        ):
            out = common.to_shadow(
                row,
                {
                    "cluster_id": common.EXPECTED_CLUSTER_ID,
                    "topic": common.INPUT_TOPIC,
                    "partition": 0,
                    "offset": 0,
                },
                common.encode(row),
                "2026-10-12T00:00:00+00:00",
            )
            out[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                common.validate_shadow(out)

    def test_wrong_topic_or_cluster_rejected(self):
        row = rows()[0]
        for patch in (
            {"topic": "bluefield-events"},
            {"cluster_id": "other"},
        ):
            source = {
                "cluster_id": common.EXPECTED_CLUSTER_ID,
                "topic": common.INPUT_TOPIC,
                "partition": 0,
                "offset": 0,
                **patch,
            }
            with self.assertRaises(ValueError):
                common.to_shadow(row, source, common.encode(row))

    def test_delta_state_cannot_rewrite_null_zero_meaning(self):
        base = rows()[0]
        bad = copy.deepcopy(base)
        bad["delta_rx_bytes"] = 0
        with self.assertRaises(ValueError):
            common.validate_review(bad)

        computed = copy.deepcopy(rows()[2])
        computed["delta_rx_bytes"] = None
        with self.assertRaises(ValueError):
            common.validate_review(computed)

    def test_mapping_is_strict_and_has_no_raw_event_field(self):
        mapping = common.index_mapping()
        self.assertEqual(mapping["mappings"]["dynamic"], "strict")
        props = mapping["mappings"]["properties"]
        self.assertNotIn("raw_event", props)
        self.assertNotIn("capture_scope", props)
        self.assertEqual(props["source"]["dynamic"], "strict")
        self.assertEqual(props["delta_status"]["dynamic"], "strict")


if __name__ == "__main__":
    unittest.main(verbosity=2)
