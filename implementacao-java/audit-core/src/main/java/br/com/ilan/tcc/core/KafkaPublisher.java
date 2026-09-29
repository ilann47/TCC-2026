package br.com.ilan.tcc.core;

import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.List;
import java.util.Properties;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import org.apache.kafka.clients.producer.BufferExhaustedException;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.Producer;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.clients.producer.RecordMetadata;
import org.apache.kafka.common.KafkaException;
import org.apache.kafka.common.header.Header;
import org.apache.kafka.common.header.internals.RecordHeader;
import org.apache.kafka.common.serialization.ByteArraySerializer;

/** A returned receipt means broker ACK, not end-to-end persistence. */
public final class KafkaPublisher implements AutoCloseable {
    private final Producer<byte[], byte[]> producer;
    private final Duration timeout;

    public KafkaPublisher(String bootstrapServers, Duration timeout) {
        this(new KafkaProducer<>(properties(bootstrapServers, timeout)), timeout);
    }

    public KafkaPublisher(Producer<byte[], byte[]> producer, Duration timeout) {
        this.producer = producer;
        this.timeout = timeout;
    }

    public RecordMetadata publish(String topic, byte[] key, byte[] value, String runId) {
        Iterable<Header> headers = runId == null ? List.of()
            : List.of(new RecordHeader("x-run-id", runId.getBytes(StandardCharsets.UTF_8)));
        ProducerRecord<byte[], byte[]> record = new ProducerRecord<>(topic, null, null, key, value, headers);
        try {
            return producer.send(record).get(timeout.toMillis(), TimeUnit.MILLISECONDS);
        } catch (BufferExhaustedException ex) {
            throw new PublicationFailure("rejected", "producer_buffer_full", ex);
        } catch (TimeoutException ex) {
            throw new PublicationFailure("unknown", "delivery_timeout", ex);
        } catch (InterruptedException ex) {
            Thread.currentThread().interrupt();
            throw new PublicationFailure("unknown", "delivery_interrupted", ex);
        } catch (ExecutionException | KafkaException ex) {
            throw new PublicationFailure("unknown", "delivery_failed", ex);
        }
    }

    public boolean ready(String topic) {
        try {
            return producer.partitionsFor(topic).stream().anyMatch(partition -> partition.leader() != null);
        } catch (KafkaException ex) {
            return false;
        }
    }

    @Override public void close() { producer.close(timeout); }

    private static Properties properties(String bootstrapServers, Duration timeout) {
        Properties properties = new Properties();
        properties.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        properties.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, ByteArraySerializer.class.getName());
        properties.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, ByteArraySerializer.class.getName());
        properties.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG, true);
        properties.put(ProducerConfig.ACKS_CONFIG, "all");
        properties.put(ProducerConfig.DELIVERY_TIMEOUT_MS_CONFIG, (int) timeout.toMillis());
        properties.put(ProducerConfig.REQUEST_TIMEOUT_MS_CONFIG, Math.min(5_000, (int) timeout.toMillis() - 1));
        properties.put(ProducerConfig.MAX_BLOCK_MS_CONFIG, Math.min(2_000, (int) timeout.toMillis()));
        return properties;
    }
}
