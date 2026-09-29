from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, HTTPException

from app.shared.config import KAFKA_TOPIC
from app.shared.kafka import KafkaPublisher, PublicationFailure
from app.shared.observability import install_request_context, milestone, run_context
from app.shared.processing import canonical_event
from app.shared.schemas import AuditAccepted, AuditEvent


publisher: KafkaPublisher | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    global publisher
    publisher = KafkaPublisher()
    yield
    remaining = publisher.close()
    if remaining:
        milestone("producer_shutdown_incomplete", reason="unconfirmed_messages")
    publisher = None


app = FastAPI(title="Audit Processing - Asynchronous Producer", lifespan=lifespan)
install_request_context(app, "async")


@app.get("/live")
def live() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health")
def health() -> dict[str, str]:
    if publisher is None or not publisher.ready(KAFKA_TOPIC):
        raise HTTPException(503, detail={"status": "not_ready", "dependency": "kafka"})
    return {"status": "ready", "dependency": "kafka"}


@app.post("/audit", response_model=AuditAccepted, status_code=202)
def accept_audit(event: AuditEvent) -> AuditAccepted:
    started = perf_counter()
    milestone("request_received", event_id=event.event_id)
    if publisher is None:
        raise HTTPException(503, detail={"reason": "producer_unavailable", "acceptance": "rejected",
                                         "event_id": str(event.event_id)})
    try:
        headers = [("x-run-id", run_context.get().encode())] if run_context.get() else None
        receipt = publisher.publish(KAFKA_TOPIC, key=event.entity_id.encode("utf-8"),
                                    value=canonical_event(event).encode("utf-8"), headers=headers)
    except PublicationFailure as exc:
        milestone("publication_unconfirmed", event_id=event.event_id,
                  reason=exc.reason, status=exc.acceptance)
        raise HTTPException(503, detail={"reason": exc.reason, "acceptance": exc.acceptance,
                                         "event_id": str(event.event_id)}) from exc
    milestone("broker_acknowledged", event_id=event.event_id,
              topic=receipt.topic, partition=receipt.partition, offset=receipt.offset,
              duration_ms=(perf_counter() - started) * 1000)
    return AuditAccepted(event_id=event.event_id)
