# Protótipo experimental — cópia de revisão

Esta versão pertence à cópia `TCC_Revisao_Completa_2026-09-07`. O projeto anterior foi preservado. A arquitetura compara o mesmo contrato, hash e repositório, alterando o caminho de comunicação. Testes de verificação funcional e ensaios exploratórios não substituem as repetições previstas no capítulo metodológico.

## Contratos implementados

| Operação | Significado |
| --- | --- |
| `POST /audit` síncrono | `201 persisted` somente depois do COMMIT; `201 duplicate` quando UUID e hash já existem; `409` para UUID com conteúdo diferente. |
| `POST /audit` assíncrono | `202 accepted` somente após callback de entrega sem erro do Kafka; não confirma persistência no PostgreSQL. |
| Falha de publicação | `503`, `detail.acceptance=rejected` para buffer local cheio/produtor ausente; `unknown` para timeout/erro de entrega. A mensagem pode ainda ter sido entregue. |
| Falha do PostgreSQL síncrono | `503` com `acceptance=unknown`: uma falha de comunicação pode impedir a confirmação de um COMMIT já executado. |
| `GET /audit/{event_id}` síncrono | Consulta UUID/hash/marcador temporal de um registro visível; `404` quando ausente; `503` para indisponibilidade do banco. Não retorna o payload. |
| `GET /health` | Readiness: banco/esquema na API síncrona; metadados do tópico e líderes na assíncrona. Não comprova funcionamento de todo o fluxo. |
| `GET /live` | Processo HTTP ativo; não verifica dependências. |

Em qualquer reenvio, conservar **o evento completo**, inclusive `event_id` e `occurred_at`. A API pode preencher os dois campos quando omitidos, mas o cliente experimental sempre os fornece. O consumidor exige ambos no registro Kafka, evitando gerar outra identidade durante uma reentrega. A idempotência do produtor protege retransmissões da sua sessão; a chave primária e o hash no PostgreSQL protegem a persistência entre sessões e processos.

O cabeçalho opcional `X-Run-ID` aceita um UUID e acompanha o evento no header Kafka `x-run-id`. Ele é metadado de observação e não altera o hash canônico. A consulta está somente na API síncrona para evitar acoplar o produtor assíncrono ao banco.

## Consumidor, retry e DLQ

Cada registro é validado e processado individualmente. O padrão é três tentativas totais (primeira execução e duas repetições), com esperas de 0,5 e 1 segundo. Timeout, número de tentativas e teto do backoff são configuráveis, com limite de orçamento inferior ao intervalo máximo de poll. Os limites do banco abrangem conexão, espera do pool, instruções SQL e locks; falhas extremas de rede/sistema operacional ainda podem exceder estimativas e devem ser observadas nos ensaios.

Eventos inválidos, conflito de conteúdo e esgotamento das tentativas seguem para `audit-events-dlq`. O consumidor exige o ACK da DLQ antes de confirmar o offset da origem. Se a publicação na DLQ ou o commit do offset falhar, a sessão termina, reabre e relê a origem não confirmada. `enable.auto.commit` e `enable.auto.offset.store` estão desativados. Uma falha inesperada também reinicia a sessão sem avançar o offset.

A DLQ preserva o conteúdo original em base64, chave, motivo controlado e identidade `tópico:partição:offset`. Ela pode conter payload sensível e não deve ser publicada como evidência sem tratamento. A publicação na DLQ e o commit da origem não são uma transação única: a DLQ pode conter duplicatas após uma falha entre esses passos, identificáveis pelo `source_message_id`. Não há reprocessamento automático da DLQ; é necessário revisar o motivo antes de reenviar o mesmo evento. Esgotar retries e confirmar a DLQ não significa persistir o evento de negócio.

## Banco e marcação temporal

`audit_records.event_id` continua sendo a chave primária. `INSERT ... ON CONFLICT DO NOTHING` resolve a disputa pela chave; uma instrução seguinte em `READ COMMITTED` lê o registro vencedor e compara seu hash. Conteúdo diferente não substitui a linha existente. O retorno ocorre somente depois da saída bem-sucedida da transação. O PostgreSQL é configurado com `synchronous_commit=on`.

A inicialização adiciona apenas a coluna `persisted_at TIMESTAMPTZ` se ausente. Linhas antigas permanecem nulas, sem inventar data histórica. Novas linhas recebem `clock_timestamp()` no INSERT: esse valor antecede o COMMIT e **não é o instante exato de conclusão**. O marco JSON `commit_completed`, emitido depois que o COMMIT retorna, é a observação de conclusão da aplicação. A consulta HTTP comprova visibilidade e introduz atraso de sondagem.

## Logs e métricas

Cada marco da aplicação é uma linha JSON com `milestone`, `timestamp` UTC, `wall_time_ns`, `monotonic_ns`, `run_id` e `variant`, além dos campos permitidos para o evento. Os logs não incluem payload, ator, URL de conexão, credenciais nem mensagens arbitrárias de exceção.

- `request_received`: entrada na função após validação do contrato HTTP.
- `broker_acknowledged`: confirmação Kafka, com tópico, partição e offset.
- `message_received` e `processing_attempt`: leitura e tentativa, vinculadas ao offset; permitem contar reentregas e tentativas separadamente.
- `retry_scheduled`: motivo controlado e espera aplicada.
- `commit_completed`: COMMIT retornou; `status=persisted` ou `duplicate` e `event_id`.
- `dlq_acknowledged`: falha encaminhada com ACK; ainda não é sucesso de persistência.
- `offset_committed`: confirmação síncrona do offset de origem.

Não comparar diretamente HTTP `201` e `202` como se ambos representassem conclusão. A latência ponta a ponta deve usar o marco de COMMIT correlacionado ao envio. Relógios UTC entre máquinas exigem sincronização/avaliação de erro; contadores monotônicos de hosts diferentes não são comparáveis. Nanosegundos na representação não garantem precisão física de nanossegundos. A resolução e o ponto de coleta do gerador de carga devem constar no relatório. Backlog é consultado no Kafka; os logs, isoladamente, não o medem.

## Ambiente isolado e execução

Dependências diretas são fixadas em `requirements.txt`. O Compose usa Python 3.12, PostgreSQL 16 e Apache Kafka 3.9.1. Registrar também a versão de patch, digest das imagens e dependências transitivas efetivas de cada execução.

Defina `POSTGRES_PASSWORD` no ambiente local usando uma senha exclusiva, aleatória e compatível com URL (por exemplo, caracteres hexadecimais); não a registre no relatório. O Compose não contém senha fixa. O projeto tem nome `tcc-revisao-20260907`, volumes próprios e portas publicadas somente em loopback: REST síncrono 18000, assíncrono 18001, PostgreSQL 15432 e Kafka externo 19092. O listener Kafka interno é `kafka:9092`. Não usar volumes ou serviços de outros projetos.

```bash
docker compose -p tcc-revisao-20260907 config --quiet
docker compose -p tcc-revisao-20260907 up --build -d
docker compose -p tcc-revisao-20260907 ps
docker compose -p tcc-revisao-20260907 logs --no-color sync-api async-api consumer
```

No Windows desta revisão, o Docker está no WSL Ubuntu; executar os comandos no terminal desse ambiente, dentro desta cópia, com a variável definida. O serviço `kafka-volume-init` ajusta somente o proprietário da raiz do volume isolado para o UID 1000 utilizado pela imagem Kafka. `kafka-init` cria os dois tópicos com uma partição e fator de replicação 1, sem criação automática de tópicos. APIs, consumidor e dependências reiniciam com `unless-stopped`.

Os limites explícitos de recursos são configurações exploratórias do piloto: 1 CPU por serviço, PostgreSQL 512 MiB, Kafka 1 GiB e cada processo Python 256 MiB. Não representam calibração final nem acrescentam observações ao protocolo C1–C5. Uma única partição e um único broker não demonstram tolerância à perda do broker ou garantias de cluster replicado; `acks=all` nesse ambiente aguarda somente a réplica disponível.

## Verificação

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q -m "not integration"
```

Os testes unitários usam dublês explícitos para simular falhas e verificar ordem de operações. Para testes de integração com os serviços reais do projeto isolado:

```bash
docker compose -p tcc-revisao-20260907 --profile tests run --rm tests
```

Sem `RUN_INTEGRATION=1`, os testes reais são marcados como não executados. Ao habilitar a opção, serviços indisponíveis fazem o teste falhar. A suíte real verifica concorrência/duplicidade, conflito, publicação e consumo, persistência, mensagens inválidas e DLQ. Ensaios de parada de serviço, retomada, carga e métricas são executados separadamente pelos scripts experimentais, preservando resultados brutos. Registros sintéticos gerados pelos testes são mantidos como evidência no ambiente isolado. Não executar a suíte em dados reais.

Foi incluído `tests/integration_faults.py`, um verificador funcional que para e inicia serviços **somente** no projeto `tcc-revisao-20260907`, sem apagar dados. Ele registra pedidos/respostas sintéticos, operações de controle, linhas SQL, backlog, DLQ e marcos JSON. Ele espera a configuração local em `.runtime/compose.env`; esse arquivo contém a senha e não integra as evidências nem o pacote público. Executar no WSL:

```bash
python3 tests/integration_faults.py --evidence ../../revisao/evidencias_funcionais
```

Essa execução verifica o comportamento com consumidor parado, broker indisponível, banco indisponível, retomada, mensagem inválida, duplicidade e conflito. Seus volumes pequenos e tempos de observação servem à validação funcional e não são resultados da comparação científica C1–C5. A situação efetivamente verificada consta em `../../revisao/prototipo_relatorio.md` e nos relatórios JUnit.

## Fontes técnicas consultadas para implementação

Estas fontes oficiais documentam APIs e comportamento das dependências; não são adições às referências científicas do TCC.

- [Cliente Python Kafka: callbacks, poll, flush e commits](https://docs.confluent.io/kafka-clients/python/current/overview.html).
- [API Python Confluent: callback por mensagem e verificação do retorno de commit](https://docs.confluent.io/platform/7.9/clients/confluent-kafka-python/html/index.html).
- [PostgreSQL 16: INSERT e ON CONFLICT](https://www.postgresql.org/docs/16/sql-insert.html).
- [PostgreSQL 16: isolamento READ COMMITTED e visibilidade após conflitos](https://www.postgresql.org/docs/16/transaction-iso.html).
