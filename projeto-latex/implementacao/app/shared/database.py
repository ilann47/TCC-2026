from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, String, Text, create_engine, select, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID, insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.shared.config import DATABASE_URL, DB_TIMEOUT_SECONDS
from app.shared.observability import milestone
from app.shared.processing import content_hash
from app.shared.schemas import AuditEvent, AuditStored


class EventConflict(Exception):
    """The identifier already belongs to different immutable content."""


class Base(DeclarativeBase):
    pass


class AuditRecord(Base):
    __tablename__ = "audit_records"

    event_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    actor_id: Mapped[str] = mapped_column(String(200), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    # INSERT timestamp, not COMMIT completion. Historical rows remain NULL.
    persisted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=text("clock_timestamp()")
    )


engine = create_engine(
    DATABASE_URL, pool_pre_ping=True, pool_timeout=DB_TIMEOUT_SECONDS,
    isolation_level="READ COMMITTED",
    connect_args={"connect_timeout": DB_TIMEOUT_SECONDS,
                  "options": f"-c statement_timeout={DB_TIMEOUT_SECONDS * 1000} "
                             f"-c lock_timeout={DB_TIMEOUT_SECONDS * 1000} -c synchronous_commit=on"},
)


def initialize_database() -> None:
    with engine.begin() as connection:
        # Serializes prototype processes creating this same local schema.
        connection.execute(text("SELECT pg_advisory_xact_lock(20260907)"))
        Base.metadata.create_all(connection)
        connection.execute(text("ALTER TABLE audit_records ADD COLUMN IF NOT EXISTS persisted_at TIMESTAMPTZ"))
        connection.execute(text("ALTER TABLE audit_records ALTER COLUMN persisted_at SET DEFAULT clock_timestamp()"))


def database_ready() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(select(AuditRecord.event_id, AuditRecord.persisted_at).limit(1))
        return True
    except SQLAlchemyError:
        return False


def find_event(event_id: UUID) -> AuditStored | None:
    with engine.connect() as connection:
        existing = connection.execute(select(AuditRecord.content_hash, AuditRecord.persisted_at)
                                      .where(AuditRecord.event_id == event_id)).mappings().first()
    if existing is None:
        return None
    return AuditStored(event_id=event_id, status="persisted", content_hash=existing["content_hash"],
                       persisted_at=existing["persisted_at"])


def persist_event(event: AuditEvent) -> AuditStored:
    digest = content_hash(event)
    with engine.begin() as connection:
        row = connection.execute(
            insert(AuditRecord).values(**event.model_dump(), content_hash=digest)
            .on_conflict_do_nothing(index_elements=[AuditRecord.event_id])
            .returning(AuditRecord.persisted_at)
        ).first()
        if row is not None:
            result = AuditStored(event_id=event.event_id, status="persisted", content_hash=digest,
                                 persisted_at=row.persisted_at)
        else:
            # A new READ COMMITTED statement observes the competing transaction's row.
            existing = connection.execute(select(AuditRecord).where(
                AuditRecord.event_id == event.event_id)).mappings().one()
            if existing["content_hash"] != digest:
                raise EventConflict("event_id_content_conflict")
            result = AuditStored(event_id=event.event_id, status="duplicate", content_hash=digest,
                                 persisted_at=existing["persisted_at"])
    milestone("commit_completed", event_id=event.event_id, status=result.status,
              persisted_at=result.persisted_at)
    return result
