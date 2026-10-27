"""Read-only, bounded projections of local demo evidence; no campaign inputs."""
import json
import math
import re
import statistics
import subprocess
import zlib
from datetime import datetime, timezone


def finite(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def percentile(values, probability):
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower, upper = math.floor(position), math.ceil(position)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def read_samples(path):
    result = {"sent": None, "errors": None, "dropped_iterations": None,
              "http_p95_ms": None, "latency_ms": {}, "series": [], "statuses": {},
              "http_observed": None, "http_failures": None, "checks_passed": None,
              "checks_failed": None, "stages_ms": {}, "vus_peak": None,
              "raw_complete": False, "provisional": True}
    try:
        with path.open("rb") as stream:
            compressed = stream.read(4_000_001)
        decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
        data = decoder.decompress(compressed[:4_000_000], 16_000_000)
        result["raw_complete"] = decoder.eof and len(compressed) <= 4_000_000
    except (OSError, zlib.error):
        return result
    counters, timings, buckets, stages, checks = {}, [], {}, {}, []
    failures = []
    for line in data.split(b"\n")[:-1]:
        try:
            point = json.loads(line)
            item, metric = point.get("data", {}), point.get("metric")
            value = item.get("value")
            if point.get("type") != "Point" or not finite(value):
                continue
            if metric in ("demo_sent", "demo_errors", "dropped_iterations"):
                counters[metric] = counters.get(metric, 0) + value
            if metric == "vus":
                result["vus_peak"] = max(value, result["vus_peak"] or 0)
            tags = item.get("tags", {})
            if tags.get("phase") != "demo":
                continue
            if metric == "checks":
                checks.append(value)
            if metric == "http_req_failed":
                failures.append(value)
            if metric in ("http_req_blocked", "http_req_connecting", "http_req_sending", "http_req_waiting", "http_req_receiving"):
                stages.setdefault(metric, []).append(value)
            if metric == "http_req_duration":
                timings.append(value)
                status = str(tags.get("status", ""))
                if re.fullmatch(r"[1-5][0-9]{2}|0", status):
                    result["statuses"][status] = result["statuses"].get(status, 0) + 1
                stamp = datetime.fromisoformat(item.get("time", "").replace("Z", "+00:00"))
                if stamp.tzinfo is not None:
                    second = stamp.astimezone(timezone.utc).replace(microsecond=0).isoformat()
                    buckets.setdefault(second, []).append(value)
        except (ValueError, TypeError, AttributeError):
            continue
    result.update(sent=counters.get("demo_sent"), errors=counters.get("demo_errors"),
                  dropped_iterations=counters.get("dropped_iterations"))
    if timings:
        result["latency_ms"] = {"min": min(timings), "avg": statistics.mean(timings),
                                "med": statistics.median(timings), "p(95)": percentile(timings, .95),
                                "p(99)": percentile(timings, .99), "max": max(timings)}
        result["http_p95_ms"] = result["latency_ms"]["p(95)"]
        result["http_observed"] = len(timings)
    if failures:
        result["http_failures"] = sum(failures)
        result["http_failure_pct"] = statistics.mean(failures) * 100
    if checks:
        result.update(checks_passed=sum(value == 1 for value in checks),
                      checks_failed=sum(value != 1 for value in checks))
    result["stages_ms"] = {metric.removeprefix("http_req_"): statistics.mean(values)
                            for metric, values in stages.items()}
    result["series"] = [{"time": key, "avg_ms": statistics.mean(values),
                         "p95_ms": percentile(values, .95), "count": len(values)}
                        for key, values in sorted(buckets.items())][-60:]
    return result


def enrich(metrics, summary, native, seconds):
    """Pure projection: final demo summary wins; global generator metrics labeled separately."""
    result = dict(metrics)
    result["latency_ms"] = dict(metrics.get("latency_ms", {}))
    if summary:
        result.update(sent=summary.get("sent"), errors=summary.get("errors"),
                      dropped_iterations=summary.get("dropped_iterations"), provisional=False)
        result["latency_ms"].update(summary.get("http_duration_ms", {}))
        result["http_p95_ms"] = result["latency_ms"].get("p(95)")
    if finite(result.get("sent")):
        result["send_rate_window"] = result["sent"] / seconds
    sent, errors = result.get("sent"), result.get("errors")
    if finite(sent) and sent > 0 and finite(errors):
        result["invalid_pct"] = errors / sent * 100
    native_metrics = (native or {}).get("metrics", {})

    def native_value(name, field):
        value = native_metrics.get(name, {}).get("values", {}).get(field)
        return value if finite(value) else None

    # These explicitly include readiness and are not HTTP-only event metrics.
    result["generator"] = {"http_total": native_value("http_reqs", "count"),
                           "bytes_sent": native_value("data_sent", "count"),
                           "bytes_received": native_value("data_received", "count"),
                           "vus_available": native_value("vus_max", "max"),
                           "vus_sampled_peak": native_value("vus", "max")}
    checks = native_metrics.get("checks{phase:demo}", {}).get("values", {})
    if checks:
        result.update(checks_passed=checks.get("passes"), checks_failed=checks.get("fails"))
    failure_rate = native_value("http_req_failed{phase:demo}", "rate")
    if failure_rate is not None:
        result["http_failure_pct"] = failure_rate * 100
    return result


def memory_mib(value):
    match = re.fullmatch(r"([0-9.]+)\s*(B|kB|KB|KiB|MB|MiB|GB|GiB)", value.strip())
    if not match:
        raise ValueError("Unidade de memória desconhecida")
    amount = float(match[1])
    if not finite(amount):
        raise ValueError("Memória inválida")
    factor = {"B": 1, "kB": 1000, "KB": 1000, "KiB": 1024, "MB": 10**6,
              "MiB": 1024**2, "GB": 10**9, "GiB": 1024**3}[match[2]]
    return amount * factor / 1024**2


def resource_snapshot(run=subprocess.run):
    """Read only this Compose project's verified containers. Never output inspect env/paths."""
    def command(args):
        result = run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3, check=True)
        return result.stdout.decode("utf-8")

    identities = command(["docker", "ps", "-q", "--filter", "label=com.docker.compose.project=tcc-java-2026"]).split()
    if not identities or len(identities) > 8 or any(not re.fullmatch(r"[0-9a-f]{12,64}", value) for value in identities):
        raise ValueError("Contêineres da demonstração não identificados")
    info = command(["docker", "inspect", "--format", '{{.Id}} {{json .Config.Labels}}', *identities])
    services = {}
    allowed = {"sync-api", "async-api", "consumer", "kafka", "postgres"}
    for line in info.splitlines():
        identity, labels = line.split(" ", 1)
        labels = json.loads(labels)
        service = labels.get("com.docker.compose.service")
        if (re.fullmatch(r"[0-9a-f]{12,64}", identity) and service in allowed
                and labels.get("com.docker.compose.project") == "tcc-java-2026"):
            if service in services.values():
                raise ValueError("Serviço duplicado; amostra recusada")
            services[identity] = service
    if len(services) != 5:
        raise ValueError("Esperados os cinco serviços da demonstração")
    stats = command(["docker", "stats", "--no-stream", "--format", '{{json .}}', *services])
    rows = []
    for line in stats.splitlines():
        item = json.loads(line)
        identity = item.get("ID", item.get("Container", ""))
        matches = [service for key, service in services.items() if key.startswith(identity) and len(identity) >= 12]
        if len(matches) != 1:
            raise ValueError("Amostra de contêiner desconhecido")
        cpu = float(item["CPUPerc"].removesuffix("%"))
        if not finite(cpu):
            raise ValueError("CPU inválida")
        rows.append({"service": matches[0], "cpu_pct": cpu,
                     "memory_mib": memory_mib(item["MemUsage"].split("/", 1)[0])})
    if len(rows) != 5 or len({row["service"] for row in rows}) != 5:
        raise ValueError("Amostra incompleta")
    return {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "services": rows}


def resource_summary(snapshots):
    rows = []
    for service in ("sync-api", "async-api", "consumer", "postgres", "kafka"):
        values = [row for snapshot in snapshots for row in snapshot["services"] if row["service"] == service]
        if values:
            rows.append({"service": service, "samples": len(values),
                         "cpu_avg_pct": statistics.mean(row["cpu_pct"] for row in values),
                         "cpu_peak_pct": max(row["cpu_pct"] for row in values),
                         "memory_avg_mib": statistics.mean(row["memory_mib"] for row in values),
                         "memory_peak_mib": max(row["memory_mib"] for row in values)})
    return rows
