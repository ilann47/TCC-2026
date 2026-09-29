> Links: [[README]] · [[03-der]] · [[07-dicionario-de-dados]] · [[09-diagramas-sequencia]]

# 8. Diagrama de classes — componentes centrais

```mermaid
classDiagram
    class AuditEvent {
      +UUID eventId
      +String eventType
      +String entityType
      +String entityId
      +String actorId
      +String source
      +OffsetDateTime occurredAt
      +JsonNode payload
    }
    class AuditStored {
      +UUID eventId
      +String status
      +String contentHash
      +OffsetDateTime persistedAt
    }
    class AuditAccepted {
      +UUID eventId
      +String status
    }
    class CanonicalEventCodec {
      +encode(AuditEvent) String
      +hash(AuditEvent) String
    }
    class AuditRepository {
      +persist(AuditEvent) AuditStored
      +find(UUID) Optional~AuditStored~
      +ready() boolean
    }
    class KafkaPublisher {
      +publish(topic, key, value, runId) RecordMetadata
      +ready(topic) boolean
      +close() void
    }
    class SyncAuditController {
      +create(AuditEvent) ResponseEntity
      +find(UUID) ResponseEntity
      +health() ResponseEntity
    }
    class AsyncAuditController {
      +accept(AuditEvent) ResponseEntity
      +health() ResponseEntity
    }
    class AuditMessageProcessor {
      +process(ConsumerRecord, Consumer) String
    }
    class ConsumerWorker {
      +start() void
      +stop() void
    }
    SyncAuditController --> AuditRepository : usa
    AsyncAuditController --> KafkaPublisher : usa
    AuditRepository --> CanonicalEventCodec : calcula hash
    AuditRepository --> AuditStored : retorna
    AsyncAuditController --> AuditAccepted : retorna
    AuditMessageProcessor --> AuditRepository : persiste
    AuditMessageProcessor --> KafkaPublisher : publica DLQ
    ConsumerWorker --> AuditMessageProcessor : cria
    AuditRepository --> AuditEvent : recebe
```

O diagrama representa dependências de código, não tabelas adicionais. `AuditEvent` e as respostas são records imutáveis. A API síncrona não usa `KafkaPublisher` em execução; a API assíncrona não usa `AuditRepository`. `ConsumerWorker` cria sessão Kafka e `AuditMessageProcessor`, não uma segunda implementação das regras de persistência.
