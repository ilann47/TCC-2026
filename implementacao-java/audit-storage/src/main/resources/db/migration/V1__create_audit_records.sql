CREATE TABLE audit_records (
    event_id UUID PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id VARCHAR(200) NOT NULL,
    actor_id VARCHAR(200) NOT NULL,
    source VARCHAR(100) NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    payload JSONB NOT NULL,
    content_hash TEXT NOT NULL,
    persisted_at TIMESTAMPTZ DEFAULT clock_timestamp()
);

CREATE INDEX idx_audit_records_entity_id ON audit_records(entity_id);
