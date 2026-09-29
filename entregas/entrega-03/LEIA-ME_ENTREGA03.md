# Entrega 03 — fechamento do desenvolvimento

## Arquivos para envio

- `Entrega03_TCC_Fechamento_Desenvolvimento.pdf` — texto completo; o Capítulo 4 contém a modelagem e a descrição do protótipo.
- `Entrega03_Apresentacao_10min_v3.pptx` — 10 slides, com notas de fala em linguagem natural.
- `Entrega03_Fontes_Editaveis.zip` — LaTeX, PlantUML/PNG, código Python, testes e Docker Compose. O ponto de entrada do texto é `modelo.tex`.

## Inventário da modelagem entregue

| Vista | Arquivos PlantUML | Situação |
|---|---|---|
| Casos de uso | `casos-de-uso.puml`, `casos-experimento.puml` | Aplicação e operação de avaliação; UC01–UC07 especificados no Capítulo 4. |
| Atividades | `atividade-sincrona.puml`, `atividade-assincrona.puml`, `atividade-consumidor.puml` | Fluxos de sucesso, duplicata, conflito, ACK, retry e DLQ. |
| Classes/módulos | `classes-dados.puml`, `classes.puml` | DTOs, persistência e módulos identificados conforme o código Python. |
| Sequência | `sequencia-sincrona.puml`, `sequencia-assincrona.puml` | Diferença temporal entre HTTP 201, HTTP 202, commit no banco e offset. |
| Componentes | `componentes.puml` | Dependências principais; o caminho de DLQ está detalhado nas outras vistas. |
| Implantação | `implantacao.puml` | Cinco serviços permanentes, rede Compose e dois volumes nomeados. |
| Arquitetura | `arquitetura-sincrona.puml`, `arquitetura-assincrona.puml` | Caminhos das duas variantes. |
| Banco conceitual e lógico | `mer-atual.puml`, `modelo-logico-atual.puml`, `mer-proposto.puml`, `modelo-logico.puml` | Os dois arquivos `*-atual` representam o banco implementado. Os dois arquivos de extensão são **propostas**, não tabelas existentes. |

O esquema operacional efetivo contém apenas `audit_records` (10 colunas, PK em `event_id`, índice não único em `entity_id`, nenhuma FK). O mapeamento está em `implementacao/app/shared/database.py`; o dicionário, o modelo físico e a regra de unicidade/idempotência estão no Capítulo 4. Logs e métricas da execução são arquivos externos. Os quatro wireframes do capítulo são propostas de interface, não telas implementadas.

## Autoria, fontes e limites

Os diagramas foram elaborados para este protótipo a partir do código e de `docker-compose.yml`; as figuras indicam a autoria no PDF. O referencial e a seção de referências do TCC identificam os artigos científicos usados para fundamentar REST, Kafka, sistemas distribuídos, implantação e método experimental. Não há alegação de resultado comparativo definitivo nesta entrega.

Verificação desta cópia: compilação LaTeX/BibTeX sem referências indefinidas e 24 testes offline aprovados (`pytest -m 'not integration'`). Isso não equivale a uma nova execução dos testes de integração em contêineres nem à coleta científica definitiva.
