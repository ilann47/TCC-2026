> Links: [[README]] · [[08-diagramas-classe]] · [[05-casos-de-uso/uc001-registrar-sincrono]] · [[05-casos-de-uso/uc003-consumir-evento]]

# 9. Diagramas de sequência

## 9.1 Registro síncrono

```mermaid
sequenceDiagram
    actor Cliente
    participant API as SyncAuditController
    participant Repo as AuditRepository
    participant DB as PostgreSQL
    Cliente->>API: POST /audit
    API->>Repo: persist(event)
    Repo->>Repo: hash do JSON canônico
    Repo->>DB: BEGIN + INSERT ON CONFLICT
    alt ID novo
        DB-->>Repo: persisted_at
    else ID repetido
        Repo->>DB: SELECT content_hash
        DB-->>Repo: hash original
    end
    Repo->>DB: COMMIT
    Repo-->>API: AuditStored
    API-->>Cliente: 201 persisted/duplicate
```

Se o hash original divergir, o repositório aborta a transação e a API responde `409`. Em falha de banco, responde `503` com aceitação incerta.

## 9.2 Aceitação e persistência assíncronas

```mermaid
sequenceDiagram
    actor Cliente
    participant API as AsyncAuditController
    participant K as Kafka audit-events
    participant C as AuditMessageProcessor
    participant DB as PostgreSQL
    Cliente->>API: POST /audit
    API->>K: publish(evento canônico)
    K-->>API: ACK tópico/partição/offset
    API-->>Cliente: 202 accepted
    K->>C: evento
    C->>DB: INSERT ON CONFLICT + COMMIT
    DB-->>C: persisted/duplicate
    C->>K: commitSync(offset + 1)
```

O espaço entre `202` e commit do PostgreSQL é intencional. Para medir fim a fim, usar `commit_completed.wall_time_ns`, não a latência HTTP do `202` isoladamente.

## 9.3 Exaustão de tentativas e DLQ

```mermaid
sequenceDiagram
    participant K as Kafka audit-events
    participant C as AuditMessageProcessor
    participant DB as PostgreSQL
    participant Q as Kafka DLQ
    K->>C: evento
    loop até RETRY_ATTEMPTS
        C->>DB: persist(evento)
        DB-->>C: erro temporário
    end
    C->>Q: envelope com origem e payload Base64
    Q-->>C: ACK da DLQ
    C->>K: commitSync(offset + 1)
```

Sem ACK da DLQ, o último passo não ocorre. Se o ACK da DLQ ocorrer e o commit do offset falhar, a mensagem de origem pode ser reentregue e gerar outra entrada na DLQ; `source_message_id` identifica a origem para reconciliação.
