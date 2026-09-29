> Links: [[README]] · [[10-requisitos-nao-funcionais]] · [[plano-refatoracao]]

# Relatório de conformidade da versão Java

## Implementado no código

| Item | Evidência | Verificação até agora |
|---|---|---|
| Contrato, defaults e validação | `AuditEvent`, `AuditEventDeserializer` | Teste unitário de omitido/nulo e limites básicos |
| JSON/hash compatível em fixtures | `CanonicalEventCodec` | Testes contra string/hash gerados pelo Python, inclusive fronteira de notação numérica |
| Persistência idempotente | `AuditRepository`, PK e migração V1 | Smoke CI confirmou linha nova e duplicata; concorrência real pendente |
| `201` após transação | `SyncAuditController`/`AuditRepository` | Smoke CI confirmou `201` e `503` sob falha de banco |
| `202` após ACK Kafka | `AsyncAuditController`/`KafkaPublisher` | Smoke CI confirmou `202` e posterior persistência normal; `202` continuou sob C4 |
| DLQ e offset manual | `AuditMessageProcessor` | Testes unitários com dependências simuladas; DLQ real pendente |
| Ambiente isolado | `docker-compose.yml` | Executado com sucesso no CI; Docker indisponível localmente |

## Divergências em relação ao modelo genérico de documentação

Não há empresa, autenticação, telas, entidades cadastrais múltiplas, relacionamentos FK ou relatórios de negócio. A ausência foi registrada nas seções 1, 3, 4 e 6. Não se adicionou funcionalidade artificial para satisfazer um template. A arquitetura é de protótipo acadêmico: Kafka com uma partição e sem proteção de transporte; isso está registrado nos RNF.

## Divergências entre Java e Python

O Java exige timestamp de entrada com offset quando fornecido; o FastAPI/Pydantic pode aceitar outras representações. O formato do erro `422` Java é resumido. O JSON/hash foi verificado com uma fixture representativa, não com todos os valores possíveis de ponto flutuante. Essas diferenças estão também em [paridade](../paridade.md). O banco Java é novo e isolado; Flyway V1 **não** deve ser aplicada ao banco Python já existente.

## Pendências de validação

O [workflow de 29/09/2026](https://github.com/ilann47/TCC-2026/actions/runs/36626692629) passou em build, testes, integração normal e smoke C4/recovery. Permanecem:

1. Testar concorrência real sobre o mesmo `event_id`, conflito, retry, falha de ACK da DLQ e offset em broker real.
2. Executar cenário C4 **quantitativo** segundo protocolo congelado, com evidência separada do smoke automatizado, do piloto e do ensaio definitivo.
3. Conferir logs Java com o normalizador de métricas Python antes de reaproveitá-lo.

Nenhum resultado de carga, comparação quantitativa ou conclusão científica foi fabricado a partir dos testes unitários.
