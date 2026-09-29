> Links: [[README]] · [[03-der]] · [[04-requisitos-funcionais]] · [[08-diagramas-classe]]

# 7. Dicionário de dados

Fonte: `AuditEvent`, `AuditStored` e migração SQL V1. “Obrigatório na API” distingue campo que pode ser omitido para aplicar default de campo obrigatório na linha. Para consumo Kafka, `event_id` e `occurred_at` são sempre obrigatórios no wire.

| Campo `audit_records` | Tipo SQL | Obrigatório na API | Tamanho/limite | Regra de validação e observação |
|---|---|---|---|---|
| `event_id` | UUID, PK | Não; gera UUID quando omitido | 16 bytes | Imutável; explícito nulo é inválido; único no banco |
| `event_type` | VARCHAR(100) NOT NULL | Sim | 1–100 caracteres Java | Não vazio; representa tipo do fato |
| `entity_type` | VARCHAR(100) NOT NULL | Sim | 1–100 | Não vazio; tipo da entidade de origem |
| `entity_id` | VARCHAR(200) NOT NULL | Sim | 1–200 | Não vazio; índice simples; chave de publicação Kafka |
| `actor_id` | VARCHAR(200) NOT NULL | Sim | 1–200 | Não vazio; não é usuário autenticado |
| `source` | VARCHAR(100) NOT NULL | Sim | 1–100 | Não vazio; origem declarada pelo cliente |
| `occurred_at` | TIMESTAMPTZ NOT NULL | Não; usa UTC atual quando omitido | Microssegundos no PostgreSQL | Entrada Java exige ISO 8601 com offset quando fornecida; não confundir com inserção/commit |
| `payload` | JSONB NOT NULL | Não; default `{}` | Limitado pelo armazenamento, não há limite de aplicação | Deve ser objeto JSON; pode conter dados sensíveis |
| `content_hash` | TEXT NOT NULL | Gerado | 64 caracteres hexadecimais | SHA-256 de evento canônico; detecta conflito de conteúdo para mesmo ID |
| `persisted_at` | TIMESTAMPTZ, nullable | Gerado pelo banco | Microssegundos | `clock_timestamp()` da inserção; **não** é instante de commit |

Não há FK nem relacionamento relacional. A API `AuditStored` contém `event_id`, `status` (`persisted` ou `duplicate`), `content_hash` e `persisted_at`. `AuditAccepted` contém `event_id` e `status=accepted`. O envelope da DLQ **não é tabela**; inclui `source_message_id`, `source_topic`, `source_partition`, `source_offset`, `reason`, `attempts`, `event_id`, `failed_at`, `run_id`, `original_value_base64` e `original_key_base64`. Valores Base64 não são anonimização nem criptografia.
