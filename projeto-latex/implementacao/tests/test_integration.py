"""Real services only. Opt in with RUN_INTEGRATION=1 in an isolated Compose project."""
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from uuid import uuid4

import httpx
import pytest
from confluent_kafka import Consumer, TopicPartition
from sqlalchemy import func, select

from app.shared.config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_DLQ_TOPIC, KAFKA_TOPIC
from app.shared.database import AuditRecord, engine
from app.shared.kafka import KafkaPublisher


pytestmark = [pytest.mark.integration,
              pytest.mark.skipif(os.getenv("RUN_INTEGRATION") != "1", reason="Real services not explicitly enabled")]
SYNC = os.getenv("SYNC_BASE_URL", "http://localhost:18000")
ASYNC = os.getenv("ASYNC_BASE_URL", "http://localhost:18001")


def event():
    return {"event_id": str(uuid4()), "event_type": "record.changed", "entity_type": "synthetic",
            "entity_id": "integration-test", "actor_id": "synthetic-actor", "source": "integration-test",
            "occurred_at": datetime.now(timezone.utc).isoformat(), "payload": {"value": 1}}


@pytest.fixture(scope="module")
def client():
    with httpx.Client(timeout=20) as current:
        assert current.get(f"{SYNC}/health").status_code == 200
        assert current.get(f"{ASYNC}/health").status_code == 200
        yield current


def wait_record(client, event_id, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(f"{SYNC}/audit/{event_id}")
        if response.status_code == 200:
            return response.json()
        assert response.status_code in (404, 503)
        time.sleep(0.1)
    pytest.fail("Committed record was not observed before the integration deadline")


def read_new_topic(topic):
    consumer = Consumer({"bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
                         "group.id": f"integration-observer-{uuid4()}", "enable.auto.commit": False,
                         "enable.auto.offset.store": False, "log_level": 0})
    _, high = consumer.get_watermark_offsets(TopicPartition(topic, 0), timeout=10)
    consumer.assign([TopicPartition(topic, 0, high)])
    return consumer


def wait_message(consumer, predicate, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        message = consumer.poll(0.2)
        if message is not None and not message.error():
            data = json.loads(message.value())
            if predicate(data):
                return data
    pytest.fail("Expected real Kafka record not observed")


def test_concurrent_duplicate_requests_preserve_one_row(client):
    body, run_id = event(), str(uuid4())
    with ThreadPoolExecutor(max_workers=8) as executor:
        responses = list(executor.map(lambda _: client.post(f"{SYNC}/audit", json=body,
                              headers={"X-Run-ID": run_id}), range(8)))
    assert all(response.status_code == 201 for response in responses)
    statuses = [response.json()["status"] for response in responses]
    assert statuses.count("persisted") == 1
    assert statuses.count("duplicate") == 7
    assert len({response.json()["content_hash"] for response in responses}) == 1
    with engine.connect() as connection:
        count = connection.execute(select(func.count()).select_from(AuditRecord).where(
            AuditRecord.event_id == body["event_id"])).scalar_one()
    assert count == 1


def test_conflict_returns_409_and_preserves_original_row(client):
    body = event()
    original = client.post(f"{SYNC}/audit", json=body)
    assert original.status_code == 201
    body["payload"]["value"] = 999
    response = client.post(f"{SYNC}/audit", json=body)
    assert response.status_code == 409
    record = wait_record(client, body["event_id"])
    assert record["content_hash"] == original.json()["content_hash"]


def test_async_ack_publication_and_eventual_committed_persistence(client):
    body, run_id = event(), str(uuid4())
    observer = read_new_topic(KAFKA_TOPIC)
    try:
        response = client.post(f"{ASYNC}/audit", json=body, headers={"X-Run-ID": run_id})
        assert response.status_code == 202
        published = wait_message(observer, lambda value: value.get("event_id") == body["event_id"])
        assert published["payload"] == body["payload"]
        stored = wait_record(client, body["event_id"])
        assert stored["persisted_at"] is not None
        duplicate = client.post(f"{SYNC}/audit", json=body)
        assert duplicate.status_code == 201 and duplicate.json()["status"] == "duplicate"
        assert duplicate.json()["content_hash"] == stored["content_hash"]
    finally:
        observer.close()


def test_invalid_kafka_record_is_observable_in_dlq(client):
    observer = read_new_topic(KAFKA_DLQ_TOPIC)
    publisher = KafkaPublisher()
    try:
        source = publisher.publish(KAFKA_TOPIC, b"invalid-integration-json", key=str(uuid4()).encode())
        expected = f"{source.topic}:{source.partition}:{source.offset}"
        dead = wait_message(observer, lambda value: value.get("source_message_id") == expected)
        assert dead["reason"] == "invalid_event"
        assert dead["attempts"] == 0
    finally:
        observer.close()
        publisher.close()


def test_async_content_conflict_is_sent_to_dlq(client):
    body = event()
    original = client.post(f"{SYNC}/audit", json=body)
    assert original.status_code == 201
    observer = read_new_topic(KAFKA_DLQ_TOPIC)
    try:
        body["payload"]["value"] = 999
        assert client.post(f"{ASYNC}/audit", json=body).status_code == 202
        dead = wait_message(observer, lambda value: value.get("event_id") == body["event_id"])
        assert dead["reason"] == "event_id_content_conflict"
        assert wait_record(client, body["event_id"])["content_hash"] == original.json()["content_hash"]
    finally:
        observer.close()
