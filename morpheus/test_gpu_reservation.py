from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import unittest


SOURCE = Path(__file__).with_name("check_gpu_reservation.py")

spec = importlib.util.spec_from_file_location(
    "gpu_reservation",
    SOURCE,
)

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ReservationContract(unittest.TestCase):

    def reservation(self):
        return {
            "authorization": "authorized fixture",
            "effective_from": "2026-10-14T12:00:00+07:00",
            "reservation_end": "2026-10-14T14:00:00+07:00",
            "launcher_cutoff": "2026-10-14T13:55:00+07:00",
            "max_session_seconds": 600,
            "gpu_uuid": "GPU-fixture",
        }

    def now(self, hour=12, minute=30):
        return datetime(
            2026, 10, 14,
            hour, minute,
            tzinfo=timezone(
                __import__("datetime").timedelta(hours=7)
            ),
        )

    def test_valid_window(self):
        result = module.validate_window(
            self.reservation(),
            self.now(),
            120,
        )

        self.assertEqual(
            result["requested_seconds"],
            120,
        )

    def test_expired_reservation_rejected(self):
        with self.assertRaises(RuntimeError):
            module.validate_window(
                self.reservation(),
                self.now(15, 0),
                120,
            )

    def test_before_start_rejected(self):
        with self.assertRaises(RuntimeError):
            module.validate_window(
                self.reservation(),
                self.now(11, 0),
                120,
            )

    def test_session_limit_rejected(self):
        with self.assertRaises(RuntimeError):
            module.validate_window(
                self.reservation(),
                self.now(),
                601,
            )

    def test_crossing_cutoff_rejected(self):
        with self.assertRaises(RuntimeError):
            module.validate_window(
                self.reservation(),
                self.now(13, 54),
                120,
            )

    def test_cutoff_after_reservation_invalid(self):
        data = self.reservation()
        data["launcher_cutoff"] = "2026-10-14T14:05:00+07:00"

        with self.assertRaises(ValueError):
            module.validate_window(
                data,
                self.now(),
                60,
            )

    def test_missing_authorization_rejected(self):
        data = self.reservation()
        data["authorization"] = ""

        with self.assertRaises(ValueError):
            module.validate_window(
                data,
                self.now(),
                60,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
