package br.com.ilan.tcc.storage;

import br.com.ilan.tcc.core.AuditEvent;
import br.com.ilan.tcc.core.AuditStored;
import br.com.ilan.tcc.core.CanonicalEventCodec;
import br.com.ilan.tcc.core.MilestoneLog;
import java.sql.SQLException;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.postgresql.util.PGobject;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.TransactionDefinition;
import org.springframework.transaction.support.TransactionTemplate;

/** Insert-once semantics shared by the synchronous endpoint and the consumer. */
@Repository
public class AuditRepository {
    private final JdbcTemplate jdbc;
    private final TransactionTemplate transactions;

    public AuditRepository(JdbcTemplate jdbc, PlatformTransactionManager manager) {
        this.jdbc = jdbc;
        this.transactions = new TransactionTemplate(manager);
        this.transactions.setIsolationLevel(TransactionDefinition.ISOLATION_READ_COMMITTED);
    }

    public AuditStored persist(AuditEvent event) {
        String digest = CanonicalEventCodec.hash(event);
        AuditStored result = transactions.execute(status -> {
            List<OffsetDateTime> inserted = jdbc.query("""
                INSERT INTO audit_records
                (event_id, event_type, entity_type, entity_id, actor_id, source, occurred_at, payload, content_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (event_id) DO NOTHING RETURNING persisted_at
                """, (rs, rowNum) -> rs.getObject("persisted_at", OffsetDateTime.class),
                event.eventId(), event.eventType(), event.entityType(), event.entityId(), event.actorId(),
                event.source(), event.occurredAt(), jsonb(event), digest);
            if (!inserted.isEmpty()) {
                return new AuditStored(event.eventId(), "persisted", digest, inserted.getFirst());
            }
            List<AuditStored> existing = jdbc.query("""
                SELECT content_hash, persisted_at FROM audit_records WHERE event_id = ?
                """, (rs, rowNum) -> new AuditStored(event.eventId(), "duplicate",
                    rs.getString("content_hash"), rs.getObject("persisted_at", OffsetDateTime.class)), event.eventId());
            if (existing.isEmpty() || !existing.getFirst().contentHash().equals(digest)) {
                throw new EventConflictException();
            }
            return existing.getFirst();
        });
        if (result == null) throw new IllegalStateException("transaction_returned_null");
        MilestoneLog.emit("commit_completed", "event_id", result.eventId(), "status", result.status(),
            "persisted_at", result.persistedAt());
        return result;
    }

    public Optional<AuditStored> find(UUID eventId) {
        List<AuditStored> rows = jdbc.query("""
            SELECT content_hash, persisted_at FROM audit_records WHERE event_id = ?
            """, (rs, rowNum) -> new AuditStored(eventId, "persisted", rs.getString("content_hash"),
                rs.getObject("persisted_at", OffsetDateTime.class)), eventId);
        return rows.stream().findFirst();
    }

    public boolean ready() {
        try {
            jdbc.queryForObject("SELECT 1 FROM audit_records LIMIT 1", Integer.class);
            return true;
        } catch (org.springframework.dao.DataAccessException ex) {
            return false;
        }
    }

    private static PGobject jsonb(AuditEvent event) {
        PGobject value = new PGobject();
        value.setType("jsonb");
        try {
            value.setValue(CanonicalEventCodec.mapper().writeValueAsString(event.payload()));
        } catch (com.fasterxml.jackson.core.JsonProcessingException | SQLException ex) {
            throw new IllegalArgumentException("invalid_payload", ex);
        }
        return value;
    }
}
