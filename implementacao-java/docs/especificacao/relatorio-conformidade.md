> Links: [[README]] · [[10-requisitos-nao-funcionais]] · [[plano-refatoracao]]

# Relatório de conformidade da versão Java

## Implementado no código

| Item | Evidência | Verificação até agora |
|---|---|---|
| Contrato, defaults e validação | `AuditEvent`, `AuditEventDeserializer` | Teste unitário de omitido/nulo e limites básicos |
| JSON/hash compatível em fixture | `CanonicalEventCodec` | Teste contra string/hash gerados pelo Python |
| Persistência idempotente | `AuditRepository`, PK e migração V1 | Inspeção/compilação; integração real pendente de CI |
| `201` após transação | `SyncAuditController`/`AuditRepository` | Inspeção/compilação; smoke CI previsto |
| `202` após ACK Kafka | `AsyncAuditController`/`KafkaPublisher` | Inspeção/compilação; smoke CI previsto |
| DLQ e offset manual | `AuditMessageProcessor` | Testes unitários com dependências simuladas |
| Ambiente isolado | `docker-compose.yml` | Arquivo preparado; não executado localmente sem Docker |

## Divergências em relação ao modelo genérico de documentação

Não há empresa, autenticação, telas, entidades cadastrais múltiplas, relacionamentos FK ou relatórios de negócio. A ausência foi registrada nas seções 1, 3, 4 e 6. Não se adicionou funcionalidade artificial para satisfazer um template. A arquitetura é de protótipo acadêmico: Kafka com uma partição e sem proteção de transporte; isso está registrado nos RNF.

## Divergências entre Java e Python

O Java exige timestamp de entrada com offset quando fornecido; o FastAPI/Pydantic pode aceitar outras representações. O formato do erro `422` Java é resumido. O JSON/hash foi verificado com uma fixture representativa, não com todos os valores possíveis de ponto flutuante. Essas diferenças estão também em [paridade](../paridade.md). O banco Java é novo e isolado; Flyway V1 **não** deve ser aplicada ao banco Python já existente.

## Pendências de validação

1. Confirmar workflow GitHub Actions de build e smoke Docker após publicação.
2. Testar concorrência real sobre o mesmo `event_id`, conflito, retry, falha de ACK da DLQ e offset em broker real.
3. Executar cenário C4 e recuperação segundo protocolo congelado, com evidência separada de piloto e ensaio definitivo.
4. Conferir logs Java com o normalizador de métricas Python antes de reaproveitá-lo.

Nenhum resultado de carga, comparação quantitativa ou conclusão científica foi fabricado a partir dos testes unitários.
