package br.com.ilan.tcc.sync;

import br.com.ilan.tcc.core.AuditEvent;
import br.com.ilan.tcc.core.AuditStored;
import br.com.ilan.tcc.core.MilestoneLog;
import br.com.ilan.tcc.storage.AuditRepository;
import br.com.ilan.tcc.storage.EventConflictException;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.ExampleObject;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import java.util.Map;
import java.util.UUID;
import org.springframework.dao.DataAccessException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.transaction.TransactionException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@RestController
@Tag(name = "Auditoria síncrona", description = "A resposta de criação é enviada após a transação no PostgreSQL.")
public class SyncAuditController {
    private final AuditRepository repository;

    public SyncAuditController(AuditRepository repository) { this.repository = repository; }

    @Operation(summary = "Verificar se o processo HTTP está ativo")
    @GetMapping("/live")
    public Map<String, String> live() { return Map.of("status", "alive"); }

    @Operation(summary = "Verificar a disponibilidade do PostgreSQL")
    @ApiResponses({@ApiResponse(responseCode = "200", description = "Banco disponível"),
        @ApiResponse(responseCode = "503", description = "Banco indisponível")})
    @GetMapping("/health")
    public ResponseEntity<?> health() {
        if (!repository.ready()) return ResponseEntity.status(503)
            .body(Map.of("detail", Map.of("status", "not_ready", "dependency", "postgresql")));
        return ResponseEntity.ok(Map.of("status", "ready", "dependency", "postgresql"));
    }

    @Operation(summary = "Consultar um registro persistido pelo identificador do evento")
    @ApiResponses({
        @ApiResponse(responseCode = "200", description = "Registro encontrado",
            content = @Content(schema = @Schema(implementation = AuditStored.class))),
        @ApiResponse(responseCode = "404", description = "Registro ainda não encontrado"),
        @ApiResponse(responseCode = "422", description = "Identificador inválido"),
        @ApiResponse(responseCode = "503", description = "Banco indisponível")})
    @GetMapping("/audit/{eventId}")
    public ResponseEntity<?> find(@PathVariable UUID eventId) {
        try {
            return repository.find(eventId).<ResponseEntity<?>>map(ResponseEntity::ok)
                .orElseGet(() -> ResponseEntity.status(404).body(Map.of("detail", Map.of("reason", "event_not_found"))));
        } catch (DataAccessException | TransactionException ex) {
            return ResponseEntity.status(503).body(Map.of("detail", Map.of("reason", "database_unavailable")));
        }
    }

    @Operation(summary = "Persistir um evento de auditoria",
        description = "Retorna 201 somente após a transação. O status do corpo é persisted ou duplicate. "
            + "event_id e occurred_at podem ser omitidos; nesse caso, a API gera seus valores.")
    @ApiResponses({
        @ApiResponse(responseCode = "201", description = "Evento persistido ou duplicata idêntica",
            content = @Content(schema = @Schema(implementation = AuditStored.class))),
        @ApiResponse(responseCode = "409", description = "Mesmo event_id com conteúdo diferente"),
        @ApiResponse(responseCode = "422", description = "Evento inválido"),
        @ApiResponse(responseCode = "503", description = "Banco indisponível; confirmação da gravação desconhecida")})
    @PostMapping("/audit")
    public ResponseEntity<?> create(@RequestBody
        @io.swagger.v3.oas.annotations.parameters.RequestBody(required = true,
            content = @Content(mediaType = "application/json", schema = @Schema(implementation = AuditEvent.class),
                examples = @ExampleObject(value = """
                    {"event_type":"created","entity_type":"order","entity_id":"E1",
                     "actor_id":"A1","source":"swagger-ui","payload":{"value":1}}
                    """))) AuditEvent event) {
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
        } catch (DataAccessException | TransactionException ex) {
            MilestoneLog.emit("request_failed", "event_id", event.eventId(), "reason", "database_unavailable");
            return ResponseEntity.status(503).body(Map.of("detail", Map.of(
                "reason", "database_unavailable", "acceptance", "unknown", "event_id", event.eventId().toString())));
        }
    }
}
