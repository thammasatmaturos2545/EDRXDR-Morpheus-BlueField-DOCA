"""CPU-only contract tests for Morpheus live severity inference."""

import importlib.util
import sys
from pathlib import Path
import unittest


SOURCE = (
    Path(__file__)
    .with_name("live_inference.py")
)

spec = importlib.util.spec_from_file_location(
    "live_inference_contract",
    SOURCE,
)

module = importlib.util.module_from_spec(
    spec
)

sys.modules[
    spec.name
] = module

spec.loader.exec_module(module)


class LiveInferenceContract(unittest.TestCase):

    def raw(self, event_id="1791991000.1541940"):
        return {
            "id": event_id,

            "manager": {
                "name":
                    "oa-hgx-h100-bu-02",
            },

            "agent": {
                "id": "001",
                "name":
                    "windows-agent",
            },

            "rule": {
                "id": "60137",
                "level": 5,
            },
        }

    def event(self):
        raw = self.raw()

        uid = module.canonical_wazuh_uid(
            raw
        )

        return {
            "event_uid":
                uid,

            "source_type":
                "wazuh",

            "source_topic":
                "wazuh-alerts",

            "source_partition":
                0,

            "source_offset":
                123,

            "raw_event":
                raw,
        }

    def output(self, score=0.25):
        event = self.event()

        return module.build_output(
            event,
            event["event_uid"].encode(
                "ascii"
            ),
            score,
            0,
            7,
            model_name="fixture-model",
            artifact_hashes={
                "x": "y"
            },
            vocab_hash_sha256=
                "a" * 64,
            engine_sha256=
                "b" * 64,
            worker_sha256=
                "c" * 64,
            scored_at_utc=
                "2026-10-14T00:00:00+00:00",
        )

    def test_valid_identity_passes(self):
        event = self.event()

        raw, uid = module.validate_input(
            event,
            event[
                "event_uid"
            ].encode("ascii"),
        )

        self.assertEqual(
            uid,
            event["event_uid"],
        )

        self.assertEqual(
            raw["id"],
            "1791991000.1541940",
        )

    def test_wrong_key_rejected(self):
        with self.assertRaises(
            ValueError
        ):
            module.validate_input(
                self.event(),
                b"0" * 64,
            )

    def test_changed_raw_identity_rejected(self):
        event = self.event()

        event["raw_event"]["id"] = (
            "different"
        )

        with self.assertRaises(
            ValueError
        ):
            module.validate_input(
                event,
                event[
                    "event_uid"
                ].encode("ascii"),
            )

    def test_wrong_source_rejected(self):
        event = self.event()

        event["source_topic"] = (
            "replay-wazuh-alerts"
        )

        with self.assertRaises(
            ValueError
        ):
            module.validate_input(
                event,
                event[
                    "event_uid"
                ].encode("ascii"),
            )

    def test_invalid_coordinates_rejected(self):
        for field, value in (
            (
                "source_partition",
                -1,
            ),
            (
                "source_partition",
                True,
            ),
            (
                "source_offset",
                -1,
            ),
            (
                "source_offset",
                False,
            ),
        ):
            event = self.event()
            event[field] = value

            with self.assertRaises(
                ValueError
            ):
                module.validate_input(
                    event,
                    event[
                        "event_uid"
                    ].encode(
                        "ascii"
                    ),
                )

    def test_output_preserves_exact_identity(self):
        event = self.event()
        out = self.output()

        self.assertEqual(
            out["event_uid"],
            event["event_uid"],
        )

        self.assertEqual(
            out["source_topic"],
            "wazuh-alerts",
        )

        self.assertEqual(
            out["source_partition"],
            0,
        )

        self.assertEqual(
            out["source_offset"],
            123,
        )

        self.assertEqual(
            out["input_topic"],
            "morpheus-input",
        )

        self.assertEqual(
            out["input_partition"],
            0,
        )

        self.assertEqual(
            out["input_offset"],
            7,
        )

    def test_output_is_nonproduction_and_no_response(self):
        out = self.output()

        self.assertIs(
            out["production_ready"],
            False,
        )

        self.assertIs(
            out[
                "automated_response_allowed"
            ],
            False,
        )

        self.assertEqual(
            out["processing_mode"],
            "live",
        )

        self.assertEqual(
            out["analysis_engine"],
            "nvidia-morpheus-context-severity-v1",
        )

    def test_raw_payload_not_emitted(self):
        out = self.output()

        self.assertNotIn(
            "raw_event",
            out,
        )

        self.assertNotIn(
            "full_log",
            out,
        )

        self.assertNotIn(
            "text_input",
            out,
        )

    def test_threshold_and_label(self):
        low = self.output(
            0.499
        )

        high = self.output(
            0.5
        )

        self.assertEqual(
            low["threshold"],
            0.5,
        )

        self.assertEqual(
            low["predicted_label"],
            "low_severity",
        )

        self.assertEqual(
            high["predicted_label"],
            "high_severity",
        )

    def test_invalid_score_rejected(self):
        for score in (
            -0.1,
            1.1,
            float("nan"),
            float("inf"),
            True,
        ):
            with self.assertRaises(
                ValueError
            ):
                self.output(score)

    def test_execution_gate_defaults_closed(self):
        import os

        old = os.environ.pop(
            "LIVE_INFERENCE_RUN_ALLOWED",
            None,
        )

        try:
            with self.assertRaises(
                RuntimeError
            ):
                module.require_run_permission()
        finally:
            if old is not None:
                os.environ[
                    "LIVE_INFERENCE_RUN_ALLOWED"
                ] = old


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
