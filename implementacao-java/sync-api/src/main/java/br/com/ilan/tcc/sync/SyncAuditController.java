package br.com.ilan.tcc.sync;

import br.com.ilan.tcc.core.AuditEvent;
import br.com.ilan.tcc.core.AuditStored;
import br.com.ilan.tcc.core.MilestoneLog;
import br.com.ilan.tcc.storage.AuditRepository;
import br.com.ilan.tcc.storage.EventConflictException;
import java.util.Map;
import java.util.UUID;
import org.springframework.dao.DataAccessException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class SyncAuditController {
    private final AuditRepository repository;

    public SyncAuditController(AuditRepository repository) { this.repository = repository; }

    @GetMapping("/live")
    public Map<String, String> live() { return Map.of("status", "alive"); }

    @GetMapping("/health")
    public ResponseEntity<?> health() {
        if (!repository.ready()) return ResponseEntity.status(503)
            .body(Map.of("detail", Map.of("status", "not_ready", "dependency", "postgresql")));
        return ResponseEntity.ok(Map.of("status", "ready", "dependency", "postgresql"));
    }

    @GetMapping("/audit/{eventId}")
    public ResponseEntity<?> find(@PathVariable UUID eventId) {
        try {
            return repository.find(eventId).<ResponseEntity<?>>map(ResponseEntity::ok)
                .orElseGet(() -> ResponseEntity.status(404).body(Map.of("detail", Map.of("reason", "event_not_found"))));
        } catch (DataAccessException ex) {
            return ResponseEntity.status(503).body(Map.of("detail", Map.of("reason", "database_unavailable")));
        }
    }

    @PostMapping("/audit")
    public ResponseEntity<?> create(@RequestBody AuditEvent event) {
        long start = System.nanoTime();
        MilestoneLog.emit("request_received", "event_id", event.eventId());
        try {
            AuditStored result = repository.persist(event);
            MilestoneLog.emit("persistence_confirmed", "event_id", event.eventId(), "status", result.status(),
                "persisted_at", result.persistedAt(), "duration_ms", (System.nanoTime() - start) / 1_000_000.0);
            return ResponseEntity.status(HttpStatus.CREATED).body(result);
        } catch (EventConflictException ex) {
            MilestoneLog.emit("request_failed", "event_id", event.eventId(), "reason", "event_id_content_conflict");
            return ResponseEntity.status(409).body(Map.of("detail", Map.of(
                "reason", "event_id_content_conflict", "event_id", event.eventId().toString())));
        } catch (DataAccessException ex) {
            MilestoneLog.emit("request_failed", "event_id", event.eventId(), "reason", "database_unavailable");
            return ResponseEntity.status(503).body(Map.of("detail", Map.of(
                "reason", "database_unavailable", "acceptance", "unknown", "event_id", event.eventId().toString())));
        }
    }
}
