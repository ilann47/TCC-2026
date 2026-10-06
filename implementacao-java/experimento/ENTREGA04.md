# Instrumentos para a Entrega 04

Leia primeiro o [protocolo e as pendências científicas](PROTOCOLO-ENTREGA04.md). O texto e a apresentação atuais são de preparação, não de fechamento da pesquisa.

## Antes de executar

Use WSL/Linux com Docker Compose >= 2.24.4 (o override usa `!reset`). Mantenha a sessão do WSL aberta durante os testes. Os testes iniciam outro projeto, `tcc-entrega04`, sem portas públicas e com volumes próprios. O banco interativo `tcc-java-2026` não é apagado. O executor reinicializa **somente** linhas sintéticas do banco experimental, após parar os processos que gravam; recusa banco com registros de outra origem. Não execute dois ensaios simultâneos: eles compartilham o mesmo projeto experimental.

Antes de medir, prefira uma janela sem outros trabalhos pesados. O executor registra os contêineres concorrentes, mas não os interrompe. Parâmetros e erros são preservados na pasta de cada execução. Não editar `run.sh` ou outro script enquanto ele estiver executando.

Dentro de `implementacao-java`:

```bash
docker compose build sync-api async-api consumer
docker build -t tcc-pilot-analyzer:local experimento/analyzer
```

O Dockerfile do analisador executa os testes no JDK 21. Os executáveis do sistema continuam sendo os cinco módulos Maven anteriores; o analisador é uma ferramenta independente.

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

## Validar uma taxa candidata

```bash
RATE=50 VUS=256 bash experimento/calibrate.sh
```

A taxa 50 é uma **candidata a testar**, não uma capacidade já demonstrada. O script usa 60 s de aquecimento, 300 s de medição e 30 s de observação posterior por variante. Uma candidata só pode ser adotada depois de examinar as janelas de 10 s, drops, erros, pendências e recursos. Não busca automaticamente a capacidade máxima.

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
- `kafka-lag-end.txt`: fotografia final do lag, **não série de backlog durante o ensaio**.
- `controller.log`: inicialização, parada/retomada e exportações; falhas de desenvolvimento permanecem rastreáveis.
- `events.csv`, `summary.json`, `analyzer-console.txt`: conciliação e métricas por execução.
- `SHA256SUMS`: verificação de alteração posterior. Execute `sha256sum -c SHA256SUMS` dentro da pasta.

`instrument_valid` trata consistência da coleta, não aprovação da hipótese. HTTP 503 durante falha pode ser um resultado válido. Uma mensagem na DLQ permanece retida, mas não foi salva no banco. Retenção no tópico não significa pendência quando o registro já foi salvo. Falta de confirmação deve permanecer não conciliada, nunca virar uma alegação automática de perda.

O analisador mede primeiro commit e drenagem do backlog após a retomada. A recuperação estável de throughput, a medição de overhead do gerador e a agregação estatística entre repetições ainda precisam de validação antes da campanha definitiva. Os arquivos brutos ficam fora do Git; o pacote contém um catálogo e resumos verificáveis.

## Encerrar o ambiente experimental

```bash
EXPERIMENT_TOPIC=unused docker compose -p tcc-entrega04 \
  -f docker-compose.yml -f experimento/compose.yml stop
```

Isso para apenas o ambiente experimental e preserva os volumes. Não usar `down -v` no ambiente interativo. Para retomar a aplicação usual: `docker compose up -d`.
