# Instrumentos para a Entrega 04

Leia primeiro o [protocolo](PROTOCOLO-ENTREGA04.md) e a [calibração de 26/10/2026](calibracao/2026-10-26-529e0349/README.md). Instrumentação validada, referência comum de **48 eventos/s** e plano congelado. As 130 execuções definitivas ainda não começaram; o texto e a apresentação históricos continuam sendo de preparação.

## Antes de executar

Use WSL/Linux com Docker Compose >= 2.24.4 (o override usa `!reset`). Mantenha a sessão do WSL aberta durante os testes. Os testes iniciam outro projeto, `tcc-entrega04`, sem portas públicas e com volumes próprios. O banco interativo `tcc-java-2026` não é apagado. O executor reinicializa **somente** linhas sintéticas do banco experimental, após parar os processos que gravam; recusa banco com registros de outra origem. Não execute dois ensaios simultâneos: eles compartilham o mesmo projeto experimental.

Antes de medir, prefira uma janela sem outros trabalhos pesados. O executor registra os contêineres concorrentes, mas não os interrompe. Parâmetros e erros são preservados na pasta de cada execução. Não editar `run.sh` ou outro script enquanto ele estiver executando.

Para preparar **outro ambiente**, dentro de `implementacao-java`:

```bash
docker compose build sync-api async-api consumer
docker build -t tcc-pilot-analyzer:local experimento/analyzer
```

O Dockerfile do analisador executa os testes no JDK 21. Os executáveis do sistema continuam sendo os cinco módulos Maven anteriores; o analisador é uma ferramenta independente.

**Não reconstrua as imagens medidas antes de executar a campanha já congelada nesta máquina.** Os IDs efetivos são conferidos. Reconstrução ou mudança relevante de ambiente exige revisar e recalibrar o protocolo, preservando o relatório anterior.

## Validar os caminhos

```bash
bash experimento/validate.sh
```

O script executa sete ensaios curtos: modelo comum síncrono/assíncrono, PostgreSQL parado nas duas versões, rajada nas duas e consumidor parado na assíncrona. Não use essas sete execuções como se fossem dez repetições dos cenários definitivos. O perfil `model` envia exatamente 50 eventos, faz um reenvio igual e um conflitante. O comparador das duas exportações é executado com:

```bash
docker run --rm --network none \
  --mount "type=bind,src=$PWD/.runtime/entrega04,dst=/evidence" \
  tcc-pilot-analyzer:local model \
  /evidence/UUID_SYNC-sync/database.jsonl \
  /evidence/UUID_ASYNC-async/database.jsonl \
  /evidence/model-comparison.json
```

Substitua os dois UUIDs pelos ensaios pareados com o mesmo `dataset_id`. O comparador exige exatamente 50 linhas e igualdade de conteúdo/hash, excluindo apenas `persisted_at`.

## Calibração e campanha congelada

```bash
bash experimento/campaign.sh --check experimento/calibracao/2026-10-26-529e0349/plan.csv
```

Esse comando verifica hashes do plano/Compose sem gerar carga ou alterar serviços. Exige checkout limpo. Para iniciar de fato, reserve uma janela longa e pare somente o ambiente interativo deste TCC:

```bash
docker compose -p tcc-java-2026 stop
bash experimento/campaign.sh experimento/calibracao/2026-10-26-529e0349/plan.csv
```

Não pare projetos alheios. Não execute os dois modos ao mesmo tempo. O plano possui 10 blocos/130 execuções, com 60 s de aquecimento, 12 s entre fases, 300 s de medição e 90 s de drenagem. Somente aquecimento + medição somam 13 h. Níveis: 12/24/36/48 eventos/s; rajada 48→96→48; falhas a 12/s por 40 s. VUs: 128 nas cargas normais e 176 nas falhas.

O executor recusa mudanças de código instrumentador, imagens e parâmetros congelados antes de reinicializar o banco experimental. Falhas de coleta ou falta de folga do gerador/observador interrompem a campanha para investigação. Não reinicie cegamente o mesmo plano após falha: pastas existentes nunca são sobrescritas; preserve a tentativa e documente qualquer substituição.

Para **nova calibração**, não para executar o plano já aprovado: `bash experimento/calibrate.sh`. O script segue a política predeclarada em `calibration-policy.json`: recuperação, exploração 10/25/50/100, oito controles e duas confirmações de cinco minutos. `RATE`/`VUS` externos não escolhem a referência desse roteiro. Cada sessão recebe UUID próprio e pode levar mais de uma hora.

O finalizador usa Node.js sem pacotes externos e é separado do gerador/analisador Docker. Exemplo de inspeção, também disponível no PowerShell com Node:

```bash
node experimento/finalize-calibration.mjs . 529e0349-d5b4-4001-a862-a0755cd69b72
```

Sem `--finalize`, apenas examina a sessão local. Com essa opção, verifica checksums e cria relatório/plano/protocolo **somente se ainda não existirem**, nunca sobrescrevendo um protocolo anterior. Outra calibração exige uma revisão explícita do congelamento, não a edição retroativa dos números históricos. Node não é necessário para iniciar a campanha Bash/Docker já congelada.

Verificação adicional opcional: `node experimento/verify-frozen.mjs`. Confere hashes do código/arquivos publicados, os 130 UUIDs, o conteúdo compartilhado dos pares, dez repetições por condição e primeira variante balanceada em 5/5. Verifica também que as pastas planejadas ainda não existem localmente. A contagem de arquivos brutos conferidos é a registrada no congelamento, não uma nova verificação dos brutos ausentes em um clone do Git.

## Ensaio individual

```bash
KIND=validation PROFILE=steady RATE=5 WARMUP_SECONDS=5 \
MEASURE_SECONDS=18 DRAIN_SECONDS=5 VUS=32 \
bash experimento/run.sh sync

KIND=validation PROFILE=postgres-stop RATE=5 WARMUP_SECONDS=5 \
MEASURE_SECONDS=18 DRAIN_SECONDS=5 VUS=32 FAULT_SECONDS=5 \
bash experimento/run.sh async
```

Perfis: `steady`, `burst`, `postgres-stop`, `consumer-stop` (somente assíncrona) e `model`. O default sem sobrescrever parâmetros é **60 + 300 s**, mas a classificação continua `validation`, não `definitive`. A variável `KIND` não transforma um ensaio em evidência científica válida. A opção `definitive` exige protocolo congelado e checkout limpo, e ainda depende da conferência de parâmetros e dos critérios do protocolo.

## Evidências

Em `.runtime/entrega04/<run_id>-<variante>/`:

- `manifest.txt`: parâmetros, commit, imagens, limites, tempos e estado do checkout; sem exportar credenciais.
- `k6.jsonl.gz`, `k6-console.txt`: dados brutos e saída do cliente; fases separadas.
- `app.log`, `database.jsonl`, `retained.jsonl`, `dlq.jsonl`: confirmação, conteúdo e destinos. A exportação do Kafka usa atribuição direta à partição zero, evitando confundir atraso de rebalanceamento do exportador com tópico vazio.
- `resources.tsv`, `resources-errors.log`: amostras brutas por contêiner e falhas de coleta.
- `resource-batches.jsonl`: início/fim dos lotes Docker, aproximadamente a cada três segundos, inclusive gerador e observador.
- `observation.jsonl`, `observer-console.txt`: banco/relógio SQL e offsets/lag Kafka aproximadamente a cada segundo, com erros de consulta preservados.
- `timeline.csv`: grade de um segundo com aceites, aceites sem commit, lag e registros visíveis no banco; não é uma fila física equivalente entre arquiteturas.
- `kafka-lag-end.txt`: fotografia final do lag, **não série de backlog durante o ensaio**.
- `controller.log`: inicialização, parada/retomada e exportações; falhas de desenvolvimento permanecem rastreáveis.
- `events.csv`, `summary.json`, `analyzer-console.txt`: conciliação e métricas por execução.
- `SHA256SUMS`: verificação de alteração posterior. Execute `sha256sum -c SHA256SUMS` dentro da pasta.

`instrument_valid` trata consistência da coleta, não aprovação da hipótese. HTTP 503 durante falha pode ser um resultado válido. Uma mensagem na DLQ permanece retida, mas não foi salva no banco. Retenção no tópico não significa pendência quando o registro já foi salvo. Falta de confirmação deve permanecer não conciliada, nunca virar uma alegação automática de perda.

O analisador separa primeiro commit, persistência do backlog anterior e recuperação operacional sustentada, validada em três janelas consecutivas de dez segundos com entrada ativa. As margens do gerador/observador e os controles de telemetria foram verificados na calibração; não significam overhead zero. A agregação estatística entre repetições e os capítulos finais dependem da campanha. Os arquivos brutos ficam fora do Git; o relatório contém catálogo, resumos e hashes verificáveis.

## Encerrar o ambiente experimental

```bash
EXPERIMENT_TOPIC=unused docker compose -p tcc-entrega04 \
  -f docker-compose.yml -f experimento/compose.yml --profile observation stop
```

Isso para apenas o ambiente experimental e preserva os volumes. Não usar `down -v` no ambiente interativo. Para retomar a aplicação usual: `docker compose up -d`.
