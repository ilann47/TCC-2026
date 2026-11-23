"""No Docker or load generation: HTTP boundaries, lifecycle and honest metrics."""
import gzip
import http.client
import importlib.util
import io
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

DEMO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(DEMO))
spec = importlib.util.spec_from_file_location("demo_panel", DEMO / "panel.py")
panel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(panel)
SESSION = "11111111-2222-4333-8444-555555555555"
RUN = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
CONFIG = {"variant": "sync", "rate": 5, "seconds": 20}


class ParameterTests(unittest.TestCase):
    def test_compose_startup_does_not_require_a_second_terminal(self):
        self.assertIn("docker compose stop painel", panel.startup_message(5666, True))
        self.assertNotIn("Mantenha este terminal", panel.startup_message(5666, True))
        self.assertIn("Mantenha este terminal", panel.startup_message(5666))

    def test_allowed_boundaries(self):
        for variant in ("sync", "async"):
            for rate in (1, 10):
                for seconds in (1, 30):
                    value = dict(variant=variant, rate=rate, seconds=seconds)
                    self.assertEqual(panel.parameters(value), value)

    def test_arbitrary_targets_and_invalid_values_rejected(self):
        invalid = [None, [], {}, dict(CONFIG, target="http://remote"), dict(CONFIG, variant="sync;id"),
                   dict(CONFIG, variant=["sync"]), dict(CONFIG, rate=True), dict(CONFIG, rate=0),
                   dict(CONFIG, rate=11), dict(CONFIG, seconds=31), dict(CONFIG, seconds="20"),
                   dict(CONFIG, seconds=1.5)]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                panel.parameters(value)

    def test_environment_removes_injected_settings(self):
        with tempfile.TemporaryDirectory() as root, patch.dict(panel.os.environ, {"BASH_ENV": "evil", "K6_OUT": "remote", "TCC_DEMO_RATE": "999"}):
            env = panel.Manager(Path(root)).environment(CONFIG)
            self.assertNotIn("BASH_ENV", env)
            self.assertNotIn("K6_OUT", env)
            self.assertEqual(env["TCC_DEMO_RATE"], "5")
            self.assertEqual(env["TCC_DEMO_DASHBOARD"], "0")


class SampleTests(unittest.TestCase):
    def test_incomplete_gzip_filters_readiness_and_keeps_drops_separate(self):
        points = []
        for metric, value, phase in [("http_req_duration", 9999, "readiness"),
                                     ("http_req_duration", 10, "demo"),
                                     ("http_req_duration", 30, "demo"),
                                     ("demo_sent", 1, None), ("demo_sent", 1, "demo"),
                                     ("demo_errors", 0, None), ("dropped_iterations", 1, None)]:
            points.append(json.dumps({"type": "Point", "metric": metric,
                                      "data": {"value": value, "time": "2026-10-27T20:00:01Z", "tags": {"phase": phase}}}))
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "samples.gz"
            path.write_bytes(gzip.compress(("\n".join(points) + "\n").encode())[:-8])
            metrics = panel.samples(path)
            self.assertEqual(metrics["sent"], 2)
            self.assertEqual(metrics["errors"], 0)
            self.assertEqual(metrics["dropped_iterations"], 1)
            self.assertEqual(metrics["http_p95_ms"], 29)
            self.assertEqual(metrics["series"][0]["avg_ms"], 20)

    def test_missing_samples_are_unknown_not_zero(self):
        metrics = panel.samples(Path("nonexistent-samples-test"))
        self.assertIsNone(metrics["errors"])
        self.assertIsNone(metrics["sent"])
        self.assertEqual(metrics["series"], [])


class FinishedProcess:
    pid = 99999999

    def __init__(self, code=0):
        self.stdout = io.BytesIO(("PANEL_SESSION=" + SESSION + "\nconsole\n").encode())
        self.code = code

    def wait(self, timeout=None):
        return self.code

    def poll(self):
        return self.code


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = Path(self.temp.name)
        self.calls = []

        def popen(argv, **kwargs):
            self.calls.append((argv, kwargs))
            return FinishedProcess(self.code)

        self.manager = panel.Manager(self.app, popen=popen)
        self.code = 0

    def tearDown(self):
        self.temp.cleanup()

    def enqueue(self):
        with patch.object(panel.threading.Thread, "start"):
            return self.manager.run(CONFIG)["id"]

    def evidence(self, drops=0):
        folder = self.app / ".runtime/demonstracao" / SESSION / f"k6-{RUN}-sync"
        folder.mkdir(parents=True)
        summary = dict(kind="presentation_demo_not_definitive", run_id=RUN, **CONFIG,
                       sent=100, errors=0, dropped_iterations=drops,
                       http_duration_ms={"avg": 10, "med": 8, "p(95)": 20, "p(99)": 25, "max": 30})
        (folder / "resumo.json").write_text(json.dumps(summary))
        (folder / "manifest.txt").write_text(f"run_id={RUN}\nvariant=sync\nk6_exit={self.code}\n")
        return folder

    def test_only_fixed_command_and_no_shell(self):
        identity = self.enqueue()
        self.evidence()
        self.manager.worker(identity)
        argv, kwargs = self.calls[0]
        self.assertEqual(argv, ["bash", str(self.app / "demo/apresentacao.sh"), "--run-sync"])
        self.assertNotIn("shell", kwargs)
        self.assertTrue(kwargs["start_new_session"])
        self.assertEqual(self.manager.jobs[identity]["status"], "passed")
        self.assertIsNone(self.manager.active_id)

    def test_nonzero_exit_and_dropped_iteration_remain_failure(self):
        self.code = 99
        identity = self.enqueue()
        self.evidence(drops=1)
        self.manager.worker(identity)
        detail = self.manager.detail(identity)
        self.assertEqual(detail["status"], "failed")
        self.assertEqual(detail["k6_exit"], 99)
        self.assertEqual(detail["metrics"]["dropped_iterations"], 1)
        self.assertEqual(detail["metrics"]["errors"], 0)
        self.assertFalse(detail["metrics"]["provisional"])

    def test_no_summary_never_passes(self):
        identity = self.enqueue()
        self.manager.worker(identity)
        self.assertEqual(self.manager.jobs[identity]["status"], "failed")

    def test_mismatched_parameters_never_pass(self):
        identity = self.enqueue()
        folder = self.evidence()
        summary = json.loads((folder / "resumo.json").read_text())
        summary["rate"] = 10
        (folder / "resumo.json").write_text(json.dumps(summary))
        self.manager.worker(identity)
        self.assertEqual(self.manager.jobs[identity]["status"], "failed")

    def test_second_job_refused(self):
        self.enqueue()
        with self.assertRaises(panel.BusyError):
            self.manager.run(CONFIG)

    def test_restart_preserves_pending_as_interrupted_without_execution(self):
        identity = self.enqueue()
        restored = panel.Manager(self.app)
        self.assertEqual(restored.jobs[identity]["status"], "interrupted")
        self.assertIsNone(restored.active_id)

    def test_cancel_before_launch_does_not_execute(self):
        identity = self.enqueue()
        self.manager.stop(identity)
        self.manager.worker(identity)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.manager.jobs[identity]["status"], "interrupted")

    def test_finished_job_cannot_stop_other_processes(self):
        identity = self.enqueue()
        self.evidence()
        self.manager.worker(identity)
        with patch.object(panel.os, "killpg") as kill:
            self.manager.stop(identity)
            kill.assert_not_called()

    def test_late_cancellation_cannot_become_approved(self):
        identity = self.enqueue()
        self.evidence()
        original = panel.verify_k6

        def cancel_during_validation(summary):
            self.manager.stop(identity, "Cancelamento controlado")
            original(summary)

        with patch.object(panel, "verify_k6", cancel_during_validation):
            self.manager.worker(identity)
        self.assertEqual(self.manager.jobs[identity]["status"], "interrupted")
        self.assertEqual(self.manager.jobs[identity]["message"], "Cancelamento controlado")

    def test_stop_targets_only_its_owned_process_group(self):
        identity = self.enqueue()
        process = FinishedProcess()
        process.poll = lambda: None
        self.manager.process = process
        with patch.object(panel.os, "killpg") as kill, patch.object(panel.threading.Thread, "start"):
            self.manager.stop(identity)
            kill.assert_called_once_with(process.pid, panel.signal.SIGTERM)


class WaitingManager(panel.Manager):
    def worker(self, identity):
        self.gate.wait(5)


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.manager = WaitingManager(Path(self.temp.name))
        self.manager.gate = threading.Event()
        self.dist = Path(self.temp.name) / "dist"
        (self.dist / "assets").mkdir(parents=True)
        (self.dist / "index.html").write_text('<div id="root"></div><script type="module" src="/resultados/assets/index-test.js"></script>', encoding="utf-8")
        (self.dist / "assets/index-test.js").write_text("console.log('results')", encoding="utf-8")
        (self.dist / "assets/index-test.css").write_text("body{color:blue}", encoding="utf-8")
        self.server = panel.Server(("127.0.0.1", 0), self.manager, results_dir=self.dist)
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.manager.gate.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def request(self, path, value=None, headers=None, method=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        body = None if value is None else json.dumps(value)
        defaults = {"Host": f"localhost:{self.port}", "Origin": f"http://localhost:{self.port}",
                    "Content-Type": "application/json", "X-CSRF-Token": self.server.token}
        defaults.update(headers or {})
        connection.request(method or ("GET" if value is None else "POST"), path, body=body, headers=defaults)
        response = connection.getresponse()
        result = response.status, response.getheaders(), response.read()
        connection.close()
        return result

    def test_state_read_only_and_security_headers(self):
        status, headers, body = self.request("/api/state")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["csrf_token"], self.server.token)
        self.assertEqual(self.manager.jobs, {})
        headers = dict(headers)
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertNotIn("Access-Control-Allow-Origin", headers)

    def test_foreign_host_origin_and_invalid_tokens_refused(self):
        for headers in ({"Host": "evil.test"}, {"Origin": "http://evil.test"},
                        {"Origin": "null"}, {"X-CSRF-Token": "bad"}, {"X-CSRF-Token": ""}):
            with self.subTest(headers=headers):
                self.assertEqual(self.request("/api/run", CONFIG, headers)[0], 403)
        self.assertEqual(self.manager.jobs, {})

    def test_foreign_get_host_refused(self):
        self.assertEqual(self.request("/api/state", headers={"Host": "evil.test"})[0], 403)

    def test_unapproved_peer_is_rejected_even_with_local_host_and_token(self):
        self.server.allowed_peers = frozenset({"172.28.0.1"})
        self.assertEqual(self.request("/api/state")[0], 403)
        self.assertEqual(self.request("/api/run", CONFIG)[0], 403)
        self.assertEqual(self.manager.jobs, {})

    def test_run_and_concurrent_conflict(self):
        status, _, body = self.request("/api/run", CONFIG)
        self.assertEqual(status, 202)
        identity = json.loads(body)["id"]
        self.assertEqual(self.request("/api/run", CONFIG)[0], 409)
        self.assertEqual(self.request(f"/api/jobs/{identity}")[0], 200)
        self.assertEqual(self.request(f"/api/jobs/{identity}/stop", {})[0], 200)

    def test_unknown_fields_bad_content_type_and_large_body(self):
        self.assertEqual(self.request("/api/run", dict(CONFIG, command="rm"))[0], 400)
        self.assertEqual(self.request("/api/run", CONFIG, {"Content-Type": "text/plain"})[0], 415)
        self.assertEqual(self.request("/api/run", {"large": "x" * 5000})[0], 413)

    def test_duplicate_host_header_refused(self):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        connection.putrequest("GET", "/api/state", skip_host=True)
        connection.putheader("Host", f"localhost:{self.port}")
        connection.putheader("Host", "evil.test")
        connection.endheaders()
        response = connection.getresponse()
        self.assertEqual(response.status, 403)
        response.read()
        connection.close()

    def test_unknown_job_and_file_paths_are_not_served(self):
        for path in ("/api/jobs/" + RUN, "/api/jobs/../state", "/../../README.md", "/painel-k6.html", "/api/state?x=1"):
            self.assertIn(self.request(path)[0], (400, 404))
        self.assertEqual(self.request("/api/jobs/" + RUN + "/stop", {})[0], 404)

    def test_only_fixed_assets(self):
        for path in ("/", "/panel.js", "/panel.css", "/dashboard.css", "/resultados"):
            self.assertEqual(self.request(path)[0], 200)
        for path in ("/results.js", "/results.css", "/results.html"):
            self.assertEqual(self.request(path)[0], 404)

    def test_compiled_results_and_demo_share_the_server(self):
        for path in ("/resultados", "/resultados/"):
            status, headers, body = self.request(path)
            self.assertEqual(status, 200)
            self.assertIn(b'/resultados/assets/index-test.js', body)
            self.assertEqual(dict(headers)["Content-Type"], "text/html; charset=utf-8")
        for extension, mime in (("js", "text/javascript"), ("css", "text/css")):
            status, headers, _ = self.request("/resultados/assets/index-test." + extension)
            self.assertEqual(status, 200)
            self.assertEqual(dict(headers)["Content-Type"], mime)
            self.assertIn("script-src 'self'", dict(headers)["Content-Security-Policy"])
        self.assertIn(b'aria-label="Painel local"', self.request("/")[2])
        self.assertEqual(self.manager.jobs, {})

    def test_missing_build_is_explicit_not_a_legacy_fallback(self):
        self.server.results_dir = Path(self.temp.name) / "missing"
        status, _, body = self.request("/resultados")
        self.assertEqual(status, 503)
        self.assertIn(b'npm run build', body)
        self.assertEqual(self.request("/")[0], 200)

    def test_build_asset_boundaries_and_same_origin_guards(self):
        for path in ("/resultados/assets/missing.js", "/resultados/assets/../../panel.py",
                     "/resultados/assets/%2e%2e/index-test.js", "/resultados/assets/.env",
                     "/resultados/assets/index-test.js.map", "/resultados/src/main.jsx",
                     "/resultados/other", "/resultados/assets/../index.html"):
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 404)
        self.assertEqual(self.request("/resultados?x=1")[0], 400)
        self.assertEqual(self.request("/resultados", {})[0], 404)
        self.assertEqual(self.request("/resultados", headers={"Host": "evil.test"})[0], 403)
        self.assertEqual(self.request("/resultados/assets/index-test.js", headers={"Host": "evil.test"})[0], 403)

    def test_build_symlink_cannot_escape_dist(self):
        outside = Path(self.temp.name) / "private.js"
        outside.write_text("private", encoding="utf-8")
        try:
            (self.dist / "assets/outside.js").symlink_to(outside)
        except OSError:
            self.skipTest("OS does not permit symlink creation")
        self.assertEqual(self.request("/resultados/assets/outside.js")[0], 404)

    def test_campaign_view_is_verified_read_only(self):
        with patch.object(panel,"get_report",return_value={"kind":"published_scientific_campaign_not_live_demo"}):
            status,_,body=self.request('/api/campaign')
            self.assertEqual(status,200)
            self.assertIn(b'published_scientific',body)
        self.assertEqual(self.request('/api/campaign',{})[0],404)
        self.assertEqual(self.manager.jobs,{})
        with patch.object(panel,"get_report",side_effect=ValueError('checksum')):
            self.assertEqual(self.request('/api/campaign')[0],503)

    def test_compare_api_retains_origin_guards_and_reservation(self):
        self.assertEqual(self.request("/api/compare", {"rate": 5, "seconds": 20}, {"Origin": "http://evil.test"})[0], 403)
        status, _, body = self.request("/api/compare", {"rate": 5, "seconds": 20})
        self.assertEqual(status, 202)
        identity = json.loads(body)["id"]
        self.assertEqual(self.request("/api/run", CONFIG)[0], 409)
        self.assertEqual(self.request("/api/comparisons/"+identity)[0], 200)
        self.assertEqual(self.request("/api/comparisons/"+identity+"/stop", {})[0], 200)


if __name__ == "__main__":
    unittest.main()
