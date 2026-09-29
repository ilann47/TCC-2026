package br.com.ilan.tcc.async;

import br.com.ilan.tcc.core.KafkaPublisher;
import java.time.Duration;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

@SpringBootApplication(scanBasePackages = "br.com.ilan.tcc")
public class AsyncApplication {
    public static void main(String[] args) { SpringApplication.run(AsyncApplication.class, args); }

    @Bean(destroyMethod = "close")
    KafkaPublisher kafkaPublisher(@Value("${audit.kafka.bootstrap-servers}") String bootstrap,
                                  @Value("${audit.kafka.delivery-timeout-ms}") long timeoutMs) {
        if (timeoutMs < 1000 || timeoutMs > 30_000) throw new IllegalArgumentException("invalid_delivery_timeout");
        return new KafkaPublisher(bootstrap, Duration.ofMillis(timeoutMs));
    }
}
