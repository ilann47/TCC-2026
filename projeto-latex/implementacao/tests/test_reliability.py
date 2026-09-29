"""Unit tests with explicit doubles; these are not distributed integration tests."""
import json
import time
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.async_api import main as async_api
from app.consumer.main import RetrySession, handle_message
from app.shared import observability
from app.shared.database import EventConflict
from app.shared.kafka import DeliveryReceipt, KafkaPublisher, PublicationFailure
from app.shared.processing import canonical_event
from app.shared.schemas import AuditStored
from app.sync_api import main as sync_api
from tests.test_processing import sample_event


class Message:
    def __init__(self, value=None):
        self._value = canonical_event(sample_event()).encode() if value is None else value
    def value(self): return self._value
    def key(self): return b"42"
    def topic(self): return "audit-events"
    def partition(self): return 0
    def offset(self): return 17
    def headers(self): return [("x-run-id", b"12345678-1234-5678-1234-567812345678")]


class ControlledProducer:
    def __init__(self, error=None, never_ack=False, full=False):
        self.callback = None
        self.polls, self.error, self.never_ack, self.full = 0, error, never_ack, full
    def produce(self, *args, **kwargs):
        if self.full:
            raise BufferError("sensitive queue details")
        self.callback = kwargs["on_delivery"]
    def poll(self, timeout):
        self.polls += 1
        if self.never_ack:
            time.sleep(timeout)
        elif self.polls == 2:
            self.callback(self.error, Message())


def test_publisher_waits_for_specific_delivery_callback():
    producer = ControlledProducer()
    receipt = KafkaPublisher(producer, timeout=0.2).publish("audit-events", b"{}")
    assert producer.polls == 2
    assert receipt == DeliveryReceipt("audit-events", 0, 17)


@pytest.mark.parametrize("mode,acceptance,reason", [
    ({"never_ack": True}, "unknown", "delivery_timeout"),
    ({"error": object()}, "unknown", "delivery_failed"),
    ({"full": True}, "rejected", "producer_buffer_full"),
])
def test_publication_failure_is_not_an_ack(mode, acceptance, reason):
    with pytest.raises(PublicationFailure) as failure:
        KafkaPublisher(ControlledProducer(**mode), timeout=0.01).publish("audit-events", b"{}")
    assert (failure.value.acceptance, failure.value.reason) == (acceptance, reason)


class SourceConsumer:
    def __init__(self, trace, fail_commit=False):
        self.trace, self.fail_commit = trace, fail_commit
    def commit(self, message, asynchronous):
        assert asynchronous is False
        self.trace.append("commit")
        return [SimpleNamespace(error=object() if self.fail_commit else None)]


class DLQPublisher:
    def __init__(self, trace, fail=False):
        self.trace, self.fail, self.envelopes = trace, fail, []
    def publish(self, topic, key, value, headers=None):
        self.trace.append("dlq")
        self.envelopes.append(json.loads(value))
        if self.fail:
            raise PublicationFailure("unknown", "delivery_timeout")
        return DeliveryReceipt(topic, 0, 0)


def stored(event):
    return AuditStored(event_id=event.event_id, status="persisted", content_hash="a" * 64)


def db_unavailable(event):
    raise OperationalError("private SQL payload", {}, Exception("secret password"))


def test_consumer_retries_then_commits_after_persistence():
    trace, waits = [], []
    def eventual(event):
        trace.append("persist")
        if trace.count("persist") < 3:
            return db_unavailable(event)
        return stored(event)
    assert handle_message(SourceConsumer(trace), DLQPublisher(trace), Message(),
                          persist=eventual, wait=waits.append) == "persisted"
    assert trace == ["persist", "persist", "persist", "commit"]
    assert waits == [0.5, 1.0]


def test_exhausted_retry_goes_to_acknowledged_dlq_before_commit():
    trace, waits = [], []
    publisher = DLQPublisher(trace)
    assert handle_message(SourceConsumer(trace), publisher, Message(), persist=db_unavailable,
                          wait=waits.append) == "dlq"
    assert trace == ["dlq", "commit"]
    assert publisher.envelopes[0]["attempts"] == 3
    assert publisher.envelopes[0]["reason"] == "persistence_retries_exhausted"
    assert publisher.envelopes[0]["source_message_id"] == "audit-events:0:17"


def test_invalid_event_does_not_reach_database():
    trace = []
    def forbidden(_):
        pytest.fail("Invalid event reached persistence")
    assert handle_message(SourceConsumer(trace), DLQPublisher(trace), Message(b"invalid-json"),
                          persist=forbidden) == "dlq"
    assert trace == ["dlq", "commit"]


@pytest.mark.parametrize("missing", ["event_id", "occurred_at"])
def test_incomplete_wire_contract_never_generates_identity_on_replay(missing):
    trace = []
    body = sample_event().model_dump(mode="json")
    body.pop(missing)
    message = Message(json.dumps(body).encode())
    def forbidden(_): pytest.fail("Incomplete source record must not reach database")
    for _ in range(2):
        assert handle_message(SourceConsumer(trace), DLQPublisher(trace), message, persist=forbidden) == "dlq"
    assert trace == ["dlq", "commit", "dlq", "commit"]


def test_dlq_failure_never_commits_source_offset():
    trace = []
    with pytest.raises(RetrySession):
        handle_message(SourceConsumer(trace), DLQPublisher(trace, fail=True), Message(b"invalid"))
    assert trace == ["dlq"]


def test_offset_commit_error_interrupts_session_for_replay():
    trace = []
    with pytest.raises(RetrySession):
        handle_message(SourceConsumer(trace, fail_commit=True), DLQPublisher(trace), Message(), persist=stored)
    assert trace == ["commit"]


def test_conflicting_id_is_terminal_and_goes_to_dlq_without_retry():
    trace = []
    def conflict(_): raise EventConflict()
    publisher = DLQPublisher(trace)
    assert handle_message(SourceConsumer(trace), publisher, Message(), persist=conflict,
                          wait=lambda _: pytest.fail("Conflict must not retry")) == "dlq"
    assert publisher.envelopes[0]["reason"] == "event_id_content_conflict"
    assert trace == ["dlq", "commit"]


def test_unexpected_processing_error_does_not_commit():
    trace = []
    def programming_error(_): raise RuntimeError("internal sensitive details")
    with pytest.raises(RuntimeError):
        handle_message(SourceConsumer(trace), DLQPublisher(trace), Message(), persist=programming_error)
    assert not trace


def test_sync_conflict_maps_to_409_without_leaking_details(monkeypatch):
    def conflict(_): raise EventConflict("private content")
    monkeypatch.setattr(sync_api, "persist_event", conflict)
    response = TestClient(sync_api.app).post("/audit", json=sample_event().model_dump(mode="json"))
    assert response.status_code == 409
    assert "private" not in response.text


def test_sync_database_failure_is_503_with_unknown_outcome(monkeypatch):
    monkeypatch.setattr(sync_api, "persist_event", db_unavailable)
    response = TestClient(sync_api.app).post("/audit", json=sample_event().model_dump(mode="json"))
    assert response.status_code == 503
    assert response.json()["detail"]["acceptance"] == "unknown"
    assert "secret" not in response.text


def test_async_202_requires_publish_receipt_and_propagates_run_id(monkeypatch):
    class Acknowledged:
        def publish(self, topic, key, value, headers):
            assert headers == [("x-run-id", run_id.encode())]
            return DeliveryReceipt(topic, 0, 1)
    run_id = str(uuid4())
    monkeypatch.setattr(async_api, "publisher", Acknowledged())
    response = TestClient(async_api.app).post("/audit", json=sample_event().model_dump(mode="json"),
                                              headers={"X-Run-ID": run_id})
    assert response.status_code == 202


def test_async_ambiguous_timeout_is_503_not_202(monkeypatch):
    class Unconfirmed:
        def publish(self, *args, **kwargs): raise PublicationFailure("unknown", "delivery_timeout")
    monkeypatch.setattr(async_api, "publisher", Unconfirmed())
    response = TestClient(async_api.app).post("/audit", json=sample_event().model_dump(mode="json"))
    assert response.status_code == 503
    assert response.json()["detail"]["acceptance"] == "unknown"


def test_liveness_is_distinct_from_readiness(monkeypatch):
    monkeypatch.setattr(sync_api, "database_ready", lambda: False)
    client = TestClient(sync_api.app)
    assert client.get("/live").status_code == 200
    assert client.get("/health").status_code == 503
    monkeypatch.setattr(async_api, "publisher", None)
    assert TestClient(async_api.app).get("/health").status_code == 503


def test_structured_logs_filter_unapproved_fields(monkeypatch):
    messages = []
    monkeypatch.setattr(observability.log, "info", messages.append)
    observability.milestone("test", event_id=uuid4(), payload={"password": "secret"},
                            credentials="token", reason="controlled_reason")
    entry = json.loads(messages[0])
    assert "secret" not in messages[0]
    assert "credentials" not in entry
    assert entry["wall_time_ns"] > 0 and entry["monotonic_ns"] > 0


def test_invalid_tracking_header_is_rejected(monkeypatch):
    response = TestClient(sync_api.app).get("/live", headers={"X-Run-ID": "not-a-uuid"})
    assert response.status_code == 400
