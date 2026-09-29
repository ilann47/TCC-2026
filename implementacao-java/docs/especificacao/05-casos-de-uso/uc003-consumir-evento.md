> Links: [[../README]] · [[../04-requisitos-funcionais]] · [[uc002-aceitar-assincrono]] · [[../09-diagramas-sequencia]]

# UC003 — Consumir, persistir e tratar falha

## Objetivo e regras de negócio

RN009: replay não pode criar novo `event_id` nem novo `occurred_at`; ambos devem existir no wire Kafka. RN010: o offset de origem só é confirmado depois do commit PostgreSQL ou do ACK da DLQ. RN011: erro transitório de banco recebe tentativas limitadas; conflito, evento inválido e exaustão vão à DLQ. RN012: DLQ/commit não confirmados provocam reabertura de sessão e possível reentrega; não há promessa de exatamente uma entrega.

## Atores

Consumidor automatizado; Kafka e PostgreSQL.

## Pré-condição, pós-condição e ativação

Pré-condição: tópico/consumer group configurados. Ativação: leitura de registro em `audit-events`. Pós-condição normal: linha `audit_records` presente e offset confirmado. Pós-condição alternativa: mensagem confirmada na DLQ e offset de origem confirmado. Se um desses ACKs falhar, o offset permanece não confirmado.

## Fluxo principal

1. Consumidor lê uma mensagem (`max.poll.records=1`) e recupera `X-Run-ID` se válido.
2. Registra `message_received`; verifica que o valor é objeto JSON com `event_id` e `occurred_at` explícitos.
3. Valida e desserializa `AuditEvent`.
4. Registra `processing_attempt`; chama o repositório compartilhado.
5. Após transação concluída, registra `persistence_confirmed`.
6. Confirma explicitamente **offset da mensagem + 1**, com `commitSync` para a partição de origem, e registra `offset_committed`.

## Fluxos alternativos

A1 — Duplicata: repositório retorna `duplicate`; o offset é confirmado sem inserir segunda linha.

A2 — Erro de banco: aplica espera exponencial limitada. Esgotadas as tentativas, publica envelope na DLQ com identificação de origem, motivo, tentativas e chave/valor originais em Base64; espera ACK e só então confirma offset.

A3 — Evento inválido ou hash conflitante: envia à DLQ sem repetir o processamento normal.

## Fluxos de exceção

E1 — ACK da DLQ ausente: lança `RetrySession`, não confirma o offset original. A DLQ poderá receber cópia duplicada em reentrega.

E2 — Commit de offset falha: lança `RetrySession`; a mensagem poderá ser entregue novamente. A PK e o hash tornam a persistência idempotente, sem garantia de exactly-once do fluxo inteiro.

E3 — Falha inesperada: sessão é reaberta sem registrar payload no log e sem avanço deliberado do offset.
