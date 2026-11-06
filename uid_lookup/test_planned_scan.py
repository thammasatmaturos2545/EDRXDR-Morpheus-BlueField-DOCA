import unittest

from uid_lookup.checkpoint import make_plan
from uid_lookup.planned_scan import scan_planned_slice

INDEX = "wazuh-alerts-4.x-2026.10.15"


def sample_hit(index=INDEX):
    return {
        "_index": index,
        "_id": "doc-1",
        "_source": {
            "manager": {"name": "manager"},
            "agent": {"id": "001"},
            "id": "123",
        },
    }


class Transport:
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


class TestPlannedScan(unittest.TestCase):

    def setUp(self):
        self.plan = make_plan([INDEX], slices=32)

    def test_exact_index_and_slice(self):
        transport = Transport([
            {
                "_scroll_id": "scroll-1",
                "hits": {"hits": [sample_hit()]},
            },
            {
                "_scroll_id": "scroll-1",
                "hits": {"hits": []},
            },
        ])

        result = scan_planned_slice(
            transport,
            self.plan,
            3,
            page_size=1,
            max_documents=10,
        )

        method, path, body = transport.calls[0]

        self.assertEqual(method, "POST")
        self.assertEqual(
            path,
            f"/{INDEX}/_search?scroll=1m",
        )
        self.assertEqual(
            body["slice"],
            {"id": 3, "max": 32},
        )
        self.assertTrue(result["complete"])
        self.assertEqual(result["scanned"], 1)

    def test_bounded_incomplete_scan(self):
        transport = Transport([
            {
                "_scroll_id": "scroll-1",
                "hits": {"hits": [sample_hit()]},
            },
        ])

        result = scan_planned_slice(
            transport,
            self.plan,
            0,
            page_size=1,
            max_documents=1,
        )

        self.assertFalse(result["complete"])
        self.assertEqual(result["scanned"], 1)

    def test_foreign_index_rejected(self):
        transport = Transport([
            {
                "_scroll_id": "scroll-1",
                "hits": {
                    "hits": [
                        sample_hit(
                            "wazuh-alerts-4.x-2026.10.14"
                        )
                    ]
                },
            },
            {
                "_scroll_id": "scroll-1",
                "hits": {"hits": []},
            },
        ])

        with self.assertRaises(ValueError):
            scan_planned_slice(
                transport,
                self.plan,
                0,
                page_size=1,
                max_documents=10,
            )

    def test_invalid_slice_rejected(self):
        with self.assertRaises(ValueError):
            scan_planned_slice(
                None, self.plan, 32
            )

    def test_modified_plan_rejected(self):
        bad_plan = dict(self.plan)
        bad_plan["source_indices"] = [
            "wazuh-alerts-4.x-*"
        ]

        with self.assertRaises(ValueError):
            scan_planned_slice(
                None, bad_plan, 0
            )


if __name__ == "__main__":
    unittest.main()
