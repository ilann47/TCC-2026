import hashlib
import json

from app.shared.schemas import AuditEvent


def canonical_event(event: AuditEvent) -> str:
    return json.dumps(
        event.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def content_hash(event: AuditEvent) -> str:
    return hashlib.sha256(canonical_event(event).encode("utf-8")).hexdigest()

