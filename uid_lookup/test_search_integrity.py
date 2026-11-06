import unittest

from uid_lookup.bounded_scan import scan_wazuh


def response(*, timed_out=False, failed=0):
    return {
        "_scroll_id": "test-scroll",
        "timed_out": timed_out,
        "_shards": {
            "total": 1,
            "successful": 0 if failed else 1,
            "skipped": 0,
            "failed": failed,
        },
        "hits": {"hits": []},
    }


class Transport:
    def __init__(self, data):
        self.data = data
        self.cleaned = False

    def __call__(self, method, path, body):
        if method == "DELETE":
            self.cleaned = True
            return {"succeeded": True}
        return self.data


class TestSearchIntegrity(unittest.TestCase):

    def test_timeout_rejected(self):
        transport = Transport(response(timed_out=True))

        with self.assertRaises(ValueError):
            scan_wazuh(transport)

        self.assertTrue(transport.cleaned)

    def test_shard_failure_rejected(self):
        transport = Transport(response(failed=1))

        with self.assertRaises(ValueError):
            scan_wazuh(transport)

        self.assertTrue(transport.cleaned)

    def test_complete_response_accepted(self):
        transport = Transport(response())

        result = scan_wazuh(transport)

        self.assertTrue(result["complete"])
        self.assertEqual(result["scanned"], 0)
        self.assertTrue(transport.cleaned)


if __name__ == "__main__":
    unittest.main()
