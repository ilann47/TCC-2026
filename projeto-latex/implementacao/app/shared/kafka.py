"""Bounded, per-record broker acknowledgement (not end-to-end persistence)."""
from dataclasses import dataclass
from threading import Event
from time import monotonic

from confluent_kafka import KafkaException, Producer

from app.shared.config import DELIVERY_TIMEOUT_SECONDS, KAFKA_BOOTSTRAP_SERVERS


class PublicationFailure(Exception):
    def __init__(self, acceptance: str, reason: str):
        self.acceptance, self.reason = acceptance, reason
        super().__init__(reason)


@dataclass(frozen=True)
class DeliveryReceipt:
    topic: str
    partition: int
    offset: int


class KafkaPublisher:
    def __init__(self, producer=None, timeout=DELIVERY_TIMEOUT_SECONDS):
        self.timeout = timeout
        self.producer = producer if producer is not None else Producer({
            "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
            "enable.idempotence": True,
            "acks": "all",
            "delivery.timeout.ms": int(timeout * 1000),
            "socket.timeout.ms": int(timeout * 1000),
            "log_level": 0,
        })

    def publish(self, topic: str, value: bytes, key: bytes | None = None,
                headers: list | None = None) -> DeliveryReceipt:
        completed = Event()
        outcome = {}

        def delivered(error, message):
            outcome["error"] = error
            if error is None:
                outcome["receipt"] = DeliveryReceipt(message.topic(), message.partition(), message.offset())
            completed.set()

        deadline = monotonic() + self.timeout
        try:
            self.producer.produce(topic, value=value, key=key, headers=headers, on_delivery=delivered)
        except BufferError as exc:
            raise PublicationFailure("rejected", "producer_buffer_full") from exc
        except KafkaException as exc:
            raise PublicationFailure("unknown", "producer_error") from exc
        while not completed.is_set():
            remaining = deadline - monotonic()
            if remaining <= 0:
                # The message may still be delivered. Never claim rejection or cancel/retry it.
                raise PublicationFailure("unknown", "delivery_timeout")
            try:
                self.producer.poll(min(0.05, remaining))
            except KafkaException as exc:
                raise PublicationFailure("unknown", "delivery_poll_error") from exc
        if outcome["error"] is not None:
            raise PublicationFailure("unknown", "delivery_failed")
        return outcome["receipt"]

    def ready(self, topic: str) -> bool:
        try:
            metadata = self.producer.list_topics(timeout=min(2, self.timeout))
            topic_metadata = metadata.topics.get(topic)
            return bool(topic_metadata and topic_metadata.error is None
                        and topic_metadata.partitions
                        and all(part.leader >= 0 for part in topic_metadata.partitions.values()))
        except KafkaException:
            return False

    def close(self) -> int:
        return self.producer.flush(self.timeout)
