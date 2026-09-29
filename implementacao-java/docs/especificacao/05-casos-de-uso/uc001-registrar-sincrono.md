> Links: [[../README]] · [[../04-requisitos-funcionais]] · [[uc002-aceitar-assincrono]]

# UC001 — Registrar auditoria sincronamente

## Objetivo e regras de negócio

RN001: `event_id` identifica logicamente um evento imutável. RN002: o hash é SHA-256 do JSON canônico do evento, inclusive payload, excluindo `X-Run-ID`. RN003: `201` só é devolvido depois de concluída a transação no PostgreSQL. RN004: repetir o mesmo ID e conteúdo devolve `duplicate`, sem segunda linha; mesmo ID com conteúdo diferente gera conflito `409`.

## Atores

Aplicação cliente; PostgreSQL como dependência externa.

## Pré-condição, pós-condição e ativação

Pré-condição: API em execução e evento JSON de entrada; conexão com o banco é necessária para sucesso. Ativação: `POST /audit` na API síncrona. Pós-condição de sucesso: existe uma única linha para o ID e a resposta inclui `event_id`, `status`, `content_hash` e `persisted_at`. Em erro `503`, o cliente não deve assumir rejeição definitiva: `acceptance=unknown`.

## Fluxo principal

1. Cliente envia JSON; opcionalmente `X-Run-ID` UUID.
2. Filtro valida o header; desserializador valida os campos e aplica defaults somente aos omitidos.
3. Controlador registra `request_received`.
4. Repositório calcula hash, abre transação `READ COMMITTED` e tenta `INSERT ... ON CONFLICT DO NOTHING RETURNING`.
5. Se a inserção ocorrer, a transação é concluída e `commit_completed` é registrado.
6. Controlador registra `persistence_confirmed` e responde `201` com `status=persisted`.

## Fluxos alternativos

A1 — Duplicata: após conflito na PK, uma consulta dentro da transação encontra o mesmo hash; responde `201` com `status=duplicate`, preservando a linha original. Não há alteração ou exclusão. A consulta do registro é descrita em UC004.

## Fluxos de exceção

E1 — Conteúdo incompatível para mesmo ID: o hash difere; responder `409` com `detail.reason=event_id_content_conflict` e manter a linha original.

E2 — Banco indisponível: registrar `request_failed`; responder `503`, `detail.reason=database_unavailable`, `acceptance=unknown`.

E3 — Contrato inválido: responder `422` com `detail.reason=invalid_event`. `X-Run-ID` malformado gera `400`, `detail.reason=invalid_run_id`.
