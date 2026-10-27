"""Sequence and extra metrics: mocks only, never Docker or a load generator."""
import gzip
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import panel
import panel_metrics as metrics


class SequenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.manager = panel.Manager(Path(self.temp.name), collect_resources=False)
        self.order = []

    def tearDown(self):
        self.temp.cleanup()

    def enqueue(self):
        with patch.object(panel.threading.Thread, "start"):
            return self.manager.compare({"rate": 5, "seconds": 20})["id"]

    def succeed(self, identity):
        job = self.manager.jobs[identity]
        self.assertEqual(self.manager.active_id, identity)
        self.assertIsNotNone(self.manager.active_comparison_id)
        with self.assertRaises(panel.BusyError):
            self.manager.run({"variant": "sync", "rate": 1, "seconds": 1})
        self.order.append(job["parameters"]["variant"])
        job.update(status="passed", k6_exit=0, summary={"sent": 100}, comparison_evidence_ready=True, finished_at=panel.now())
        self.manager.save(job)
        self.manager.active_id = None

    def test_order_identical_parameters_distinct_ids_and_no_overlap(self):
        identity = self.enqueue()
        self.manager.worker = self.succeed
        self.manager.comparison_worker(identity)
        pair = self.manager.comparisons[identity]
        self.assertEqual(self.order, ["sync", "async"])
        self.assertNotEqual(pair["jobs"]["sync"], pair["jobs"]["async"])
        for job_id in pair["jobs"].values():
            config = self.manager.jobs[job_id]["parameters"]
            self.assertEqual((config["rate"], config["seconds"]), (5, 20))
        self.assertEqual(pair["status"], "passed")
        self.assertIsNone(self.manager.active_comparison_id)

    def test_pair_reservation_refuses_single_and_another_pair(self):
        self.enqueue()
        with self.assertRaises(panel.BusyError):
            self.manager.run({"variant": "async", "rate": 5, "seconds": 20})
        with self.assertRaises(panel.BusyError):
            self.manager.compare({"rate": 5, "seconds": 20})
        with self.assertRaises(panel.BusyError):
            self.manager.readiness()

    def test_threshold_failure_is_preserved_and_second_still_runs_once(self):
        identity = self.enqueue()

        def worker(job_id):
            self.succeed(job_id)
            job = self.manager.jobs[job_id]
            if job["parameters"]["variant"] == "sync":
                job.update(status="failed", k6_exit=99)

        self.manager.worker = worker
        self.manager.comparison_worker(identity)
        self.assertEqual(self.order, ["sync", "async"])
        self.assertEqual(self.manager.comparisons[identity]["status"], "failed")
        self.assertEqual(len(self.manager.jobs), 2)

    def test_precondition_block_does_not_start_second(self):
        identity = self.enqueue()

        def worker(job_id):
            job = self.manager.jobs[job_id]
            self.order.append(job["parameters"]["variant"])
            job.update(status="failed", k6_exit=None, summary=None)
            self.manager.active_id = None

        self.manager.worker = worker
        self.manager.comparison_worker(identity)
        self.assertEqual(self.order, ["sync"])
        self.assertIsNone(self.manager.comparisons[identity]["jobs"]["async"])

    def test_incomplete_metric_evidence_stops_sequence(self):
        identity = self.enqueue()

        def worker(job_id):
            self.succeed(job_id)
            self.manager.jobs[job_id].update(status="failed", comparison_evidence_ready=False)

        self.manager.worker = worker
        self.manager.comparison_worker(identity)
        self.assertEqual(self.order, ["sync"])
        self.assertEqual(self.manager.comparisons[identity]["status"], "failed")

    def test_cancellation_between_stages_never_starts_async(self):
        identity = self.enqueue()

        def worker(job_id):
            self.succeed(job_id)
            self.manager.stop_comparison(identity)

        self.manager.worker = worker
        self.manager.comparison_worker(identity)
        self.assertEqual(self.order, ["sync"])
        self.assertEqual(self.manager.comparisons[identity]["status"], "interrupted")

    def test_cancellation_before_launch_creates_no_children(self):
        identity = self.enqueue()
        self.manager.stop_comparison(identity)
        self.manager.comparison_worker(identity)
        self.assertEqual(self.manager.jobs, {})
        self.assertEqual(self.manager.comparisons[identity]["status"], "interrupted")

    def test_stopping_child_also_cancels_next_variant(self):
        identity = self.enqueue()

        def worker(job_id):
            self.manager.stop(job_id)
            self.manager.jobs[job_id]["status"] = "interrupted"
            self.manager.active_id = None

        self.manager.worker = worker
        self.manager.comparison_worker(identity)
        pair = self.manager.comparisons[identity]
        self.assertIsNone(pair["jobs"]["async"])
        self.assertEqual(pair["status"], "interrupted")

    def test_restart_does_not_resume_sequence(self):
        identity = self.enqueue()
        restored = panel.Manager(Path(self.temp.name), collect_resources=False)
        self.assertEqual(restored.comparisons[identity]["status"], "interrupted")
        self.assertIsNone(restored.active_comparison_id)
        self.assertEqual(restored.jobs, {})

    def test_no_extra_fields_or_unbounded_settings(self):
        for value in ({"rate": 5, "seconds": 20, "target": "remote"},
                      {"rate": True, "seconds": 20}, {"rate": 11, "seconds": 20},
                      {"rate": 5, "seconds": 31}, {"rate": 5, "seconds": "20"}):
            with self.assertRaises(ValueError):
                panel.comparison_parameters(value)


class RichMetricsTests(unittest.TestCase):
    def test_phase_filter_statuses_stages_and_final_summary(self):
        points = []
        for metric, value, status, phase in [
            ("http_req_duration", 9999, "200", "readiness"),
            ("http_req_duration", 10, "201", "demo"),
            ("http_req_duration", 30, "503", "demo"),
            ("http_req_waiting", 8, "201", "demo"),
            ("http_req_failed", 0, "201", "demo"),
            ("http_req_failed", 1, "503", "demo"),
            ("checks", 1, "201", "demo"), ("checks", 0, "503", "demo"),
            ("demo_sent", 1, None, None), ("demo_sent", 1, None, None),
            ("demo_errors", 1, None, None)]:
            points.append(json.dumps({"type": "Point", "metric": metric,
                                      "data": {"value": value, "time": "2026-10-27T23:00:01Z",
                                               "tags": {"status": status, "phase": phase}}}))
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "data.gz"
            path.write_bytes(gzip.compress(("\n".join(points) + "\n").encode()))
            result = metrics.read_samples(path)
        self.assertTrue(result["raw_complete"])
        self.assertEqual(result["statuses"], {"201": 1, "503": 1})
        self.assertEqual(result["http_failure_pct"], 50)
        self.assertEqual(result["checks_passed"], 1)
        self.assertEqual(result["checks_failed"], 1)
        self.assertEqual(result["stages_ms"]["waiting"], 8)
        self.assertEqual(result["latency_ms"]["avg"], 20)
        summary = {"sent": 2, "errors": 1, "dropped_iterations": 0,
                   "http_duration_ms": {"p(95)": 28.5}}
        enriched = metrics.enrich(result, summary, {"metrics": {"http_reqs": {"values": {"count": 3}}}}, 2)
        self.assertEqual(enriched["send_rate_window"], 1)
        self.assertEqual(enriched["invalid_pct"], 50)
        self.assertEqual(enriched["http_p95_ms"], 28.5)
        self.assertEqual(enriched["generator"]["http_total"], 3)
        self.assertEqual(enriched["http_observed"], 2)
        self.assertEqual(result["http_p95_ms"], 29)  # projection does not mutate raw analysis

    def test_absent_metrics_are_unknown_and_not_zero(self):
        result = metrics.enrich(metrics.read_samples(Path("missing")), None, None, 20)
        self.assertIsNone(result["sent"])
        self.assertIsNone(result["generator"]["bytes_sent"])
        self.assertNotIn("send_rate_window", result)

    def test_memory_units_and_bad_values(self):
        self.assertEqual(metrics.memory_mib("1GiB"), 1024)
        self.assertEqual(metrics.memory_mib("1024KiB"), 1)
        for value in ("NaNMiB", "-1MiB", "1banana", "infinity B"):
            with self.assertRaises(ValueError):
                metrics.memory_mib(value)

    def test_resource_snapshot_only_uses_verified_project(self):
        identities = [str(index) * 64 for index in range(1, 6)]
        services = ["sync-api", "async-api", "consumer", "postgres", "kafka"]
        calls = []

        def fake_run(args, **kwargs):
            calls.append(args)
            if args[1] == "ps":
                output = "\n".join(identities)
            elif args[1] == "inspect":
                output = "\n".join(identity + " " + json.dumps({"com.docker.compose.project": "tcc-java-2026",
                                  "com.docker.compose.service": service}) for identity, service in zip(identities, services))
            else:
                output = "\n".join(json.dumps({"ID": identity[:12], "CPUPerc": "1.5%", "MemUsage": "20MiB / 1GiB"}) for identity in identities)
            return subprocess.CompletedProcess(args, 0, stdout=output.encode(), stderr=b"")

        snapshot = metrics.resource_snapshot(run=fake_run)
        self.assertEqual(len(snapshot["services"]), 5)
        self.assertEqual(snapshot["services"][0]["memory_mib"], 20)
        self.assertTrue(all(command[1] in ("ps", "inspect", "stats") for command in calls))
        self.assertEqual(set(calls[-1][-5:]), set(identities))
        summary = metrics.resource_summary([snapshot, snapshot])
        self.assertEqual(summary[0]["samples"], 2)
        self.assertEqual(summary[0]["cpu_avg_pct"], 1.5)

    def test_foreign_project_is_rejected_before_stats(self):
        identity = "a" * 64
        calls = []

        def fake_run(args, **kwargs):
            calls.append(args)
            output = identity if args[1] == "ps" else identity+' {"com.docker.compose.project":"other","com.docker.compose.service":"sync-api"}'
            return subprocess.CompletedProcess(args, 0, stdout=output.encode(), stderr=b"")

        with self.assertRaises(ValueError):
            metrics.resource_snapshot(run=fake_run)
        self.assertEqual([command[1] for command in calls], ["ps", "inspect"])


if __name__ == "__main__":
    unittest.main()
