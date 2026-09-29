"""Controlled functional faults against this revision's isolated Compose project.

Run in WSL Ubuntu: python3 tests/integration_faults.py --evidence ../../revisao/evidencias_funcionais
This is not an execution of the scientific C1-C5 comparison protocol.
"""
import argparse
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
PROJECT = "tcc-revisao-20260907"
COMPOSE = ["docker", "compose", "--env-file", str(ROOT / ".runtime" / "compose.env"), "-p", PROJECT]
SYNC, ASYNC = "http://localhost:18000", "http://localhost:18001"

KAFKA_SNAPSHOT = '''
import json, sys
from confluent_kafka import Consumer, TopicPartition
from app.shared.config import KAFKA_BOOTSTRAP_SERVERS,KAFKA_TOPIC,KAFKA_DLQ_TOPIC,KAFKA_GROUP_ID
c=Consumer({"bootstrap.servers":KAFKA_BOOTSTRAP_SERVERS,"group.id":KAFKA_GROUP_ID,"enable.auto.commit":False,"log_level":0})
if sys.argv[1]=="lag":
 p=TopicPartition(KAFKA_TOPIC,0)
 low,high=c.get_watermark_offsets(p,timeout=5)
 committed=c.committed([p],timeout=5)[0].offset
 print(json.dumps({"low":low,"high":high,"committed":committed,"lag":max(0,high-max(committed,low))}))
else:
 p=TopicPartition(KAFKA_DLQ_TOPIC,0)
 low,high=c.get_watermark_offsets(p,timeout=5)
 c.assign([TopicPartition(KAFKA_DLQ_TOPIC,0,low)])
 found=[]
 import time
 end=time.monotonic()+8
 while low<high and time.monotonic()<end:
  m=c.poll(.2)
  if m is None or m.error():continue
  data=json.loads(m.value())
  if data.get("run_id")==sys.argv[2]:found.append(data)
  if m.offset()>=high-1:break
 print(json.dumps(found))
c.close()
'''

SQL_SNAPSHOT = '''
import json,sys
from uuid import UUID
from sqlalchemy import select
from app.shared.database import AuditRecord,engine
with engine.connect() as c:
 rows=c.execute(select(AuditRecord.event_id,AuditRecord.content_hash,AuditRecord.persisted_at)
  .where(AuditRecord.event_id.in_([UUID(x) for x in json.loads(sys.argv[1])]))).mappings().all()
print(json.dumps([dict(row) for row in rows],default=str))
'''

PUBLISH_INVALID = '''
import json,sys
from app.shared.kafka import KafkaPublisher
from app.shared.config import KAFKA_TOPIC
p=KafkaPublisher()
r=p.publish(KAFKA_TOPIC,b"synthetic-invalid-json",key=b"functional-verification",headers=[("x-run-id",sys.argv[1].encode())])
print(json.dumps({"topic":r.topic,"partition":r.partition,"offset":r.offset}))
p.close()
'''


class FunctionalValidation:
    def __init__(self, destination):
        self.run_id = str(uuid4())
        self.destination = destination.resolve()
        if self.destination.exists() and any(self.destination.iterdir()):
            self.destination = self.destination / ("run_" + self.run_id)
        self.destination.mkdir(parents=True, exist_ok=True)
        self.started = datetime.now(timezone.utc).isoformat()
        self.http, self.commands, self.events, self.checks = [], [], [], []

    def command(self, *args, timeout=90):
        started = time.monotonic()
        result = subprocess.run(COMPOSE + list(args), cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        self.commands.append({"operation": list(args[:3]), "exit_code": result.returncode,
                              "elapsed_seconds": time.monotonic() - started,
                              "timestamp": datetime.now(timezone.utc).isoformat()})
        if result.returncode:
            # Do not expose library/Compose stderr that could contain environment details.
            raise RuntimeError(f"compose_command_failed:{args[0]}:{result.returncode}")
        return result.stdout

    def helper(self, code, *args):
        output = self.command("exec", "-T", "async-api", "python", "-c", code, *args)
        return json.loads(output.strip().splitlines()[-1])

    def request(self, variant, path, body=None):
        url = (SYNC if variant == "sync" else ASYNC) + path
        data = json.dumps(body).encode() if body is not None else None
        request = Request(url, data=data, headers={"Content-Type": "application/json", "X-Run-ID": self.run_id})
        started = time.perf_counter_ns()
        try:
            with urlopen(request, timeout=20) as response:
                code, result = response.status, json.loads(response.read())
        except HTTPError as exc:
            code, result = exc.code, json.loads(exc.read())
        except (URLError, TimeoutError):
            code, result = 0, {"reason": "client_transport_failure", "acceptance": "unknown"}
        elapsed = (time.perf_counter_ns() - started) / 1e6
        self.http.append({"timestamp": datetime.now(timezone.utc).isoformat(), "variant": variant,
                          "method": "POST" if body is not None else "GET", "path": path,
                          "request": body, "http_status": code, "response": result,
                          "client_observed_ms": elapsed})
        return code, result

    def new_event(self, label):
        value = {"event_id": str(uuid4()), "event_type": "record.changed", "entity_type": "synthetic",
                 "entity_id": "functional-verification", "actor_id": "synthetic-actor",
                 "source": "functional-verification", "occurred_at": datetime.now(timezone.utc).isoformat(),
                 "payload": {"case": label}}
        self.events.append(value)
        return value

    def require(self, label, condition, **evidence):
        self.checks.append({"check": label, "passed": bool(condition), **evidence})
        if not condition:
            raise AssertionError(label)

    def until(self, predicate, timeout=75):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            result = predicate()
            if result:
                return result
            time.sleep(0.5)
        raise TimeoutError("functional_observation_deadline")

    def health(self):
        for variant in ("sync", "async"):
            self.until(lambda: self.request(variant, "/health")[0] == 200)

    def record(self, value):
        return self.until(lambda: self.request("sync", "/audit/" + value["event_id"])[0] == 200)

    def logs(self):
        raw = self.command("logs", "--no-color", "--no-log-prefix", "--since", self.started,
                           "sync-api", "async-api", "consumer")
        found = []
        for line in raw.splitlines():
            try:
                value = json.loads(line)
            except ValueError:
                continue
            if value.get("run_id") == self.run_id and "milestone" in value:
                found.append(value)
        return found

    def execute(self):
        self.health()
        self.command("stop", "consumer")
        backlog_events = [self.new_event("consumer_stopped") for _ in range(3)]
        for body in backlog_events:
            self.require("accepted_while_consumer_stopped", self.request("async", "/audit", body)[0] == 202)
            self.require("not_persisted_before_consumer_restart",
                         self.request("sync", "/audit/" + body["event_id"])[0] == 404)
        lag_before = self.helper(KAFKA_SNAPSHOT, "lag")
        self.require("backlog_contains_three_accepted_events", lag_before["lag"] >= 3, observation=lag_before)
        self.command("start", "consumer")
        for body in backlog_events:
            self.record(body)
        lag_after = self.until(lambda: (value if value["lag"] == 0 else None)
                               if (value := self.helper(KAFKA_SNAPSHOT, "lag")) is not None else None)
        self.require("backlog_drained_after_consumer_restart", lag_after["lag"] == 0, observation=lag_after)

        self.command("stop", "kafka")
        uncertain = self.new_event("broker_stopped")
        code, result = self.request("async", "/audit", uncertain)
        self.require("broker_outage_does_not_return_202", code == 503, http_status=code, response=result)
        self.require("broker_outage_preserves_uncertainty", result.get("detail", {}).get("acceptance") == "unknown")
        self.command("start", "kafka")
        self.until(lambda: self.request("async", "/health")[0] == 200)
        after_kafka = self.new_event("broker_restored")
        self.require("publication_recovers_after_broker_restart", self.request("async", "/audit", after_kafka)[0] == 202)
        self.record(after_kafka)
        unknown_status = self.request("sync", "/audit/" + uncertain["event_id"])[0]
        self.checks.append({"check": "uncertain_request_reconciled_by_observation", "passed": True,
                            "http_status_on_lookup": unknown_status,
                            "interpretation": "visible" if unknown_status == 200 else "not_observed; no blind retry"})

        self.command("stop", "postgres")
        self.require("readiness_detects_database_outage", self.request("sync", "/health")[0] == 503)
        database_failure = self.new_event("database_stopped")
        self.require("broker_accepts_during_database_outage", self.request("async", "/audit", database_failure)[0] == 202)
        dead = self.until(lambda: next((entry for entry in self.helper(KAFKA_SNAPSHOT, "dlq", self.run_id)
                                      if entry.get("event_id") == database_failure["event_id"]), None))
        self.require("database_retries_exhausted_to_dlq", dead["reason"] == "persistence_retries_exhausted"
                     and dead["attempts"] == 3, dlq=dead)
        retry_logs = [entry for entry in self.logs() if entry["milestone"] == "retry_scheduled"
                      and entry.get("event_id") == database_failure["event_id"]]
        self.require("real_retry_backoff_observed", len(retry_logs) == 2,
                     delays=[entry["delay_seconds"] for entry in retry_logs])
        self.command("start", "postgres")
        self.until(lambda: self.request("sync", "/health")[0] == 200)
        recovered = self.new_event("database_restored")
        self.require("database_recovery_accepts_new_event", self.request("async", "/audit", recovered)[0] == 202)
        self.record(recovered)
        self.require("dlq_event_is_not_falsely_counted_as_persisted",
                     self.request("sync", "/audit/" + database_failure["event_id"])[0] == 404)

        invalid_source = self.helper(PUBLISH_INVALID, self.run_id)
        source_id = f"{invalid_source['topic']}:{invalid_source['partition']}:{invalid_source['offset']}"
        invalid_dead = self.until(lambda: next((entry for entry in self.helper(KAFKA_SNAPSHOT, "dlq", self.run_id)
                                               if entry.get("source_message_id") == source_id), None))
        self.require("invalid_wire_message_reaches_dlq", invalid_dead["reason"] == "invalid_event")
        following = self.new_event("valid_after_invalid")
        self.require("invalid_message_does_not_poison_following_record",
                     self.request("async", "/audit", following)[0] == 202)
        self.record(following)

        duplicate = self.request("sync", "/audit", following)
        self.require("cross_path_idempotence_is_visible", duplicate[0] == 201
                     and duplicate[1].get("status") == "duplicate", response=duplicate[1])
        changed = {**following, "payload": {"case": "conflicting_content"}}
        self.require("cross_path_conflict_is_rejected", self.request("sync", "/audit", changed)[0] == 409)
        self.health()

    def save(self, failure=None):
        def write(name, content):
            (self.destination / name).write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
        write("http_requests_responses.json", self.http)
        write("synthetic_events.json", self.events)
        try:
            logs = self.logs()
            (self.destination / "application_milestones.jsonl").write_text(
                "\n".join(json.dumps(entry, ensure_ascii=False) for entry in logs) + "\n", encoding="utf-8")
            write("postgresql_rows.json", self.helper(SQL_SNAPSHOT, json.dumps([e["event_id"] for e in self.events])))
            write("kafka_final_lag.json", self.helper(KAFKA_SNAPSHOT, "lag"))
            write("dead_letter_records.json", self.helper(KAFKA_SNAPSHOT, "dlq", self.run_id))
        except Exception as exc:
            write("evidence_collection_failure.json", {"type": type(exc).__name__})
            failure = failure or "evidence_collection_failed:" + type(exc).__name__
        write("compose_operations.json", self.commands)
        write("verification_summary.json", {"classification": "controlled_functional_verification_not_C1_C5",
                                           "run_id": self.run_id, "started_at": self.started,
                                           "finished_at": datetime.now(timezone.utc).isoformat(),
                                           "passed": failure is None and all(c["passed"] for c in self.checks),
                                           "failure": failure, "checks": self.checks})
        return failure


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    validation = FunctionalValidation(args.evidence)
    failure = None
    try:
        validation.execute()
    except Exception as exc:
        failure = type(exc).__name__ + ":" + str(exc)
    finally:
        try:
            validation.command("start", "postgres", "kafka", "consumer")
            validation.health()
        except Exception:
            failure = failure or "service_restoration_failed"
        failure = validation.save(failure)
    print(json.dumps({"run_id": validation.run_id, "passed": failure is None,
                      "checks": len(validation.checks), "failure": failure}))
    return 1 if failure else 0


if __name__ == "__main__":
    raise SystemExit(main())
