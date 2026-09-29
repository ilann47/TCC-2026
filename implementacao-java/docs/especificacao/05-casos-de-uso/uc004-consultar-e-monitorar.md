> Links: [[../README]] · [[../04-requisitos-funcionais]] · [[uc001-registrar-sincrono]]

# UC004 — Consultar registro e monitorar dependências

## Objetivo e regras de negócio

RN013: consulta por ID observa o banco, não o ACK do Kafka. RN014: `/live` só informa que a API responde; `/health` testa a dependência principal — PostgreSQL na API síncrona e Kafka na assíncrona.

## Atores

Aplicação cliente ou operador experimental.

## Pré-condição, pós-condição e ativação

Pré-condição: API HTTP ativa. Ativação: `GET /audit/{event_id}`, `GET /live` ou `GET /health`. Pós-condição: nenhuma mutação de domínio; resposta expressa o estado observado naquele instante.

## Fluxo principal de consulta

1. Cliente envia UUID em `GET /audit/{event_id}` à API síncrona.
2. Repositório consulta `audit_records` pela PK.
3. Se encontrado, responde `200` com hash e `persisted_at`.

## Fluxos alternativos

A1 — `/live`: responde `200`, `status=alive`, sem consultar banco/broker.

A2 — `/health`: responde `200`, `status=ready`, quando a dependência relevante estiver acessível.

## Fluxos de exceção

E1 — Registro inexistente: `404`, `detail.reason=event_not_found`.

E2 — Banco indisponível na consulta: `503`, `detail.reason=database_unavailable`.

E3 — Dependência indisponível na saúde: `503`, `detail.status=not_ready`, com `dependency=postgresql` ou `kafka`.

E4 — Identificador de caminho inválido: `422`, `detail.reason=invalid_event` na API síncrona.
