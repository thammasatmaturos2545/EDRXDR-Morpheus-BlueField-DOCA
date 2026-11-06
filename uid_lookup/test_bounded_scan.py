import unittest

from uid_lookup.bounded_scan import scan_wazuh


def hit(document_id="doc1", valid=True):
    source = {
        "manager": {"name": "manager"},
        "agent": {"id": "001"} if valid else {},
        "id": "123",
        "full_log": "SECRET TEST DATA",
    }
    return {
        "_index": "wazuh-alerts-4.x-2026.10.15",
        "_id": document_id,
        "_source": source,
    }


class FakeTransport:
    def __init__(self, pages):
        self.pages = list(pages)
        self.calls = []

    def __call__(self, method, path, body):
        self.calls.append((method, path, body))

        if method == "DELETE":
            return {"succeeded": True}

        return {
            "timed_out": False,
            "_shards": {
                "total": 1,
                "successful": 1,
                "skipped": 0,
                "failed": 0,
            },
            **self.pages.pop(0),
        }


class TestBoundedScan(unittest.TestCase):

    def test_success_and_scroll_cleanup(self):
        transport = FakeTransport([
            {
                "_scroll_id": "test-scroll",
                "hits": {"hits": [hit()]},
            },
            {
                "_scroll_id": "test-scroll",
                "hits": {"hits": []},
            },
        ])

        result = scan_wazuh(
            transport, page_size=1, max_documents=10
        )

        self.assertEqual(result["scanned"], 1)
        self.assertEqual(len(result["records"]), 1)
        self.assertTrue(result["complete"])

        self.assertEqual(
            transport.calls[-1][0], "DELETE"
        )

        self.assertNotIn(
            "SECRET TEST DATA", str(result)
        )

    def test_max_documents(self):
        transport = FakeTransport([
            {
                "_scroll_id": "test-scroll",
                "hits": {"hits": [hit()]},
            }
        ])

        result = scan_wazuh(
            transport, page_size=1, max_documents=1
        )

        self.assertEqual(result["scanned"], 1)
        self.assertFalse(result["complete"])

    def test_invalid_identity_counted(self):
        transport = FakeTransport([
            {
                "_scroll_id": "test-scroll",
                "hits": {"hits": [hit(valid=False)]},
            },
            {
                "_scroll_id": "test-scroll",
                "hits": {"hits": []},
            },
        ])

        result = scan_wazuh(
            transport, page_size=1, max_documents=10
        )

        self.assertEqual(result["rejected"], 1)
        self.assertEqual(len(result["records"]), 0)

    def test_invalid_limits(self):
        with self.assertRaises(ValueError):
            scan_wazuh(None, page_size=1000)

        with self.assertRaises(ValueError):
            scan_wazuh(None, max_documents=100000)


if __name__ == "__main__":
    unittest.main()
