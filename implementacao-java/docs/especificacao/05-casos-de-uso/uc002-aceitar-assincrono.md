> Links: [[../README]] · [[../04-requisitos-funcionais]] · [[uc001-registrar-sincrono]] · [[uc003-consumir-evento]]

# UC002 — Aceitar auditoria assincronamente

## Objetivo e regras de negócio

RN005: `202` significa ACK do broker para a publicação individual; não significa gravação no PostgreSQL. RN006: `entity_id` é a chave Kafka e o valor é o JSON canônico. RN007: tempo esgotado ou erro de envio pode deixar aceitação `unknown`; buffer cheio antes do envio pode ser `rejected`. RN008: a API assíncrona não se conecta ao PostgreSQL.

## Atores

Aplicação cliente; Kafka como dependência externa.

## Pré-condição, pós-condição e ativação

Pré-condição: API ativa, tópico criado e evento válido. Ativação: `POST /audit` na API assíncrona. Pós-condição de sucesso: Kafka confirmou a mensagem; o consumidor ainda deve processá-la. Não há garantia de persistência na resposta.

## Fluxo principal

1. Cliente envia evento JSON; o header opcional `X-Run-ID` é validado.
2. API registra `request_received`, serializa evento e calcula chave a partir de `entity_id`.
3. Publicador envia com `acks=all` e idempotência do produtor habilitada.
4. A API espera a confirmação individual limitada por `DELIVERY_TIMEOUT_MS`.
5. Após ACK, registra `broker_acknowledged` com tópico, partição e offset e responde `202`, `status=accepted`.

## Fluxos alternativos

A1 — O consumidor persiste mais tarde: o cliente consulta o mesmo `event_id` pela API síncrona (UC004) para observar o estado materializado. Esse passo não faz parte da confirmação `202`.

## Fluxos de exceção

E1 — Timeout/falha de entrega: responder `503` com `acceptance=unknown`; não presumir que o broker rejeitou a mensagem.

E2 — Buffer local cheio: responder `503` com `acceptance=rejected`, `reason=producer_buffer_full`.

E3 — Evento ou `X-Run-ID` inválido: `422 invalid_event` ou `400 invalid_run_id`, respectivamente.
