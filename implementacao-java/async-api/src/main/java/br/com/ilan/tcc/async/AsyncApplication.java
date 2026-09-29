package br.com.ilan.tcc.async;

import br.com.ilan.tcc.core.KafkaPublisher;
import io.swagger.v3.oas.annotations.OpenAPIDefinition;
import io.swagger.v3.oas.annotations.info.Info;
import java.time.Duration;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

@OpenAPIDefinition(info = @Info(title = "Auditoria - API assincrona", version = "0.1.0",
    description = "Publicacao orientada a eventos: o retorno 202 confirma o ACK do Kafka, nao a persistencia."))
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
