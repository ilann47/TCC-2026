> Links: [[README]] · [[04-requisitos-funcionais]] · [[05-casos-de-uso/uc004-consultar-e-monitorar]]

# 6. Protótipos de interface

O artefato implementado consiste em duas APIs e um consumidor, sem frontend próprio da aplicação. Existe uma página Swagger UI gerada para documentar e testar manualmente ambas as APIs; ela não é o painel experimental proposto. Não existem telas próprias de login, dashboard, listagem, cadastro, edição, exclusão ou relatórios. Inventar screenshots dessas telas falsearia o estado do código. O “protótipo de interface” abaixo descreve as superfícies reais de entrada e saída.

| Superfície | Entrada | Saída observável | Ausência deliberada |
|---|---|---|---|
| `POST /audit` síncrono | JSON `AuditEvent` e `X-Run-ID` UUID opcional | `201 AuditStored`, `409`, `422` ou `503` | Não há formulário próprio da aplicação, edição ou exclusão |
| `POST /audit` assíncrono | Mesmo JSON/header | `202 AuditAccepted`, `422` ou `503` | Não mostra persistência concluída |
| `GET /audit/{event_id}` | UUID no caminho | `200 AuditStored`, `404` ou `503` | Não há listagem/paginação |
| `GET /live` | Sem corpo | `200 {"status":"alive"}` | Não testa dependência |
| `GET /health` | Sem corpo | `200 ready` ou `503 not_ready` | Não é dashboard |
| Consumidor/DLQ | Registro Kafka | Linha no PostgreSQL ou envelope na DLQ; logs JSON | Não há console de reprocessamento |
| Swagger UI único | Seleção da variante e requisição manual com JSON de exemplo | Contratos OpenAPI separados e resposta da API selecionada | Não mede carga nem apresenta indicadores experimentais |

O exemplo completo de corpo JSON e comandos para executar estão no [README operacional](../../README.md). Evidência visual futura deve ser captura real da execução, não mockup apresentado como tela existente.
