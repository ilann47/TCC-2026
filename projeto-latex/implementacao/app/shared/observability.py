"""JSON milestones without payloads, actor identifiers or exception messages."""
import json
import logging
from contextvars import ContextVar
from datetime import datetime, timezone
from time import perf_counter_ns, time_ns
from uuid import UUID

from fastapi.responses import JSONResponse


run_context = ContextVar("run_id", default=None)
variant_context = ContextVar("variant", default=None)
log = logging.getLogger("audit.milestones")
if not log.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(handler)
log.setLevel(logging.INFO)
log.propagate = False

ALLOWED_FIELDS = {
    "variant", "event_id", "status", "reason", "attempt", "delay_seconds",
    "topic", "partition", "offset", "duration_ms", "persisted_at",
}


def valid_run_id(value: str | None) -> str | None:
    return str(UUID(value)) if value else None


def milestone(name: str, **fields) -> None:
    safe = {key: str(value) if key in {"event_id", "persisted_at"} else value
            for key, value in fields.items() if key in ALLOWED_FIELDS}
    log.info(json.dumps({"milestone": name, "timestamp": datetime.now(timezone.utc).isoformat(),
                        "wall_time_ns": time_ns(), "monotonic_ns": perf_counter_ns(),
                        "run_id": run_context.get(), "variant": variant_context.get(), **safe},
                       ensure_ascii=False))


def install_request_context(app, variant: str) -> None:
    @app.middleware("http")
    async def request_context(request, call_next):
        try:
            run_id = valid_run_id(request.headers.get("x-run-id"))
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": {"reason": "invalid_run_id"}})
        run_token = run_context.set(run_id)
        variant_token = variant_context.set(variant)
        try:
            return await call_next(request)
        finally:
            run_context.reset(run_token)
            variant_context.reset(variant_token)
