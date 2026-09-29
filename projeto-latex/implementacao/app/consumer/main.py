import base64
import json
import signal
from datetime import datetime, timezone
from threading import Event
from time import sleep

from confluent_kafka import Consumer, KafkaError, KafkaException
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.shared.config import (
    KAFKA_BOOTSTRAP_SERVERS, KAFKA_DLQ_TOPIC, KAFKA_GROUP_ID, KAFKA_TOPIC,
    RECONNECT_SECONDS, RETRY_ATTEMPTS, RETRY_BACKOFF_MAX_SECONDS, RETRY_BACKOFF_SECONDS,
)
from app.shared.database import EventConflict, initialize_database, persist_event
from app.shared.kafka import KafkaPublisher, PublicationFailure
from app.shared.observability import milestone, run_context, valid_run_id, variant_context
from app.shared.schemas import AuditEvent


class RetrySession(Exception):
    """Stop this session without advancing past an unresolved source record."""


def commit_message(consumer, message) -> None:
    try:
        partitions = consumer.commit(message=message, asynchronous=False)
        if not partitions or any(part.error is not None for part in partitions):
            raise RetrySession("offset_commit_unconfirmed")
    except KafkaException as exc:
        raise RetrySession("offset_commit_unconfirmed") from exc
    milestone("offset_committed", topic=message.topic(), partition=message.partition(), offset=message.offset())


def send_to_dlq(consumer, publisher, message, reason: str, attempts: int, event_id=None) -> None:
    identity = f"{message.topic()}:{message.partition()}:{message.offset()}"
    envelope = {
        "source_message_id": identity, "source_topic": message.topic(),
        "source_partition": message.partition(), "source_offset": message.offset(),
        "reason": reason, "attempts": attempts, "event_id": str(event_id) if event_id else None,
        "failed_at": datetime.now(timezone.utc).isoformat(), "run_id": run_context.get(),
        "original_value_base64": (base64.b64encode(message.value()).decode("ascii")
                                  if message.value() is not None else None),
        "original_key_base64": (base64.b64encode(message.key()).decode("ascii")
                                if message.key() is not None else None),
    }
    try:
        publisher.publish(KAFKA_DLQ_TOPIC, key=identity.encode(), value=json.dumps(envelope).encode(),
                          headers=[("x-run-id", run_context.get().encode())] if run_context.get() else None)
    except PublicationFailure as exc:
        milestone("dlq_unconfirmed", reason=exc.reason, event_id=event_id,
                  topic=message.topic(), partition=message.partition(), offset=message.offset())
        raise RetrySession("dlq_unconfirmed") from exc
    milestone("dlq_acknowledged", reason=reason, event_id=event_id, attempt=attempts,
              topic=message.topic(), partition=message.partition(), offset=message.offset())
    commit_message(consumer, message)


def handle_message(consumer, publisher, message, persist=persist_event, wait=sleep,
                   attempts=RETRY_ATTEMPTS) -> str:
    run_id = None
    try:
        header = dict(message.headers() or []).get("x-run-id")
        run_id = valid_run_id(header.decode() if header else None)
    except (ValueError, UnicodeDecodeError):
        pass
    run_token, variant_token = run_context.set(run_id), variant_context.set("async")
    try:
        milestone("message_received", topic=message.topic(), partition=message.partition(), offset=message.offset())
        try:
            wire_value = json.loads(message.value() or b"")
            # HTTP defaults must never generate new identities/timestamps during Kafka replay.
            if not isinstance(wire_value, dict) or not {"event_id", "occurred_at"} <= wire_value.keys():
                raise ValueError("incomplete_wire_contract")
            event = AuditEvent.model_validate(wire_value)
        except (ValidationError, ValueError, UnicodeDecodeError):
            send_to_dlq(consumer, publisher, message, "invalid_event", 0)
            return "dlq"
        for attempt in range(1, attempts + 1):
            milestone("processing_attempt", event_id=event.event_id, attempt=attempt,
                      topic=message.topic(), partition=message.partition(), offset=message.offset())
            try:
                result = persist(event)
            except EventConflict:
                send_to_dlq(consumer, publisher, message, "event_id_content_conflict", attempt, event.event_id)
                return "dlq"
            except SQLAlchemyError:
                if attempt == attempts:
                    send_to_dlq(consumer, publisher, message, "persistence_retries_exhausted", attempt, event.event_id)
                    return "dlq"
                delay = min(RETRY_BACKOFF_SECONDS * 2 ** (attempt - 1), RETRY_BACKOFF_MAX_SECONDS)
                milestone("retry_scheduled", event_id=event.event_id, attempt=attempt,
                          reason="database_error", delay_seconds=delay)
                wait(delay)
            else:
                milestone("persistence_confirmed", event_id=event.event_id, status=result.status,
                          persisted_at=result.persisted_at)
                commit_message(consumer, message)
                return result.status
        raise RetrySession("invalid_retry_budget")
    finally:
        run_context.reset(run_token)
        variant_context.reset(variant_token)


def run() -> None:
    stopped = Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stopped.set())
    while not stopped.is_set():
        consumer = publisher = None
        try:
            initialize_database()
            publisher = KafkaPublisher()
            consumer = Consumer({
                "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS, "group.id": KAFKA_GROUP_ID,
                "auto.offset.reset": "earliest", "enable.auto.commit": False,
                "enable.auto.offset.store": False, "max.poll.interval.ms": 600000,
                "session.timeout.ms": 10000, "socket.timeout.ms": 10000, "log_level": 0,
            })
            consumer.subscribe([KAFKA_TOPIC])
            milestone("consumer_started")
            while not stopped.is_set():
                message = consumer.poll(1.0)
                if message is None:
                    continue
                if message.error():
                    if message.error().code() != KafkaError._PARTITION_EOF:
                        milestone("consumer_transport_error", reason="kafka_error")
                        if message.error().fatal():
                            raise RetrySession("fatal_consumer_error")
                        stopped.wait(min(RECONNECT_SECONDS, 1))
                    continue
                handle_message(consumer, publisher, message, wait=lambda delay: stopped.wait(delay))
        except (SQLAlchemyError, KafkaException, RetrySession):
            milestone("consumer_session_retry", reason="dependency_or_confirmation_failure")
        except Exception:
            # Avoid leaking payloads/credentials in library exception strings or tracebacks.
            # The source offset remains uncommitted; a programming fault cannot silently drop it.
            milestone("consumer_session_retry", reason="unexpected_processing_failure")
        finally:
            if consumer is not None:
                try:
                    consumer.close()  # auto-commit is disabled: close never skips unresolved records.
                except KafkaException:
                    milestone("consumer_close_failed", reason="kafka_error")
            if publisher is not None:
                try:
                    publisher.close()
                except KafkaException:
                    milestone("producer_close_failed", reason="kafka_error")
        if not stopped.is_set():
            stopped.wait(RECONNECT_SECONDS)


if __name__ == "__main__":
    run()
