package br.com.ilan.tcc.async;

import br.com.ilan.tcc.core.AuditAccepted;
import br.com.ilan.tcc.core.AuditEvent;
import br.com.ilan.tcc.core.CanonicalEventCodec;
import br.com.ilan.tcc.core.KafkaPublisher;
import br.com.ilan.tcc.core.MilestoneLog;
import br.com.ilan.tcc.core.PublicationFailure;
import br.com.ilan.tcc.core.RunContext;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.ExampleObject;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@RestController
@Tag(name = "Auditoria assíncrona", description = "A API publica o evento no Kafka; o consumidor persiste depois.")
public class AsyncAuditController {
    private final KafkaPublisher publisher;
    private final String topic;

    public AsyncAuditController(KafkaPublisher publisher, @Value("${audit.kafka.topic}") String topic) {
        this.publisher = publisher;
        this.topic = topic;
    }

    @Operation(summary = "Verificar se o processo HTTP está ativo")
    @GetMapping("/live")
    public Map<String, String> live() { return Map.of("status", "alive"); }

    @Operation(summary = "Verificar a disponibilidade do Kafka")
    @ApiResponses({@ApiResponse(responseCode = "200", description = "Broker disponível"),
        @ApiResponse(responseCode = "503", description = "Broker indisponível")})
    @GetMapping("/health")
    public ResponseEntity<?> health() {
        if (!publisher.ready(topic)) return ResponseEntity.status(503)
            .body(Map.of("detail", Map.of("status", "not_ready", "dependency", "kafka")));
        return ResponseEntity.ok(Map.of("status", "ready", "dependency", "kafka"));
    }

    @Operation(summary = "Publicar um evento de auditoria",
        description = "Retorna 202 após o ACK do Kafka. Isso não confirma persistência no PostgreSQL; "
            + "consulte o registro pela API síncrona usando o event_id retornado. "
            + "event_id e occurred_at podem ser omitidos; nesse caso, a API gera seus valores.")
    @ApiResponses({
        @ApiResponse(responseCode = "202", description = "Publicação confirmada pelo Kafka",
            content = @Content(schema = @Schema(implementation = AuditAccepted.class))),
        @ApiResponse(responseCode = "422", description = "Evento inválido"),
        @ApiResponse(responseCode = "503", description = "Publicação não confirmada; verifique acceptance no corpo")})
    @PostMapping("/audit")
    public ResponseEntity<?> accept(@RequestBody
        @io.swagger.v3.oas.annotations.parameters.RequestBody(required = true,
            content = @Content(mediaType = "application/json", schema = @Schema(implementation = AuditEvent.class),
                examples = @ExampleObject(value = """
                    {"event_type":"created","entity_type":"order","entity_id":"E1",
                     "actor_id":"A1","source":"swagger-ui","payload":{"value":1}}
                    """))) AuditEvent event) {
        long start = System.nanoTime();
        MilestoneLog.emit("request_received", "event_id", event.eventId());
        try {
            var receipt = publisher.publish(topic, event.entityId().getBytes(StandardCharsets.UTF_8),
                CanonicalEventCodec.encode(event).getBytes(StandardCharsets.UTF_8), RunContext.runId());
            MilestoneLog.emit("broker_acknowledged", "event_id", event.eventId(), "topic", receipt.topic(),
                "partition", receipt.partition(), "offset", receipt.offset(),
                "duration_ms", (System.nanoTime() - start) / 1_000_000.0);
            return ResponseEntity.accepted().body(new AuditAccepted(event.eventId()));
        } catch (PublicationFailure ex) {
            MilestoneLog.emit("publication_unconfirmed", "event_id", event.eventId(),
                "reason", ex.reason(), "status", ex.acceptance());
            return ResponseEntity.status(503).body(Map.of("detail", Map.of("reason", ex.reason(),
                "acceptance", ex.acceptance(), "event_id", event.eventId().toString())));
        }
    }
}
