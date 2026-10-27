import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("demo_json", Path(__file__).resolve().parents[1] / "json_helper.py")
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
EVENT = "00000000-0000-4000-8000-000000000001"
RUN = "00000000-0000-4000-8000-000000000002"


class JsonHelperTests(unittest.TestCase):
    def test_payload_uses_supplied_identity_and_synthetic_source(self):
        data = helper.build_payload(EVENT, RUN, "async")
        self.assertEqual(EVENT, data["event_id"])
        self.assertEqual("demo-apresentacao-" + RUN, data["source"])
        self.assertIn("+00:00", data["occurred_at"])
        self.assertLessEqual(len(data["source"]), 100)

    def test_invalid_identity_is_rejected(self):
        with self.assertRaises(ValueError):
            helper.build_payload("not-a-uuid", RUN, "sync")

    def test_invalid_variant_is_rejected(self):
        with self.assertRaises(ValueError):
            helper.build_payload(EVENT, RUN, "other")

    def test_local_mapping_is_accepted(self):
        self.assertEqual("http://127.0.0.1:18002", helper.loopback_url("127.0.0.1:18002\n"))

    def test_remote_or_ambiguous_mappings_are_rejected(self):
        for value in ("0.0.0.0:80", "example.com:80", "127.0.0.1:0", "127.0.0.1:65536", "127.0.0.1:80\n127.0.0.1:81", "127.0.0.1:80/path"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                helper.loopback_url(value)

    def test_sync_persisted_and_duplicate_are_accepted(self):
        for status in ("persisted", "duplicate"):
            helper.verify_response({"event_id": EVENT, "status": status}, EVENT, "201")

    def test_async_acceptance_is_distinct_from_persistence(self):
        helper.verify_response({"event_id": EVENT, "status": "accepted"}, EVENT, "202")
        with self.assertRaises(ValueError):
            helper.verify_response({"event_id": EVENT, "status": "accepted"}, EVENT, "200")

    def test_wrong_uuid_is_not_success(self):
        with self.assertRaises(ValueError):
            helper.verify_response({"event_id": RUN, "status": "persisted"}, EVENT, "201")

    def test_non_object_is_not_success(self):
        with self.assertRaises(ValueError):
            helper.verify_response([], EVENT, "200")

    def good_summary(self):
        return {"kind": "presentation_demo_not_definitive", "sent": 6, "errors": 0,
                "dropped_iterations": 0, "http_duration_ms": dict.fromkeys(("avg", "med", "p(95)", "p(99)", "max"), 2.0)}

    def test_valid_demo_summary(self):
        helper.verify_k6(self.good_summary())

    def test_empty_failed_and_dropped_runs_are_rejected(self):
        for key, value in (("sent", 0), ("errors", 1), ("dropped_iterations", 1), ("kind", "definitive")):
            data = self.good_summary()
            data[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                helper.verify_k6(data)

    def test_missing_or_nonfinite_timing_is_not_zero(self):
        for value in (None, True, float("nan"), float("inf"), -1):
            data = self.good_summary()
            data["http_duration_ms"]["p(95)"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                helper.verify_k6(data)


if __name__ == "__main__":
    unittest.main()
