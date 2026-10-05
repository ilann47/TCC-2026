# Piloto de instrumentação — k6 + analisador Java

Este material prepara a coleta solicitada pela orientadora. É um **piloto curto de conferência dos instrumentos**, não uma execução dos cenários definitivos C1–C5, nem uma comparação suficiente para confirmar as hipóteses do TCC. Os capítulos 5 e 6 dependem da campanha experimental posterior.

A primeira validação real, suas tentativas inválidas e o diagnóstico do ambiente estão no [relatório de 05/10/2026](PILOTO-2026-10-05.md).

## Executar

No WSL/Linux, dentro de `implementacao-java`, com Docker e Compose disponíveis:

```bash
docker compose up -d
bash experimento/pilot.sh sync
bash experimento/pilot.sh async
```

Mantenha o Docker em execução e use a mesma sessão de terminal. Aguarde as dependências ficarem saudáveis. O script exige os cinco serviços em execução, verifica a saúde de PostgreSQL/Kafka e o k6 consulta a saúde das APIs antes de enviar os eventos. Não precisa de k6, Maven ou Java instalados no WSL: o gerador e o analisador executam em contêineres. A primeira execução pode levar mais tempo para baixar dependências e compilar/testar o analisador.

Por padrão, cada execução usa **2 eventos/s por 10 s**, quatro usuários virtuais disponíveis e uma espera de cinco segundos para observar a persistência. Isso é uma carga conservadora para validar a coleta, **não a carga de referência do experimento**. Exemplo de ajuste, ainda limitado a um piloto:

```bash
RATE=5 DURATION=15s VUS=8 DRAIN_SECONDS=10 bash experimento/pilot.sh async
```

Limites: `RATE=1..20`, `DURATION=1s..60s`, `VUS=1..50`, `DRAIN_SECONDS=1..30`. Um `RUN_ID` UUID novo é gerado automaticamente. É possível fornecê-lo, mas **não reutilize um UUID**, nem mesmo entre variantes. O script recusa sobrescrever uma pasta existente. Ele não apaga tabelas, mensagens ou volumes. Os registros do piloto permanecem no PostgreSQL com `source=k6-pilot-<RUN_ID>`; a amostra sintética fica isolada por identificador, **não por instância física de banco**. Isso não substitui a estratégia de isolamento/reset que será definida para a campanha final.

## O que foi implementado

- `pilot.js`: carga com taxa de chegada constante, evento e requisição identificados por UUID; `X-Run-ID` permite correlacionar os marcos do protótipo. A resposta é validada por status e pelo `event_id` devolvido.
- `pilot.sh`: verifica o ambiente, compila/testa o analisador, executa o k6, observa uma janela de drenagem, exporta os logs e somente os registros desta execução, coleta amostras brutas de CPU/memória e executa a conciliação.
- `analyzer/`: ferramenta independente em Java 21. Cruza os dados do cliente, `commit_completed` e o banco; verifica campos, payload inteiro e SHA-256 esperado por um encoder independente e específico do conjunto sintético do piloto. Não depende do codec de produção.

O executor `constant-arrival-rate` inicia iterações a uma taxa definida, independentemente da duração das respostas. Não há `sleep` no corpo da iteração. Usuários virtuais insuficientes podem causar `dropped_iterations`; qualquer ocorrência invalida a conferência deste piloto. Fundamentação: [executor na documentação do k6](https://grafana.com/docs/k6/latest/using-k6/scenarios/executors/constant-arrival-rate/).

## Arquivos de cada execução

Os dados locais ficam em `.runtime/pilot/<RUN_ID>-<sync|async>/`, fora do Git:

| Arquivo | Conteúdo |
|---|---|
| `manifest.txt` | Parâmetros, horários, commit, estado do checkout, imagens e limites dos contêineres; sem exportar senhas. |
| `k6.jsonl` | Amostras brutas do gerador, com as tags de correlação. |
| `k6-console.txt` | Saída e diagnóstico do k6. |
| `app.log` | Marcos JSON das duas APIs e do consumidor filtrados pelo UUID da execução, sem depender de filtro de horário do daemon. |
| `database.jsonl` | Eventos persistidos cujo `source` corresponde ao UUID desta execução. |
| `resources.csv` | Amostras brutas de `docker stats` para os cinco serviços. O horário é o início de cada lote, não o instante exato de cada leitura. |
| `resources-errors.log` | Falhas do coletor de recursos, se ocorrerem. |
| `events.csv` | Uma linha por evento com os intervalos e evidências de conclusão. |
| `summary.json` | Contagens, distribuição dos intervalos, inconsistências e `instrument_valid`. |
| `analyzer-console.txt` | Saída do analisador. |
| `SHA256SUMS` | Checksums para conferir alterações posteriores nos arquivos coletados. |

Para verificar os checksums, execute `sha256sum -c SHA256SUMS` dentro da pasta da execução. Eles detectam alterações, mas não constituem assinatura digital nem garantia de autenticidade. Preserve também a versão do código: um piloto com checkout modificado é marcado como `working_tree=dirty` e não deve entrar na campanha definitiva.

## Como interpretar os tempos

| Campo no resumo | Início → fim | Significado |
|---|---|---|
| `http_duration_ms` | Intervalo nativo `http_req_duration` do k6 | Tempo do envio/espera/recebimento HTTP; não inclui todas as etapas anteriores de conexão/bloqueio. |
| `send_to_response_ms` | Amostra `pilot_sent` → amostra `pilot_response` | Intervalo instrumentado que inclui a chamada HTTP e a conferência da resposta. Não é idêntico ao tempo nativo do k6. |
| `send_to_commit_ms` | Amostra `pilot_sent` → marco `commit_completed` | Intervalo até o código observar o retorno da transação de persistência. Não usa `persisted_at`. |

O marco `commit_completed` é emitido **após** o retorno da transação. Inclui a pequena demora até emitir o log; não é uma instrumentação interna do instante físico de fsync. A resposta `201` da variante síncrona vem após a persistência; `202` da assíncrona confirma a publicação no Kafka, não a gravação no banco. Os três tempos permanecem separados na análise.

O resumo exibido no console do k6 inclui também as requisições de saúde de `setup()`. Para os tempos dos eventos, use `summary.json`/`events.csv`: o analisador exclui explicitamente as amostras com `phase=readiness`.

Média e percentis p50/p95/p99 são calculados por execução. Os percentis usam **nearest rank** (índice `ceil(n × p)`, iniciado em 1); não se mistura a amostra das duas variantes. Com aproximadamente vinte eventos, os percentis superiores são instáveis e podem coincidir com o máximo. Não os use como evidência de superioridade arquitetural.

Fontes para os instrumentos: [saída JSON do k6](https://grafana.com/docs/k6/latest/results-output/real-time/json/), [tags de métricas](https://grafana.com/docs/k6/latest/using-k6/tags-and-groups/), [identificador de iteração](https://grafana.com/docs/k6/latest/javascript-api/k6-execution/) e [métricas personalizadas](https://grafana.com/docs/k6/latest/javascript-api/k6-metrics/).

## Critérios deste piloto

`instrument_valid=true` significa que, para os eventos observados:

1. há evidência de envio, retorno e duração HTTP, sem marcador repetido;
2. todas as respostas têm o status esperado (`201` ou `202`) e o identificador correto;
3. cada evento tem um único marco `commit_completed` com `status=persisted` e um registro correspondente;
4. os campos, o payload e o hash persistidos coincidem com o conteúdo sintético esperado;
5. não há envio à DLQ, intervalo negativo ou iteração descartada pelo gerador.

Um `false` ou código de saída não zero exige investigação. **Ausência após cinco segundos não prova perda**, e múltiplos marcos de commit não provam múltiplas linhas: podem indicar reentrega idempotente. O critério aqui é deliberadamente estrito para uma execução normal com UUIDs novos. Não é o critério definitivo para cenários com falhas, retransmissão ou recuperação. A PK já impede duas linhas com o mesmo `event_id`; este piloto não é um teste de reenvio idempotente nem de equivalência usando exatamente o mesmo conjunto nas duas versões.

## Limitações e o que ainda falta

- Os intervalos entre processos usam relógios de parede. Intervalos negativos são detectados, mas desvios positivos podem passar despercebidos. A sincronização/estabilidade temporal precisa ser verificada antes da campanha final.
- Tags por evento aumentam a cardinalidade; exportação JSON, logs e `docker stats` acrescentam custo. O coletor de recursos amostra aproximadamente a cada três segundos, dependendo do tempo do comando, e não mede o gerador ou o overhead global do Docker/Windows. CPU/memória permanecem **dados brutos**, sem agregação ou interpretação de custo nesta etapa.
- O gerador roda na mesma máquina do sistema. A campanha final precisa registrar a configuração do computador, aquecimento, estado de fundo, contenção e limitações de generalização.
- Faltam a comparação documentada entre JMeter e k6, a calibração da carga de referência, os critérios e parâmetros congelados, repetições, regras de descarte, experimento do mesmo modelo nas duas versões, testes de idempotência, falhas e recuperação, e cálculo de throughput/erros/recuperação conforme o protocolo final.
- **Não alterar capítulos de resultados/conclusão nem entregas históricas com estes números.**

O k6 é fixado em `2.3.0` com digest da imagem; o manifesto registra o ID efetivo do analisador e das aplicações. Para testar somente o analisador no PowerShell: `./mvnw.cmd -f experimento/analyzer/pom.xml verify`. O Dockerfile executa os mesmos testes no JDK 21 antes de empacotar a ferramenta.
