#!/usr/bin/env python3
"""Loopback-only control panel for bounded presentation tests, not the campaign."""
import argparse
import hmac
import json
import os
import re
import secrets
import signal
import subprocess
import threading
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from json_helper import canonical_uuid, verify_k6
from panel_metrics import enrich, finite, read_samples, resource_snapshot, resource_summary

APP = Path(__file__).resolve().parent.parent
ASSETS = Path(__file__).resolve().parent / "panel"
ACTIVE = {"queued", "running", "stopping"}
STATES = ACTIVE | {"passed", "failed", "interrupted"}
UUID_PATTERN = r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}"
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parameters(value):
    if not isinstance(value, dict) or set(value) != {"variant", "rate", "seconds"}:
        raise ValueError("Informe somente variant, rate e seconds.")
    if value["variant"] not in ("sync", "async"):
        raise ValueError("Variante deve ser sync ou async.")
    for key, maximum in (("rate", 10), ("seconds", 30)):
        if type(value[key]) is not int or not 1 <= value[key] <= maximum:
            raise ValueError(f"{key} deve ser inteiro entre 1 e {maximum}.")
    return dict(value)


def comparison_parameters(value):
    if not isinstance(value, dict) or set(value) != {"rate", "seconds"}:
        raise ValueError("A comparação aceita somente rate e seconds.")
    parameters(dict(value, variant="sync"))
    return dict(value)


def read_json(path):
    if path.stat().st_size > 256_000:
        raise ValueError("JSON excede limite.")
    return json.loads(path.read_text(encoding="utf-8"))


def tail(path):
    try:
        with path.open("rb") as stream:
            stream.seek(max(0, path.stat().st_size - 16_000))
            return stream.read(16_000).decode("utf-8", errors="replace")
    except OSError:
        return ""


def samples(path):
    return read_samples(path)


class BusyError(Exception):
    pass


class Manager:
    def __init__(self, app=APP, popen=subprocess.Popen, collect_resources=True):
        self.app = Path(app)
        self.root = self.app / ".runtime/demonstracao/painel/jobs"
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.jobs = {}
        self.comparisons = {}
        self.active_comparison_id = None
        self.collect_resources = collect_resources
        self.resource_records = {}
        self.resource_errors = {}
        self.process = None
        self.active_id = None
        self.checking = False
        self.check = None
        self.popen = popen
        self.metric_cache = {}
        for path in sorted(self.root.glob("*.json"), key=lambda item: item.stat().st_mtime):
            try:
                job = read_json(path)
                canonical_uuid(path.stem)
                if job["id"] != path.stem or job["status"] not in STATES:
                    continue
                parameters(job["parameters"])
                if job["status"] in ACTIVE:
                    job.update(status="interrupted", finished_at=now(),
                               message="O painel foi reiniciado; não houve retomada automática.")
                    self.save(job)
                self.jobs[job["id"]] = job
            except (OSError, ValueError, KeyError, TypeError):
                continue
        pairs = self.root.parent / "comparisons"
        pairs.mkdir(exist_ok=True)
        (self.root.parent / "resources").mkdir(exist_ok=True)
        for path in sorted(pairs.glob("*.json"), key=lambda item: item.stat().st_mtime)[-100:]:
            try:
                pair = read_json(path)
                canonical_uuid(path.stem)
                comparison_parameters(pair["parameters"])
                if pair["id"] != path.stem or pair["status"] not in STATES:
                    continue
                if pair["status"] in ACTIVE:
                    pair.update(status="interrupted", finished_at=now(),
                                message="Servidor reiniciado; a sequência não foi retomada.")
                    self.save_pair(pair)
                self.comparisons[pair["id"]] = pair
            except (OSError, ValueError, KeyError, TypeError):
                continue

    def save(self, job):
        path = self.root / (job["id"] + ".json")
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(path)

    def save_pair(self, pair):
        path = self.root.parent / "comparisons" / (pair["id"] + ".json")
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(pair, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(path)

    def environment(self, config=None):
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith(("TCC_DEMO_", "K6_")) and key not in ("BASH_ENV", "ENV")}
        environment.update(TCC_DEMO_DASHBOARD="0", TCC_DEMO_DASHBOARD_PORT="5665",
                           TCC_DEMO_RATE=str((config or {}).get("rate", 5)),
                           TCC_DEMO_SECONDS=str((config or {}).get("seconds", 20)))
        return environment

    def run(self, config):
        config = parameters(config)
        with self.lock:
            if self.active_id or self.active_comparison_id or self.checking:
                raise BusyError("Aguarde o teste ou a verificação em andamento.")
            job = self.new_job(config)
            threading.Thread(target=self.worker, args=(job["id"],), daemon=True).start()
            return dict(job)

    def new_job(self, config, comparison_id=None):
        identity = str(uuid.uuid4())
        job = {"id": identity, "parameters": config, "status": "queued",
               "started_at": now(), "finished_at": None, "session": None,
               "summary": None, "exit_code": None, "k6_exit": None,
               "comparison_id": comparison_id,
               "message": "Verificando o ambiente; nenhuma campanha será iniciada."}
        self.jobs[identity] = job
        self.active_id = identity
        self.save(job)
        return job

    def compare(self, config):
        config = comparison_parameters(config)
        with self.lock:
            if self.active_id or self.active_comparison_id or self.checking:
                raise BusyError("Aguarde a execução em andamento.")
            identity = str(uuid.uuid4())
            pair = {"id": identity, "parameters": config, "status": "queued",
                    "started_at": now(), "finished_at": None, "jobs": {"sync": None, "async": None},
                    "message": "Sequência reservada: síncrono → assíncrono. Mesma taxa/duração, UUIDs distintos."}
            self.comparisons[identity] = pair
            self.active_comparison_id = identity
            self.save_pair(pair)
            threading.Thread(target=self.comparison_worker, args=(identity,), daemon=True).start()
            return dict(pair)

    def comparison_worker(self, identity):
        pair = self.comparisons[identity]
        try:
            for variant in ("sync", "async"):
                with self.lock:
                    if pair.get("stop_reason"):
                        break
                    pair.update(status="running", message=f"Executando {'1/2 síncrono' if variant == 'sync' else '2/2 assíncrono'}; sem cargas simultâneas.")
                    job = self.new_job(dict(pair["parameters"], variant=variant), identity)
                    pair["jobs"][variant] = job["id"]
                    self.save_pair(pair)
                # Synchronous call is deliberate: never overlap the two workloads.
                self.worker(job["id"])
                with self.lock:
                    if job["status"] == "interrupted":
                        pair["stop_reason"] = "Sequência interrompida; a próxima variante não foi iniciada."
                    if not job.get("comparison_evidence_ready") or job.get("k6_exit") not in (0, 99):
                        pair["message"] = "Sequência parou por bloqueio/ausência de evidência íntegra. Não houve reposição ou repetição."
                        break
            with self.lock:
                both = [self.jobs.get(pair["jobs"].get(variant), {}) for variant in ("sync", "async")]
                if pair.get("stop_reason"):
                    pair.update(status="interrupted", message=pair["stop_reason"])
                elif all(job.get("status") == "passed" for job in both):
                    pair.update(status="passed", message="As duas demonstrações terminaram. Compare HTTP e recursos observados; não tempo até commit.")
                else:
                    pair["status"] = "failed"
                    if all(job.get("finished_at") for job in both):
                        pair["message"] = "As duas execuções foram preservadas; ao menos uma falhou. Não há repetição automática."
        except Exception as error:
            pair.update(status="failed", message=f"Falha na sequência: {type(error).__name__}: {error}")
        finally:
            with self.lock:
                if pair.get("stop_reason"):
                    pair.update(status="interrupted", message=pair["stop_reason"])
                pair["finished_at"] = now()
                self.save_pair(pair)
                self.active_comparison_id = None

    def stop_comparison(self, identity, reason="Sequência interrompida; não iniciar a próxima variante."):
        with self.lock:
            pair = self.comparisons[identity]
            if self.active_comparison_id != identity:
                return dict(pair)
            pair.update(status="stopping", stop_reason=reason, message=reason)
            self.save_pair(pair)
            if self.active_id:
                self.stop(self.active_id, reason)
            return dict(pair)

    def resources_worker(self, identity, stopped):
        while not stopped.is_set():
            try:
                with self.lock:
                    job = dict(self.jobs[identity])
                folder = self.folder(job)
                if folder and (folder / "amostras.jsonl.gz").exists():
                    snapshot = resource_snapshot()
                    if not stopped.is_set():
                        with self.lock:
                            records = self.resource_records.setdefault(identity, [])
                            records.append(snapshot)
                            path = self.root.parent / "resources" / (identity + ".json")
                            temporary = path.with_suffix(".tmp")
                            temporary.write_text(json.dumps(records[-40:], ensure_ascii=False), encoding="utf-8")
                            temporary.replace(path)
            except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
                self.resource_errors[identity] = f"Amostra indisponível: {type(error).__name__}"
            stopped.wait(3)

    def folder(self, job):
        if not job.get("session"):
            return None
        session = canonical_uuid(job["session"])
        root = self.app / ".runtime/demonstracao" / session
        variant = job["parameters"]["variant"]
        folders = [path for path in root.glob(f"k6-*-{variant}")
                   if re.fullmatch(f"k6-{UUID_PATTERN}-{variant}", path.name) and not path.is_symlink()]
        return folders[0] if len(folders) == 1 else None

    def worker(self, identity):
        job = self.jobs[identity]
        process = None
        timer = None
        resources_stopped = threading.Event()
        resources_thread = None
        try:
            with self.lock:
                if job["status"] == "stopping":
                    return
                process = self.popen(["bash", str(self.app / "demo/apresentacao.sh"),
                                      "--run-" + job["parameters"]["variant"]],
                                     cwd=self.app, env=self.environment(job["parameters"]),
                                     stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, start_new_session=True)
                self.process = process
                job.update(status="running", message="Executando demonstração local com k6.")
                self.save(job)
            timer = threading.Timer(150, lambda: self.stop(identity, "Tempo limite do executor excedido."))
            timer.daemon = True
            timer.start()
            if self.collect_resources:
                resources_thread = threading.Thread(target=self.resources_worker, args=(identity, resources_stopped), daemon=True)
                resources_thread.start()
            with (self.root / (identity + ".log")).open("wb") as output:
                total = 0
                for raw in iter(process.stdout.readline, b""):
                    # Limit retained console to avoid unbounded child output.
                    line = ANSI.sub("", raw.decode("utf-8", errors="replace")).replace("\r", "")
                    if total < 1_000_000:
                        encoded = line.encode("utf-8")[:8192]
                        output.write(encoded)
                        output.flush()
                        total += len(encoded)
                    match = re.fullmatch("PANEL_SESSION=(" + UUID_PATTERN + ")\\n?", line)
                    if match and job["session"] is None:
                        with self.lock:
                            job["session"] = match[1]
                            self.save(job)
                process.stdout.close()
            code = process.wait(timeout=10)
            with self.lock:
                job["exit_code"] = code
            folder = self.folder(job)
            if folder:
                try:
                    manifest = dict(line.split("=", 1) for line in (folder / "manifest.txt").read_text().splitlines() if "=" in line)
                    job["k6_exit"] = int(manifest["k6_exit"])
                    summary = read_json(folder / "resumo.json")
                    if (any(summary.get(key) != value for key, value in job["parameters"].items())
                            or folder.name != f'k6-{canonical_uuid(summary["run_id"])}-{summary["variant"]}'
                            or manifest.get("run_id") != summary["run_id"]
                            or manifest.get("variant") != summary["variant"]):
                        raise ValueError("Identidade do resumo não corresponde ao teste.")
                    job["summary"] = summary
                    job["comparison_evidence_ready"] = (
                        summary.get("kind") == "presentation_demo_not_definitive"
                        and all(finite(summary.get(key)) for key in ("sent", "errors", "dropped_iterations"))
                        and summary.get("sent", 0) > 0
                        and all(finite(summary.get("http_duration_ms", {}).get(key))
                                for key in ("avg", "med", "p(95)", "p(99)", "max")))
                    verify_k6(summary)
                    if code != 0 or job["k6_exit"] != 0:
                        raise ValueError("O executor/k6 terminou com falha; confira o console.")
                    job.update(status="passed" if job["status"] != "stopping" else "interrupted",
                               message="Teste concluído; verificações HTTP aprovadas.")
                except (OSError, ValueError, KeyError, TypeError) as error:
                    if job["status"] != "stopping":
                        job.update(status="failed", message=str(error))
            elif job["status"] != "stopping":
                job.update(status="failed", message="Teste não executado ou sem resumo. Confira pré-requisitos no console.")
        except Exception as error:
            if job["status"] != "stopping":
                job.update(status="failed", message=f"Falha do executor: {type(error).__name__}: {error}")
        finally:
            resources_stopped.set()
            if resources_thread:
                resources_thread.join(timeout=10)
            if timer:
                timer.cancel()
            if process and process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                    self.kill_later(process)
                except ProcessLookupError:
                    pass
            with self.lock:
                if job.get("stop_reason") or job["status"] in ("stopping", "queued", "running"):
                    job.update(status="interrupted", message=job.get("stop_reason", "Execução interrompida; não aprovada."))
                job["finished_at"] = now()
                self.save(job)
                self.process = None
                self.active_id = None

    def stop(self, identity, reason="Interrompido pelo usuário; evidências preservadas."):
        with self.lock:
            job = self.jobs.get(identity)
            if not job:
                raise KeyError(identity)
            if self.active_id != identity or job["status"] not in ACTIVE:
                return dict(job)
            job.update(status="stopping", stop_reason=reason, message="Interrompendo somente este teste…")
            if job.get("comparison_id"):
                pair = self.comparisons[job["comparison_id"]]
                pair.update(status="stopping", stop_reason=reason, message=reason)
                self.save_pair(pair)
            self.save(job)
            process = self.process
            if process and process.poll() is None:
                # Only the session/process group created by Popen above is targeted.
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                threading.Thread(target=self.kill_later, args=(process,), daemon=True).start()
            return dict(job)

    @staticmethod
    def kill_later(process):
        try:
            process.wait(timeout=12)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    def readiness(self):
        with self.lock:
            if self.active_id or self.active_comparison_id or self.checking:
                raise BusyError("Verificação indisponível durante outro teste/verificação.")
            self.checking = True
        try:
            result = subprocess.run(["bash", str(self.app / "demo/apresentacao.sh"), "--check"],
                                    cwd=self.app, env=self.environment(), stdin=subprocess.DEVNULL,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=45)
            value = {"ok": result.returncode == 0, "at": now(),
                     "message": result.stdout.decode("utf-8", errors="replace")[-6000:]}
        except (OSError, subprocess.TimeoutExpired) as error:
            value = {"ok": False, "at": now(), "message": str(error)}
        finally:
            with self.lock:
                self.checking = False
        with self.lock:
            self.check = value
        return value

    def detail(self, identity):
        with self.lock:
            job = dict(self.jobs[identity])
        folder = self.folder(job)
        if folder:
            cached = self.metric_cache.get(identity)
            if not cached or time.monotonic() - cached[0] >= 1:
                self.metric_cache[identity] = (time.monotonic(), samples(folder / "amostras.jsonl.gz"))
            job["metrics"] = dict(self.metric_cache[identity][1])
            job["evidence"] = str(folder.relative_to(self.app))
        else:
            job["metrics"] = samples(Path("/nonexistent"))
        native = None
        if folder and job.get("summary"):
            try:
                native = read_json(folder / "k6-summary.json")
            except (OSError, ValueError):
                pass
        job["metrics"] = enrich(job["metrics"], job.get("summary"), native, job["parameters"]["seconds"])
        if identity not in self.resource_records:
            try:
                loaded_resources = read_json(self.root.parent / "resources" / (identity + ".json"))
            except (OSError, ValueError):
                loaded_resources = []
            with self.lock:
                self.resource_records.setdefault(identity, loaded_resources)
        with self.lock:
            records = list(self.resource_records.get(identity, []))
        job["resources"] = {"rows": resource_summary(records), "snapshots": len(records),
                            "message": self.resource_errors.get(identity),
                            "scope": "Amostras Docker enquanto o k6 está ativo, incluindo prontidão/drenagem. Não são resultados da campanha nem custo financeiro."}
        job["console"] = tail(self.root / (identity + ".log"))
        return job

    def comparison_detail(self, identity):
        with self.lock:
            pair = dict(self.comparisons[identity])
            jobs = dict(pair["jobs"])
        pair["results"] = {variant: self.detail(job_id) if job_id in self.jobs else None
                           for variant, job_id in jobs.items()}
        return pair

    def snapshot(self):
        with self.lock:
            jobs = sorted(self.jobs.values(), key=lambda value: value["started_at"], reverse=True)[:100]
            comparisons = sorted(self.comparisons.values(), key=lambda value: value["started_at"], reverse=True)[:100]
            return {"active_id": self.active_id, "active_comparison_id": self.active_comparison_id,
                    "checking": self.checking, "check": self.check,
                    "comparisons": [dict(pair) for pair in comparisons], "jobs": [dict(job) for job in jobs]}


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, manager):
        super().__init__(address, Handler)
        self.manager = manager
        self.token = secrets.token_urlsafe(32)
        self.hosts = {f"localhost:{self.server_port}", f"127.0.0.1:{self.server_port}"}


class Handler(BaseHTTPRequestHandler):
    server_version = "TCCDemo/1"

    def setup(self):
        super().setup()
        self.connection.settimeout(8)

    def log_message(self, *_):
        pass

    def respond(self, code, value, content_type="application/json; charset=utf-8"):
        data = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(data)

    def local(self):
        return (self.client_address[0] == "127.0.0.1" and
                len(self.headers.get_all("Host", [])) == 1 and
                self.headers.get("Host") in self.server.hosts)

    def route(self):
        parsed = urlsplit(self.path)
        if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
            raise ValueError("Parâmetros na URL não são aceitos.")
        return parsed.path

    def do_GET(self):
        if not self.local():
            return self.respond(403, {"error": "Acesso somente local."})
        try:
            route = self.route()
            assets = {"/": ("index.html", "text/html"), "/panel.css": ("panel.css", "text/css"),
                      "/dashboard.css": ("dashboard.css", "text/css"),
                      "/panel.js": ("panel.js", "text/javascript")}
            if route in assets:
                name, mime = assets[route]
                return self.respond(200, (ASSETS / name).read_bytes(), mime + "; charset=utf-8")
            if route == "/api/state":
                return self.respond(200, dict(self.server.manager.snapshot(), csrf_token=self.server.token))
            match = re.fullmatch("/api/jobs/(" + UUID_PATTERN + ")", route)
            if match:
                return self.respond(200, self.server.manager.detail(match[1]))
            match = re.fullmatch("/api/comparisons/(" + UUID_PATTERN + ")", route)
            if match:
                return self.respond(200, self.server.manager.comparison_detail(match[1]))
            return self.respond(404, {"error": "Rota não encontrada."})
        except KeyError:
            return self.respond(404, {"error": "Teste não encontrado."})
        except (OSError, ValueError, TypeError):
            return self.respond(400, {"error": "Requisição inválida."})

    def do_POST(self):
        origin = self.headers.get("Origin", "")
        expected = "http://" + self.headers.get("Host", "")
        supplied = self.headers.get("X-CSRF-Token", "")
        if (not self.local() or len(self.headers.get_all("Origin", [])) != 1
                or len(self.headers.get_all("X-CSRF-Token", [])) != 1
                or origin != expected or not supplied.isascii()
                or not hmac.compare_digest(supplied, self.server.token)):
            return self.respond(403, {"error": "Origem/token local inválido. Atualize a página."})
        try:
            if self.headers.get_content_type() != "application/json" or self.headers.get("Transfer-Encoding"):
                return self.respond(415, {"error": "Use application/json com tamanho explícito."})
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 4096:
                return self.respond(413, {"error": "Corpo deve ter entre 1 e 4096 bytes."})
            value = json.loads(self.rfile.read(length))
            route = self.route()
            if route == "/api/run":
                return self.respond(202, self.server.manager.run(value))
            if route == "/api/compare":
                return self.respond(202, self.server.manager.compare(value))
            if value != {}:
                raise ValueError("Esta operação exige JSON vazio {}.")
            if route == "/api/check":
                return self.respond(200, self.server.manager.readiness())
            match = re.fullmatch("/api/jobs/(" + UUID_PATTERN + ")/stop", route)
            if match:
                return self.respond(200, self.server.manager.stop(match[1]))
            match = re.fullmatch("/api/comparisons/(" + UUID_PATTERN + ")/stop", route)
            if match:
                return self.respond(200, self.server.manager.stop_comparison(match[1]))
            return self.respond(404, {"error": "Rota não encontrada."})
        except BusyError as error:
            return self.respond(409, {"error": str(error)})
        except KeyError:
            return self.respond(404, {"error": "Teste não encontrado."})
        except (ValueError, TypeError, UnicodeError) as error:
            return self.respond(400, {"error": str(error)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=5666)
    args = parser.parse_args()
    if os.name != "posix" or not Path("/proc/sys/kernel/random/uuid").exists():
        parser.error("Execute no WSL/Linux: wsl --cd .../implementacao-java -- python3 demo/panel.py")
    if not 1024 <= args.port <= 65535:
        parser.error("Porta deve estar entre 1024 e 65535.")
    import fcntl
    runtime = APP / ".runtime/demonstracao/painel"
    runtime.mkdir(parents=True, exist_ok=True)
    with (runtime / "server.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            parser.exit(1, "Já existe um painel desta cópia em execução. Não iniciei outro.\n")
        manager = Manager()
        try:
            server = Server(("127.0.0.1", args.port), manager)
        except OSError as error:
            parser.exit(1, f"Não foi possível abrir a porta local: {error}\n")
        print(f"Painel local: http://localhost:{args.port}\nMantenha este terminal aberto. Ctrl+C encerra só o painel e seu teste ativo.", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            if manager.active_comparison_id:
                manager.stop_comparison(manager.active_comparison_id, "Painel encerrado; sequência interrompida.")
            elif manager.active_id:
                manager.stop(manager.active_id, "Painel encerrado; teste interrompido, não aprovado.")
            if manager.active_id or manager.active_comparison_id:
                deadline = time.monotonic() + 15
                while (manager.active_id or manager.active_comparison_id) and time.monotonic() < deadline:
                    time.sleep(.1)
        finally:
            server.server_close()


if __name__ == "__main__":
    main()
