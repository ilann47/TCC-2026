# Paridade com a implementação Python

> Links: [[README]] · [[especificacao/README]]

Fonte comparada: protótipo Python da `Entrega03_Fechamento_Desenvolvimento_2026-09-29/Projeto-LaTeX/implementacao`, fora deste repositório. Este arquivo distingue intenção de equivalência, diferenças deliberadas e verificação efetiva.

| Aspecto | Python | Java | Estado |
|---|---|---|---|
| Evento | Oito campos; `event_id`, `occurred_at` e `payload` defaultados quando omitidos na API | Mesmos campos e defaults | Teste unitário parcial |
| Replay Kafka | `event_id` e `occurred_at` obrigatórios | Mesma exigência antes da desserialização | Teste unitário de evento inválido |
| JSON/hash | `model_dump(mode="json")`, `json.dumps` sem espaços e com chaves ordenadas, SHA-256 | `CanonicalEventCodec` | Fixtures Python com Unicode, objeto aninhado, `1.0`, `1e-5`, `1e-4`, `1e5` e microssegundos passaram |
| Síncrono | `201` após commit; duplicata com mesmo hash; `409` em conflito | Mesmo fluxo com JDBC e `READ COMMITTED` | Smoke real confirmou `201` persistido/duplicata e `503` sob C4; conflito real ainda pendente |
| Assíncrono | `202` após ACK individual do Kafka | `Future.get` do envio individual | Smoke real confirmou `202`, inclusive sob C4 |
| Consumidor | Commit manual após DB ou ACK da DLQ | `commitSync(offset+1)` após DB ou ACK da DLQ | Smoke real confirmou persistência normal; testes unitários cobrem DLQ/offset; DLQ real ainda pendente |
| Banco | `audit_records`; criação condicional no protótipo | Mesma tabela em banco novo, migração Flyway V1 | Não executar Flyway sobre o banco Python existente |
| Falha C4 | PostgreSQL interrompido nas duas variantes | Mesmo cenário planejado | Smoke automatizado passou; ensaio definitivo não executado |

Diferenças conhecidas: a entrada Java exige `occurred_at` com fuso/offset quando fornecido, enquanto Pydantic pode aceitar outras representações de `datetime`; erros de validação Java usam `detail.reason=invalid_event`, não a lista detalhada do FastAPI. A canonicalização de números de ponto flutuante foi coberta por fixture representativa, **não por prova para todo número JSON possível**. Antes de compartilhar uma carga entre versões ou comparar resultados entre linguagens, ampliar as fixtures e congelar o conjunto de entradas aceitas. Isso não altera a pergunta de pesquisa REST versus EDA.

Riscos de equivalência ainda pendentes: medir quantitativamente o comportamento sob falha de PostgreSQL, confirmar concorrência e conflito em PostgreSQL real, validar DLQ real e verificar os marcos de medição com os scripts de normalização. O [workflow de integração aprovado](https://github.com/ilann47/TCC-2026/actions/runs/36626692629) cobre um smoke funcional, não o protocolo experimental completo.
