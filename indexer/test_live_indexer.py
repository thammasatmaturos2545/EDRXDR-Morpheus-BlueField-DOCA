"""CPU-only contract tests for fail-closed live indexer."""

import copy
import importlib.util
from pathlib import Path
import unittest


SOURCE = (
    Path(__file__)
    .with_name("live_indexer.py")
)

spec = importlib.util.spec_from_file_location(
    "live_indexer_contract",
    SOURCE,
)

module = importlib.util.module_from_spec(
    spec
)

spec.loader.exec_module(module)


class LiveIndexerContract(unittest.TestCase):

    def event(self):
        uid = "a" * 64

        artifacts = {
            field:
                chr(
                    ord("b") + index
                ) * 64

            for index, field
            in enumerate(
                module.ARTIFACT_FIELDS
            )
        }

        return {
            "schema_version":
                "live-severity-1",

            "event_uid":
                uid,

            "source_type":
                "wazuh",

            "processing_mode":
                "live",

            "analysis_engine":
                "nvidia-morpheus-context-severity-v1",

            "model_name":
                (
                    "wazuh-severity-context-v2-balanced-"
                    "20261008T190719Z-1398863"
                ),

            "text_contract_version":
                "wazuh-context-v2-raw-1",

            "high_severity_score":
                0.75,

            "predicted_label":
                "high_severity",

            "threshold":
                0.5,

            "wazuh_rule_id":
                "60137",

            "wazuh_rule_level":
                5,

            "source_topic":
                "wazuh-alerts",

            "source_partition":
                0,

            "source_offset":
                123,

            "input_topic":
                "morpheus-input",

            "input_partition":
                0,

            "input_offset":
                456,

            "scored_at_utc":
                "2026-10-14T15:30:00+00:00",

            "artifact_hashes":
                artifacts,

            "vocab_hash_sha256":
                "1" * 64,

            "engine_sha256":
                "2" * 64,

            "worker_sha256":
                "3" * 64,

            "production_ready":
                False,

            "automated_response_allowed":
                False,
        }

    def key(self, event):
        return event[
            "event_uid"
        ].encode("ascii")

    def test_valid_event_passes(self):
        event = self.event()

        self.assertIs(
            module.validate(
                event,
                self.key(event),
            ),
            event,
        )

    def test_wrong_kafka_key_rejected(self):
        event = self.event()

        with self.assertRaises(
            ValueError
        ):
            module.validate(
                event,
                b"0" * 64,
            )

    def test_wrong_mode_engine_or_model_rejected(self):
        cases = (
            (
                "processing_mode",
                "replay",
            ),
            (
                "analysis_engine",
                "morpheus-simulator",
            ),
            (
                "model_name",
                "other-model",
            ),
        )

        for field, value in cases:
            event = self.event()
            event[field] = value

            with self.assertRaises(
                ValueError
            ):
                module.validate(
                    event,
                    self.key(event),
                )

    def test_safety_flags_fail_closed(self):
        for field in (
            "production_ready",
            "automated_response_allowed",
        ):
            event = self.event()
            event[field] = True

            with self.assertRaises(
                ValueError
            ):
                module.validate(
                    event,
                    self.key(event),
                )

    def test_raw_payload_rejected(self):
        for field in (
            "raw_event",
            "full_log",
            "text_input",
        ):
            event = self.event()
            event[field] = {
                "secret": "raw"
            }

            with self.assertRaises(
                ValueError
            ):
                module.validate(
                    event,
                    self.key(event),
                )

    def test_bad_score_and_label_rejected(self):
        for score in (
            -0.1,
            1.1,
            float("nan"),
            float("inf"),
            True,
        ):
            event = self.event()
            event[
                "high_severity_score"
            ] = score

            with self.assertRaises(
                ValueError
            ):
                module.validate(
                    event,
                    self.key(event),
                )

        event = self.event()
        event[
            "predicted_label"
        ] = "low_severity"

        with self.assertRaises(
            ValueError
        ):
            module.validate(
                event,
                self.key(event),
            )

    def test_source_coordinates_required(self):
        cases = (
            (
                "source_topic",
                "replay-wazuh-alerts",
            ),
            (
                "source_partition",
                -1,
            ),
            (
                "source_offset",
                True,
            ),
            (
                "input_topic",
                "wrong-topic",
            ),
            (
                "input_partition",
                -1,
            ),
            (
                "input_offset",
                False,
            ),
        )

        for field, value in cases:
            event = self.event()
            event[field] = value

            with self.assertRaises(
                ValueError
            ):
                module.validate(
                    event,
                    self.key(event),
                )

    def test_artifact_hashes_strict(self):
        event = self.event()

        event[
            "artifact_hashes"
        ][
            "checkpoint_weights_sha256"
        ] = "bad"

        with self.assertRaises(
            ValueError
        ):
            module.validate(
                event,
                self.key(event),
            )

        event = self.event()

        event[
            "artifact_hashes"
        ][
            "unexpected"
        ] = "f" * 64

        with self.assertRaises(
            ValueError
        ):
            module.validate(
                event,
                self.key(event),
            )

    def test_document_id_is_stable(self):
        first = self.event()
        second = copy.deepcopy(
            first
        )

        second[
            "scored_at_utc"
        ] = (
            "2026-10-14T16:30:00+00:00"
        )

        self.assertEqual(
            module.document_id(
                first
            ),
            module.document_id(
                second
            ),
        )

    def test_different_event_has_different_document_id(self):
        first = self.event()
        second = copy.deepcopy(
            first
        )

        second[
            "event_uid"
        ] = "f" * 64

        self.assertNotEqual(
            module.document_id(
                first
            ),
            module.document_id(
                second
            ),
        )

    def test_projection_removes_unknown_fields(self):
        event = self.event()

        event["unexpected"] = {
            "private": True
        }

        projected = module.project(
            event
        )

        self.assertNotIn(
            "unexpected",
            projected,
        )

        self.assertNotIn(
            "raw_event",
            projected,
        )

    def test_index_name_uses_scoring_time(self):
        self.assertEqual(
            module.index_name(
                self.event()
            ),
            "edrxdr-events-2026.10.14",
        )

    def test_nonfinite_json_rejected(self):
        with self.assertRaises(
            ValueError
        ):
            module.strict_json(
                b'{"score":NaN}'
            )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
