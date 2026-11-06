import hashlib
import unittest

from uid_lookup.wazuh_uid import wazuh_event_uid


class TestWazuhUid(unittest.TestCase):

    def test_exact_uid(self):
        event = {
            "manager": {"name": "manager"},
            "agent": {"id": "001"},
            "id": "123",
        }

        canonical = "wazuh-v1|7:manager|3:001|3:123"
        expected = hashlib.sha256(
            canonical.encode()
        ).hexdigest()

        self.assertEqual(wazuh_event_uid(event), expected)

    def test_unicode_and_trim(self):
        event = {
            "manager": {"name": " ไทย "},
            "agent": {"id": "é"},
            "id": 1,
        }

        canonical = "wazuh-v1|9:ไทย|2:é|1:1"
        expected = hashlib.sha256(
            canonical.encode("utf-8")
        ).hexdigest()

        self.assertEqual(wazuh_event_uid(event), expected)

    def test_missing_identity(self):
        self.assertIsNone(wazuh_event_uid({
            "manager": {"name": "manager"},
            "agent": {},
            "id": "123",
        }))

    def test_invalid_identity(self):
        self.assertIsNone(wazuh_event_uid({
            "manager": {"name": "manager"},
            "agent": {"id": True},
            "id": "123",
        }))


if __name__ == "__main__":
    unittest.main()
