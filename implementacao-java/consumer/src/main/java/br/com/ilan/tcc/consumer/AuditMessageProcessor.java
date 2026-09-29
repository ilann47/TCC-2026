package br.com.ilan.tcc.consumer;

import br.com.ilan.tcc.core.AuditEvent;
import br.com.ilan.tcc.core.CanonicalEventCodec;
import br.com.ilan.tcc.core.KafkaPublisher;
import br.com.ilan.tcc.core.MilestoneLog;
import br.com.ilan.tcc.core.PublicationFailure;
import br.com.ilan.tcc.core.RunContext;
import br.com.ilan.tcc.storage.AuditRepository;
import br.com.ilan.tcc.storage.EventConflictException;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import org.apache.kafka.clients.consumer.Consumer;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.OffsetAndMetadata;
import org.apache.kafka.common.KafkaException;
import org.apache.kafka.common.TopicPartition;
import org.springframework.dao.DataAccessException;
import org.springframework.transaction.TransactionException;

/** At-least-once source processing with an explicit DLQ ACK boundary. */
public final class AuditMessageProcessor {
    private final AuditRepository repository;
    private final KafkaPublisher publisher;
    private final String dlqTopic;
    private final int retryAttempts;
    private final long backoffMs;
    private final long backoffMaxMs;

    public AuditMessageProcessor(AuditRepository repository, KafkaPublisher publisher, String dlqTopic,
                                 int retryAttempts, long backoffMs, long backoffMaxMs) {
        if (retryAttempts < 1 || retryAttempts > 10 || backoffMs < 1 || backoffMaxMs < backoffMs
            || backoffMaxMs > 5000) throw new IllegalArgumentException("invalid_retry_budget");
        this.repository = repository;
        this.publisher = publisher;
        this.dlqTopic = dlqTopic;
        this.retryAttempts = retryAttempts;
        this.backoffMs = backoffMs;
        this.backoffMaxMs = backoffMaxMs;
    }

    public String process(ConsumerRecord<byte[], byte[]> record, Consumer<byte[], byte[]> consumer) {
        String runId = null;
        try {
            var header = record.headers().lastHeader("x-run-id");
            if (header != null) runId = RunContext.validate(new String(header.value(), StandardCharsets.UTF_8));
        } catch (IllegalArgumentException ex) {
            // Invalid correlation metadata never changes the event identity or processing result.
        }
        RunContext.set(runId, "async");
        try {
            MilestoneLog.emit("message_received", "topic", record.topic(), "partition", record.partition(),
                "offset", record.offset());
            AuditEvent event;
            try {
                JsonNode wire = CanonicalEventCodec.mapper().readTree(record.value());
                if (wire == null || !wire.isObject() || !wire.hasNonNull("event_id")
                    || !wire.hasNonNull("occurred_at")) throw new IllegalArgumentException("incomplete_wire_contract");
                event = CanonicalEventCodec.mapper().treeToValue(wire, AuditEvent.class);
            } catch (IOException | IllegalArgumentException ex) {
                sendToDlq(record, consumer, "invalid_event", 0, null);
                return "dlq";
            }
            for (int attempt = 1; attempt <= retryAttempts; attempt++) {
                MilestoneLog.emit("processing_attempt", "event_id", event.eventId(), "attempt", attempt,
                    "topic", record.topic(), "partition", record.partition(), "offset", record.offset());
                try {
                    var result = repository.persist(event);
                    MilestoneLog.emit("persistence_confirmed", "event_id", event.eventId(),
                        "status", result.status(), "persisted_at", result.persistedAt());
                    commit(record, consumer);
                    return result.status();
                } catch (EventConflictException ex) {
                    sendToDlq(record, consumer, "event_id_content_conflict", attempt, event.eventId());
                    return "dlq";
                } catch (DataAccessException | TransactionException ex) {
                    if (attempt == retryAttempts) {
                        sendToDlq(record, consumer, "persistence_retries_exhausted", attempt, event.eventId());
                        return "dlq";
                    }
                    long delay = Math.min(backoffMs * (1L << (attempt - 1)), backoffMaxMs);
                    MilestoneLog.emit("retry_scheduled", "event_id", event.eventId(), "attempt", attempt,
                        "reason", "database_error", "delay_seconds", delay / 1000.0);
                    try { Thread.sleep(delay); }
                    catch (InterruptedException interrupted) {
                        Thread.currentThread().interrupt();
                        throw new RetrySession("retry_interrupted", interrupted);
                    }
                }
            }
            throw new RetrySession("invalid_retry_budget");
        } finally {
            RunContext.clear();
        }
    }

    private void sendToDlq(ConsumerRecord<byte[], byte[]> record, Consumer<byte[], byte[]> consumer,
                           String reason, int attempts, UUID eventId) {
        String identity = record.topic() + ":" + record.partition() + ":" + record.offset();
        Map<String, Object> envelope = new LinkedHashMap<>();
        envelope.put("source_message_id", identity);
        envelope.put("source_topic", record.topic());
        envelope.put("source_partition", record.partition());
        envelope.put("source_offset", record.offset());
        envelope.put("reason", reason);
        envelope.put("attempts", attempts);
        envelope.put("event_id", eventId == null ? null : eventId.toString());
        envelope.put("failed_at", OffsetDateTime.now(ZoneOffset.UTC).toString());
        envelope.put("run_id", RunContext.runId());
        envelope.put("original_value_base64", record.value() == null ? null
            : Base64.getEncoder().encodeToString(record.value()));
        envelope.put("original_key_base64", record.key() == null ? null
            : Base64.getEncoder().encodeToString(record.key()));
        try {
            byte[] body = CanonicalEventCodec.mapper().writeValueAsBytes(envelope);
            publisher.publish(dlqTopic, identity.getBytes(StandardCharsets.UTF_8), body, RunContext.runId());
        } catch (PublicationFailure | JsonProcessingException ex) {
            MilestoneLog.emit("dlq_unconfirmed", "reason", "dlq_publish_failed", "event_id", eventId,
                "topic", record.topic(), "partition", record.partition(), "offset", record.offset());
            throw new RetrySession("dlq_unconfirmed", ex);
        }
        MilestoneLog.emit("dlq_acknowledged", "reason", reason, "event_id", eventId, "attempt", attempts,
            "topic", record.topic(), "partition", record.partition(), "offset", record.offset());
        commit(record, consumer);
    }

    private static void commit(ConsumerRecord<byte[], byte[]> record, Consumer<byte[], byte[]> consumer) {
        try {
            consumer.commitSync(Map.of(new TopicPartition(record.topic(), record.partition()),
                new OffsetAndMetadata(record.offset() + 1)));
        } catch (KafkaException ex) {
            throw new RetrySession("offset_commit_unconfirmed", ex);
        }
        MilestoneLog.emit("offset_committed", "topic", record.topic(), "partition", record.partition(),
            "offset", record.offset());
    }
}
