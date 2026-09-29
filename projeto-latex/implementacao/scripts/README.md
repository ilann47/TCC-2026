# Coleta reproduzível

## Continuidade do piloto em 08/09/2026

O autor escolheu PostgreSQL indisponível nas duas variantes para C4. Foi acrescentado o perfil `pilot`, que identifica os dados como calibração e nunca os torna elegíveis como repetições definitivas. `protocol.unfrozen.json` continua deliberadamente não aprovado.

Exemplo de verificação do instrumento após a correção de limites de fase:

```bash
python3 scripts/run_experiment.py pilot --stage observer_smoke_boundary_fix --variant both --duration 10 --warmup 5 --rate 5 --drain 10 --output evidence/pilot-20260908/observer-smoke-fixed
```

O coletor padrão é agora `--lag-method observer`: cliente Kafka persistente e somente leitura em contêiner separado, com imagem do consumidor, 0,25 CPU e 128 MiB de limite exploratório. Esses limites não são capacidade medida. O consumo do observador e do gerador aparece separadamente em `resources.jsonl`. `cli` preserva o mecanismo anterior para comparação controlada de custo; `none` serve exclusivamente ao controle exploratório sem coleta de offsets e não produz evidência suficiente de lag assíncrono. O healthcheck da topologia Kafka ainda usa CLI e integra o custo operacional da configuração; não foi silenciosamente removido.

No piloto, `--burst-rate`, `--burst-at` e `--burst-seconds` permitem verificar as três fases de C3 sem liberar o protocolo definitivo. O controlador de C4 registra solicitação e conclusão de parada/retomada; para PostgreSQL, observa prontidão por `SELECT 1`. O gate exige correspondência entre a falha planejada e os marcos efetivamente observados.

O gerador preserva o orçamento `rate × seconds` de cada fase. Iterações adicionais que o agendador iniciar no limite são registradas como `scheduler_excess_iteration` e não enviam HTTP nem usam o payload da fase seguinte. O resumo reconcilia essas iterações separadamente; nenhum envio descartado pelo k6 é ocultado. Duas verificações iniciais que abortaram antes dessa correção continuam preservadas em `observer-smoke` e não foram reclassificadas como sucesso.

`recovery.py` analisa prontidão, persistência, coorte pendente, DLQ e throughput sustentado separadamente. Janela, taxa de referência, fração e tamanho de bin são argumentos explícitos. Ainda não é uma escolha científica automática de critério global de recuperação. Resultados definitivos dependem de aprovação desses parâmetros.

Fontes operacionais para o gerador: [constant-arrival-rate](https://grafana.com/docs/k6/latest/using-k6/scenarios/executors/constant-arrival-rate/) e [identificadores de execução](https://grafana.com/docs/k6/latest/javascript-api/k6-execution/). Os limites de fase foram corrigidos por evidência da execução local, não por supor que a documentação garanta volume exato em toda condição de temporização.

As seções abaixo descrevem também o histórico de validação anterior. Os novos dados e o estado do piloto estão em `../../revisao/PILOTO_EM_ANDAMENTO.md`.

Este diretório contém o gerador k6, o executor Docker e a análise offline. A coleta curta é validação funcional do instrumento e do caminho real; não é piloto de capacidade nem experimento definitivo do TCC.

## Pré-requisitos e execução

Executar em Linux/WSL, dentro de `Projeto/implementacao`, com Docker Engine e Compose acessíveis. A topologia deve estar construída e saudável no projeto exclusivo `tcc-revisao-20260907`. O arquivo privado `.runtime/compose.env` contém `POSTGRES_PASSWORD`; o executor somente passa seu caminho ao Compose, não imprime valores nem exporta `Config.Env`.

```bash
python3 scripts/run_experiment.py validation --variant both --duration 10 --rate 5 --drain 10
```

O comando executa primeiro o fluxo síncrono e depois o assíncrono, ambos com taxa oferecida de 5 eventos/s durante 10 segundos. Esses valores são configuração explícita de demonstração funcional; não substituem os parâmetros científicos. Cada repetição cria UUIDs exclusivos e não apaga banco, tópico ou volume.

Falha funcional opcional, apenas para uma topologia experimental livre de outra execução:

```bash
python3 scripts/run_experiment.py validation --variant async --duration 15 --rate 5 --drain 15 --fault-service consumer --fault-at 4 --fault-seconds 4
```

Também são suportados os serviços `postgres`, `kafka`, `sync-api` e `async-api`. A interrupção é ancorada no início real da fase de medição registrado pelo k6. O serviço é retomado no bloco de limpeza mesmo se a coleta for interrompida. O comando não decide qual falha deve representar C4: essa decisão científica precisa constar do protocolo congelado.

Outras opções: `--env-file`, `--output`, `--warmup`, `--drain`, `--sample-interval`, `--vus`, `--max-vus`, `--http-timeout`, `--payload-padding`. A ausência de aquecimento no perfil curto é intencional e registrada como validação funcional. Falhas não geram sucesso artificial; o executor guarda o tipo do erro no manifesto e retorna código diferente de zero.

## Artefatos

Cada `evidence/runs/<run_id>` contém:

- `config.json`: variante, fases, duração, taxa, recursos do gerador e demais parâmetros;
- `payloads.json`: eventos sintéticos preparados antes do envio, inclusive UUID e instante preservado;
- `manifest.json`: OS/CPU/Docker, limites dos contêineres, referências/digests das imagens, checksums dos fontes, instantes de falha/retomada e saídas de execução;
- `source_snapshot/`: cópia de código, testes, scripts, Compose, Dockerfile e dependências usados na coleta; `.runtime` e segredos são excluídos por lista explícita de fontes;
- `generator.jsonl`: marcos de envio e resposta HTTP, por evento, variante, cenário e fase;
- `k6-points.jsonl`, `k6-summary.json`, `generator-process.log`: amostras e resumo do gerador, incluindo iterações descartadas;
- `application.jsonl`: somente marcos JSON correlacionados da aplicação; mensagens livres de bibliotecas não são copiadas para evitar expor credenciais de conexão;
- `database.csv`: linhas sintéticas correspondentes à execução, UUID/hash e `persisted_at`;
- `resources.jsonl`: amostras reais de CPU e memória dos contêineres;
- `lag.jsonl`: posições de partição no Kafka e lag; host/identificador do cliente são descartados;
- `inputs.sha256.json`: sela os inputs concluídos antes de normalizar, incluindo manifesto, configuração, dados brutos e snapshots; introduzido no endurecimento final do gate;
- `protocol.json` e `pilot_evidence.snapshot`: obrigatórios nos ensaios definitivos futuros, com hashes na configuração; preservam o protocolo congelado e um arquivo de relatório do piloto, sem depender depois de caminho externo mutável;
- `analysis/events.csv`, `analysis/summary.json`, `analysis/backlog_uuid.csv`, `analysis/backlog_offsets.csv`;
- `checksums.sha256.json`: digest de cada arquivo, inclusive as cópias de fontes e os dados brutos.

Nada é sobrescrito. A normalização inicial cria `analysis` somente se não existir. Para reanalisar os mesmos dados com outro código, usar um novo diretório:

```bash
python3 scripts/normalize.py evidence/runs/UUID --output evidence/reanalysis/UUID-v2
```

## Definição das métricas

O mesmo marco é usado nas duas variantes: `commit_completed.wall_time_ns / 1e6 - request_sent.sent_at_ms`. O log é emitido depois do retorno do commit real. `persisted_at` é horário SQL da inserção e não substitui esse marco. A medição usa relógio de parede do mesmo host Docker/WSL; `Date.now()` tem resolução de milissegundos. Durações negativas são sinalizadas, e nunca limitadas artificialmente a zero. Os relógios monotônicos de processos distintos não são subtraídos.

`http_wall_duration_ms` cobre a chamada HTTP observada pelo gerador. `http_transport_duration_ms` vem de `Response.timings.duration`, que não inclui todo o tempo inicial de conexão. O tempo de ACK do produtor, quando registrado, também é separado. Assim, responder `202` mais cedo não é interpretado como persistir mais cedo.

Throughput é o número de UUIDs novos com commit dentro da janela de medição dividido pela duração programada. Completamentos após a janela permanecem na conciliação e na distribuição de conclusão, mas não são incorporados artificialmente ao throughput da janela anterior. Reentregas reconhecidas como `duplicate` não contam como novas linhas.

O gerador usa chegada aberta `constant-arrival-rate`, com uma iteração por evento. `dropped_iterations` mede oportunidades de carga não enviadas, não requisições com erro HTTP. A taxa realmente oferecida é calculada a partir dos marcos de envio. Payloads de variantes diferentes usam UUIDs/run_id diferentes para impedir que o segundo fluxo seja apenas uma sequência de duplicatas da primeira execução; contrato, tamanho, tipos e distribuição sintética permanecem equivalentes, com a mesma taxa absoluta.

DLQ confirmada, conflito rejeitado e UUID aceito ainda não conciliado ao término são estados diferentes. A ausência de conclusão no prazo não é automaticamente rotulada como perda. Backlog por UUID representa aceitos ainda sem commit; lag de Kafka representa diferença de posições, que não é o mesmo contador. `first_observed_zero_lag_after_resume_seconds` é um indicador descritivo com precisão limitada à amostragem; não demonstra sozinho recuperação sustentada do throughput.

Estatísticas descritivas por execução: N, média, mediana, desvio amostral (somente N≥2), mínimo, máximo, p95 e p99 por interpolação linear. Nenhum intervalo de confiança, teste de hipótese, vencedor arquitetural ou conclusão científica é gerado automaticamente. Ausência de amostra é `null`, não zero. Recursos são apresentados com timestamps brutos e resumo de toda a observação; uma análise científica precisa respeitar as fases e o custo dos coletores. A consulta de lag usa a CLI Kafka, que inicia uma JVM dentro do contêiner do broker e consome CPU/memória; o piloto deve quantificar ou substituir esse custo. A duração da consulta pode exceder o intervalo solicitado, por isso a análise usa os timestamps reais. Lag zero em todas as amostras não demonstra ausência de filas entre elas.

Um gráfico descritivo das coletas curtas pode ser gerado em ambiente com Matplotlib (validado com 3.11.1):

```bash
python scripts/plot_validation.py evidence/runs/UUID_SYNC evidence/runs/UUID_ASYNC --output evidence/comparacao-validacao
```

O comando produz PNG/SVG/PDF, tabela CSV e proveniência por hashes, mantendo o aviso de que os números são validação de desenvolvimento. Não instala Matplotlib como dependência da aplicação em medição.

## Bloqueio do protocolo definitivo

`protocol.unfrozen.json` é um formulário incompleto, não uma configuração pronta. Valores nulos exigem piloto e decisão metodológica. O perfil definitivo verifica congelamento explícito, evidência de piloto indicada, justificativa de C4, semente, taxa de referência comum, tolerância, carga/rajada/falha, parâmetros do gerador, 60 segundos de aquecimento, 300 segundos de medição e pelo menos dez repetições.

```bash
python3 scripts/run_experiment.py check-protocol --protocol scripts/protocol.unfrozen.json
```

Esse comando deve recusar o formulário inicial. Ele pode validar preenchimento, não a qualidade científica do piloto. Depois de calibrar e congelar um novo arquivo, a coleta exige opção explícita de reinicialização dos volumes exclusivos:

O normalizador aplica uma segunda barreira independente em `evidence_gate.py`, usando as mesmas regras de `protocol.py`. `eligible_definitive_observation` só pode ser verdadeiro se o perfil for definitivo, não houver inconsistências de instrumentação e todos os artefatos essenciais forem comprovados. São exigidos códigos inteiros de saída exatamente iguais a zero para carga, exportação SQL e logs; ausência ou `null` nunca equivalem a sucesso. Configuração, manifesto, payloads, marcos, SQL, summary/pontos k6, recursos, lag assíncrono, fontes e seus hashes, protocolo/piloto congelados, fases e timestamps são verificados. JSONL malformado, dados SQL não conciliados, recursos sem amostras e divergência de hash impedem elegibilidade.

A verificação usa o manifesto de inputs fechado **antes** da análise; `checksums.sha256.json`, que inclui os outputs, é produzido depois e não é uma dependência circular. Elegibilidade significa somente completude técnica de uma observação: não comprova qualidade do piloto, aprovação do autor, execução das outras repetições ou validade científica. `scientific_conclusion_produced` permanece falso. As duas coletas funcionais já preservadas antecedem esse endurecimento, continuam com seus fontes/hashes originais e não foram reescritas para aparentar conformidade retrospectiva.

```bash
python3 scripts/run_experiment.py definitive --protocol protocolo-congelado.json --reset-isolated-state
```

O reset verifica nomes e labels do projeto/volumes antes de executar `compose down --volumes` exclusivamente em `tcc-revisao-20260907`; não é usado pela validação curta. Esse comando apaga somente os dados transitórios da topologia experimental dedicada. Artefatos de execuções ficam fora dos volumes e são preservados. A coleta definitiva pode levar horas. A sequência por bloco usa semente registrada para randomizar variantes e aplica os mesmos parâmetros absolutos a ambas. C4 e C5 são coletados na mesma observação contínua (interrupção seguida de retomada), evitando perder o vínculo entre falha e recuperação.

## Testes offline

```bash
python3 -m unittest discover -s scripts/tests -v
```

Foram aprovados 36 testes offline: 18 de métricas/conciliação e 18 da barreira de evidências. Usam amostras sintéticas temporárias para verificar fórmulas, fases, relógios, deduplicação, ausência de dados, hashes, configuração congelada e preservação de arquivos. Um fixture completo pode passar a barreira estrutural para testar seu caminho positivo; esse dado inventado está restrito ao teste temporário e jamais é apresentado como piloto ou resultado do protótipo.

## Fontes operacionais

Estas fontes documentam a implementação do instrumento; não foram acrescentadas à bibliografia científica do TCC.

- [Release oficial k6 v1.4.0](https://github.com/grafana/k6/releases/tag/v1.4.0).
- [Executor constant-arrival-rate](https://grafana.com/docs/k6/latest/using-k6/scenarios/executors/constant-arrival-rate/).
- [Dropped iterations](https://grafana.com/docs/k6/latest/using-k6/scenarios/concepts/dropped-iterations/).
- [Métricas HTTP e fronteiras de duração](https://grafana.com/docs/k6/latest/using-k6/metrics/reference/).
- [Resumo exportado por handleSummary](https://grafana.com/docs/k6/latest/results-output/end-of-test/custom-summary/).
- [Formato e destino de logs](https://grafana.com/docs/k6/latest/using-k6/k6-options/reference/).
