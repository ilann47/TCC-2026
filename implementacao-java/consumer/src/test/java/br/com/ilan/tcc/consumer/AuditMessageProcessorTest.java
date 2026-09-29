package br.com.ilan.tcc.consumer;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import br.com.ilan.tcc.core.AuditStored;
import br.com.ilan.tcc.core.KafkaPublisher;
import br.com.ilan.tcc.core.PublicationFailure;
import br.com.ilan.tcc.storage.AuditRepository;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.UUID;
import org.apache.kafka.clients.consumer.Consumer;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.OffsetAndMetadata;
import org.apache.kafka.common.TopicPartition;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.dao.DataAccessResourceFailureException;

class AuditMessageProcessorTest {
    private final AuditRepository repository = Mockito.mock(AuditRepository.class);
    private final KafkaPublisher publisher = Mockito.mock(KafkaPublisher.class);
    @SuppressWarnings("unchecked")
    private final Consumer<byte[], byte[]> consumer = Mockito.mock(Consumer.class);
    private final AuditMessageProcessor processor = new AuditMessageProcessor(repository, publisher, "audit-events-dlq", 1, 1, 1);

    private ConsumerRecord<byte[], byte[]> record(String value) {
        return new ConsumerRecord<>("audit-events", 0, 7, "E1".getBytes(StandardCharsets.UTF_8),
            value.getBytes(StandardCharsets.UTF_8));
    }

    private String valid() {
        return """
            {"event_id":"123e4567-e89b-12d3-a456-426614174000","event_type":"created","entity_type":"order","entity_id":"E1","actor_id":"A1","source":"web","occurred_at":"2026-09-29T12:34:56Z","payload":{}}
            """;
    }

    @Test
    void confirmsOnlyTheProcessedSourceOffsetAfterPersistence() {
        UUID id = UUID.fromString("123e4567-e89b-12d3-a456-426614174000");
        when(repository.persist(any())).thenReturn(new AuditStored(id, "persisted", "abc", null));
        assertEquals("persisted", processor.process(record(valid()), consumer));
        verify(consumer).commitSync(Map.of(new TopicPartition("audit-events", 0), new OffsetAndMetadata(8)));
        verify(publisher, never()).publish(any(), any(), any(), any());
    }

    @Test
    void invalidWireGoesToDlqBeforeOffsetCommit() {
        assertEquals("dlq", processor.process(record("{}"), consumer));
        verify(publisher).publish(eq("audit-events-dlq"), any(), any(), any());
        verify(consumer).commitSync(Map.of(new TopicPartition("audit-events", 0), new OffsetAndMetadata(8)));
    }

    @Test
    void databaseFailureUsesDlqAfterRetryBudget() {
        when(repository.persist(any())).thenThrow(new DataAccessResourceFailureException("db unavailable"));
        assertEquals("dlq", processor.process(record(valid()), consumer));
        verify(publisher).publish(eq("audit-events-dlq"), any(), any(), any());
        verify(consumer).commitSync(any(Map.class));
    }

    @Test
    void unconfirmedDlqDoesNotAdvanceOffset() {
        when(publisher.publish(eq("audit-events-dlq"), any(), any(), any()))
            .thenThrow(new PublicationFailure("unknown", "delivery_timeout", null));
        assertThrows(RetrySession.class, () -> processor.process(record("{}"), consumer));
        verify(consumer, never()).commitSync(any(Map.class));
    }
}
