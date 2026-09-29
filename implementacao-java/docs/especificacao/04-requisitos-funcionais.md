> Links: [[README]] · [[05-casos-de-uso/uc001-registrar-sincrono]] · [[05-casos-de-uso/uc002-aceitar-assincrono]] · [[05-casos-de-uso/uc003-consumir-evento]] · [[10-requisitos-nao-funcionais]]

# 4. Requisitos funcionais

Não há entidades cadastrais para listar/inserir/alterar/excluir. `audit_records` é um registro imutável: inserção e consulta fazem sentido, alteração/exclusão não. Requisitos são agrupados pelos processos reais.

## 4.1 Registro e consulta

| ID | Requisito | Evidência no código |
|---|---|---|
| RF001 | Receber evento JSON com campos obrigatórios e defaults para `event_id`, `occurred_at`, `payload` quando omitidos | `AuditEventDeserializer`, `AuditEvent` |
| RF002 | Registrar sincronamente e responder `201` somente depois do commit; distinguir `persisted` e `duplicate` | `SyncAuditController`, `AuditRepository` |
| RF003 | Consultar por `event_id`, retornando `200`, `404` ou `503` | `SyncAuditController.find` |
| RF004 | Impedir segunda linha com o mesmo `event_id` e detectar hash divergente | PK, `INSERT ON CONFLICT`, `AuditRepository.persist` |

## 4.2 Comunicação assíncrona e processamento

| ID | Requisito | Evidência no código |
|---|---|---|
| RF005 | Publicar evento no Kafka com chave `entity_id` e responder `202` após ACK individual | `AsyncAuditController`, `KafkaPublisher` |
| RF006 | Exigir `event_id` e `occurred_at` no wire Kafka para evitar nova identidade no replay | `AuditMessageProcessor.process` |
| RF007 | Tentar persistir até o limite configurado com espera limitada; conflito/invalidade/exaustão vão à DLQ | `AuditMessageProcessor` |
| RF008 | Confirmar offset apenas após persistência ou ACK da DLQ | `AuditMessageProcessor.commit` |

## 4.3 Operação e relatórios

| ID | Requisito | Evidência no código |
|---|---|---|
| RF009 | Expor vida do processo e prontidão da dependência principal | `/live`, `/health` em cada API |
| RF010 | Emitir marcos JSON sem payload e com `X-Run-ID` quando informado | `MilestoneLog`, filtros HTTP e consumidor |

Não existe relatório de negócio. Os logs estruturados e os dados coletados pelo protocolo experimental são a saída analítica; cálculo de métricas e relatório científico definitivo não são funcionalidades deste código.
