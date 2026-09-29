from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AuditEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: str = Field(min_length=1, max_length=100)
    entity_type: str = Field(min_length=1, max_length=100)
    entity_id: str = Field(min_length=1, max_length=200)
    actor_id: str = Field(min_length=1, max_length=200)
    source: str = Field(min_length=1, max_length=100)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: dict[str, Any] = Field(default_factory=dict)


class AuditStored(BaseModel):
    event_id: UUID
    status: str
    content_hash: str
    persisted_at: datetime | None = None


class AuditAccepted(BaseModel):
    event_id: UUID
    status: str = "accepted"
