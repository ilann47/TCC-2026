package br.com.ilan.tcc.consumer;

import br.com.ilan.tcc.core.KafkaPublisher;
import br.com.ilan.tcc.core.MilestoneLog;
import br.com.ilan.tcc.storage.AuditRepository;
import jakarta.annotation.PreDestroy;
import java.time.Duration;
import java.util.List;
import java.util.Properties;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.common.KafkaException;
import org.apache.kafka.common.errors.WakeupException;
import org.apache.kafka.common.serialization.ByteArrayDeserializer;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

@Component
public class ConsumerWorker {
    private final AuditRepository repository;
    private final String bootstrap;
    private final String topic;
    private final String dlqTopic;
    private final String group;
    private final int attempts;
    private final long backoffMs;
    private final long backoffMaxMs;
    private final long deliveryTimeoutMs;
    private final long reconnectMs;
    private volatile boolean stopped;
    private volatile KafkaConsumer<byte[], byte[]> currentConsumer;
    private Thread thread;

    public ConsumerWorker(AuditRepository repository,
                          @Value("${audit.kafka.bootstrap-servers}") String bootstrap,
                          @Value("${audit.kafka.topic}") String topic,
                          @Value("${audit.kafka.dlq-topic}") String dlqTopic,
                          @Value("${audit.kafka.group-id}") String group,
                          @Value("${audit.retry.attempts}") int attempts,
                          @Value("${audit.retry.backoff-ms}") long backoffMs,
                          @Value("${audit.retry.backoff-max-ms}") long backoffMaxMs,
                          @Value("${audit.kafka.delivery-timeout-ms}") long deliveryTimeoutMs,
                          @Value("${audit.retry.reconnect-ms}") long reconnectMs) {
        this.repository = repository;
        this.bootstrap = bootstrap;
        this.topic = topic;
        this.dlqTopic = dlqTopic;
        this.group = group;
        this.attempts = attempts;
        this.backoffMs = backoffMs;
        this.backoffMaxMs = backoffMaxMs;
        this.deliveryTimeoutMs = deliveryTimeoutMs;
        this.reconnectMs = reconnectMs;
        if (deliveryTimeoutMs < 1000 || deliveryTimeoutMs > 30_000 || reconnectMs < 1
            || attempts * (4 * 30_000L + backoffMaxMs) + deliveryTimeoutMs >= 500_000) {
            throw new IllegalArgumentException("invalid_processing_budget");
        }
    }

    @EventListener(ApplicationReadyEvent.class)
    public void start() {
        thread = new Thread(this::run, "audit-kafka-consumer");
        thread.start();
    }

    private void run() {
        while (!stopped) {
            try (KafkaPublisher publisher = new KafkaPublisher(bootstrap, Duration.ofMillis(deliveryTimeoutMs));
                 KafkaConsumer<byte[], byte[]> consumer = new KafkaConsumer<>(properties())) {
                currentConsumer = consumer;
                AuditMessageProcessor processor = new AuditMessageProcessor(repository, publisher, dlqTopic,
                    attempts, backoffMs, backoffMaxMs);
                consumer.subscribe(List.of(topic));
                MilestoneLog.emit("consumer_started");
                while (!stopped) {
                    var records = consumer.poll(Duration.ofSeconds(1));
                    for (var record : records) processor.process(record, consumer);
                }
            } catch (WakeupException ex) {
                if (!stopped) MilestoneLog.emit("consumer_session_retry", "reason", "kafka_wakeup");
            } catch (KafkaException | RetrySession ex) {
                MilestoneLog.emit("consumer_session_retry", "reason", "dependency_or_confirmation_failure");
            } catch (RuntimeException ex) {
                // Do not log exception messages, records, credentials or the original DLQ body.
                MilestoneLog.emit("consumer_session_retry", "reason", "unexpected_processing_failure");
            } finally {
                currentConsumer = null;
            }
            if (!stopped) {
                try { Thread.sleep(reconnectMs); }
                catch (InterruptedException ex) { Thread.currentThread().interrupt(); return; }
            }
        }
    }

    @PreDestroy
    public void stop() {
        stopped = true;
        KafkaConsumer<byte[], byte[]> consumer = currentConsumer;
        if (consumer != null) consumer.wakeup();
        if (thread != null) {
            try { thread.join(3000); }
            catch (InterruptedException ex) { Thread.currentThread().interrupt(); }
        }
    }

    private Properties properties() {
        Properties values = new Properties();
        values.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrap);
        values.put(ConsumerConfig.GROUP_ID_CONFIG, group);
        values.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, ByteArrayDeserializer.class.getName());
        values.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, ByteArrayDeserializer.class.getName());
        values.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "earliest");
        values.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, false);
        values.put(ConsumerConfig.MAX_POLL_RECORDS_CONFIG, 1);
        values.put(ConsumerConfig.MAX_POLL_INTERVAL_MS_CONFIG, 600_000);
        values.put(ConsumerConfig.SESSION_TIMEOUT_MS_CONFIG, 10_000);
        return values;
    }
}
