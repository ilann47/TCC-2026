from contextlib import asynccontextmanager
from time import perf_counter
from uuid import UUID

from fastapi import FastAPI, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.shared.database import EventConflict, database_ready, find_event, initialize_database, persist_event
from app.shared.observability import install_request_context, milestone
from app.shared.schemas import AuditEvent, AuditStored


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="Audit Processing - Synchronous REST", lifespan=lifespan)
install_request_context(app, "sync")


@app.get("/live")
def live() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health")
def health() -> dict[str, str]:
    if not database_ready():
        raise HTTPException(503, detail={"status": "not_ready", "dependency": "postgresql"})
    return {"status": "ready", "dependency": "postgresql"}


@app.get("/audit/{event_id}", response_model=AuditStored)
def get_audit(event_id: UUID) -> AuditStored:
    try:
        result = find_event(event_id)
    except SQLAlchemyError as exc:
        raise HTTPException(503, detail={"reason": "database_unavailable"}) from exc
    if result is None:
        raise HTTPException(404, detail={"reason": "event_not_found"})
    return result


@app.post("/audit", response_model=AuditStored, status_code=201)
def create_audit(event: AuditEvent) -> AuditStored:
    started = perf_counter()
    milestone("request_received", event_id=event.event_id)
    try:
        result = persist_event(event)
    except EventConflict as exc:
        milestone("request_failed", event_id=event.event_id, reason="event_id_content_conflict")
        raise HTTPException(409, detail={"reason": "event_id_content_conflict", "event_id": str(event.event_id)}) from exc
    except SQLAlchemyError as exc:
        milestone("request_failed", event_id=event.event_id, reason="database_unavailable")
        raise HTTPException(503, detail={"reason": "database_unavailable", "acceptance": "unknown",
                                         "event_id": str(event.event_id)}) from exc
    milestone("persistence_confirmed", event_id=event.event_id,
              status=result.status, persisted_at=result.persisted_at,
              duration_ms=(perf_counter() - started) * 1000)
    return result
