package br.com.ilan.tcc.async;

import br.com.ilan.tcc.core.AuditAccepted;
import br.com.ilan.tcc.core.AuditEvent;
import br.com.ilan.tcc.core.CanonicalEventCodec;
import br.com.ilan.tcc.core.KafkaPublisher;
import br.com.ilan.tcc.core.MilestoneLog;
import br.com.ilan.tcc.core.PublicationFailure;
import br.com.ilan.tcc.core.RunContext;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class AsyncAuditController {
    private final KafkaPublisher publisher;
    private final String topic;

    public AsyncAuditController(KafkaPublisher publisher, @Value("${audit.kafka.topic}") String topic) {
        this.publisher = publisher;
        this.topic = topic;
    }

    @GetMapping("/live")
    public Map<String, String> live() { return Map.of("status", "alive"); }

    @GetMapping("/health")
    public ResponseEntity<?> health() {
        if (!publisher.ready(topic)) return ResponseEntity.status(503)
            .body(Map.of("detail", Map.of("status", "not_ready", "dependency", "kafka")));
        return ResponseEntity.ok(Map.of("status", "ready", "dependency", "kafka"));
    }

    @PostMapping("/audit")
    public ResponseEntity<?> accept(@RequestBody AuditEvent event) {
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
