> Links: [[README]] · [[04-requisitos-funcionais]] · [[05-casos-de-uso/uc004-consultar-e-monitorar]]

# 6. Protótipos de interface

O artefato implementado é uma API e um consumidor sem interface gráfica. Não existem telas de login, dashboard, listagem, cadastro, edição, exclusão ou relatórios. Inventar screenshots dessas telas falsearia o estado do código. O “protótipo de interface” abaixo descreve as superfícies reais de entrada e saída.

| Superfície | Entrada | Saída observável | Ausência deliberada |
|---|---|---|---|
| `POST /audit` síncrono | JSON `AuditEvent` e `X-Run-ID` UUID opcional | `201 AuditStored`, `409`, `422` ou `503` | Não há formulário, edição ou exclusão |
| `POST /audit` assíncrono | Mesmo JSON/header | `202 AuditAccepted`, `422` ou `503` | Não mostra persistência concluída |
| `GET /audit/{event_id}` | UUID no caminho | `200 AuditStored`, `404` ou `503` | Não há listagem/paginação |
| `GET /live` | Sem corpo | `200 {"status":"alive"}` | Não testa dependência |
| `GET /health` | Sem corpo | `200 ready` ou `503 not_ready` | Não é dashboard |
| Consumidor/DLQ | Registro Kafka | Linha no PostgreSQL ou envelope na DLQ; logs JSON | Não há console de reprocessamento |

O exemplo completo de corpo JSON e comandos para executar estão no [README operacional](../../README.md). Evidência visual futura deve ser captura real da execução, não mockup apresentado como tela existente.
