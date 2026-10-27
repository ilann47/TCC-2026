#!/usr/bin/env bash
# A short presentation pair, using the existing isolated instrument unchanged.
set -euo pipefail
TCC_COMPARE_APP=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
TCC_COMPARE_PROJECT=tcc-entrega04
TCC_COMPARE_CLAIMED=0
TCC_COMPARE_CHILD=''
TCC_COMPARE_RUN=''

compare_dc() {
  EXPERIMENT_TOPIC=demo-unused docker compose --project-directory "$TCC_COMPARE_APP" \
    -p "$TCC_COMPARE_PROJECT" -f "$TCC_COMPARE_APP/docker-compose.yml" \
    -f "$TCC_COMPARE_APP/experimento/compose.yml" --profile observation "$@"
}

compare_guard() {
  local active
  active=$(docker ps -q --filter "label=com.docker.compose.project=$TCC_COMPARE_PROJECT") || return 1
  [[ -z $active ]] || { printf 'Há um experimento ativo. Comparação recusada, sem interrompê-lo.\n' >&2;return 1; }
}

compare_stop() {
  local active id service
  ((TCC_COMPARE_CLAIMED)) || return 0
  # Only the private project claimed after a read-only guard. Preserve volumes/evidence.
  compare_dc stop -t 5 >> "$TCC_COMPARE_OUTPUT/controle.log" 2>&1 || return 1
  if [[ -n $TCC_COMPARE_RUN ]];then
    id="tcc-e04-load-$TCC_COMPARE_RUN"
    if [[ $(docker inspect -f '{{.State.Running}}' "$id" 2>/dev/null || true) == true ]];then
      docker stop -t 3 "$id" >> "$TCC_COMPARE_OUTPUT/controle.log" 2>&1 || return 1
    fi
  fi
  active=$(docker ps -q --filter "label=com.docker.compose.project=$TCC_COMPARE_PROJECT") || return 1
  [[ -z $active ]] || { printf 'Não foi possível confirmar a parada do projeto experimental.\n' >&2;return 1; }
  TCC_COMPARE_CLAIMED=0
}

compare_cleanup() {
  local code=$?
  trap - EXIT INT TERM
  if [[ -n $TCC_COMPARE_CHILD ]];then
    kill -TERM -- "-$TCC_COMPARE_CHILD" 2>/dev/null || true
    wait "$TCC_COMPARE_CHILD" 2>/dev/null || true
    TCC_COMPARE_CHILD=''
  fi
  if ! compare_stop;then
    printf 'ATENÇÃO: confira docker compose -p tcc-entrega04 ps antes de sair.\n' >&2
    code=1
  fi
  exit "$code"
}

compare_main() {
  local scenario=${1:-normal} rate=${TCC_DEMO_RATE:-5} warm=5 measure=${TCC_DEMO_SECONDS:-20} drain=10 vus=32 fault=5
  local command profile=steady dataset variant variants=(sync async) sync='' async='' code output_parent
  if [[ $scenario == --help ]];then
    printf 'Uso: bash demo/comparar.sh [normal|postgres-stop|consumer-stop|--smoke]\n'
    printf 'Dados sintéticos em tcc-entrega04; duas execuções sequenciais; não inicia campaign.sh.\n'
    return 0
  fi
  case $scenario in
    normal) ;;
    postgres-stop) profile=postgres-stop;warm=10;measure=90;drain=20;vus=64;;
    consumer-stop) profile=consumer-stop;warm=10;measure=90;drain=20;vus=64;variants=(async);;
    --smoke) scenario=normal;rate=2;warm=2;measure=10;drain=5;vus=16;;
    *) printf 'Cenário inválido. Use --help.\n' >&2;return 1;;
  esac
  [[ $rate =~ ^[1-9][0-9]*$ && $measure =~ ^[1-9][0-9]*$ ]] && ((rate<=10 && measure>=6 && measure<=90)) || {
    printf 'Comparação exige taxa 1..10/s e duração normal 6..30 s.\n' >&2;return 1;
  }
  [[ $scenario != normal || $measure -le 30 ]] || return 1
  for command in docker python3 flock setsid timeout;do command -v "$command" >/dev/null || { printf 'Falta: %s\n' "$command" >&2;return 1; };done
  [[ -r /proc/sys/kernel/random/uuid ]] || return 1
  docker compose version >/dev/null && docker info >/dev/null || return 1
  for command in tcc-pilot-analyzer:local tcc-java-2026-sync-api:latest tcc-java-2026-async-api:latest tcc-java-2026-consumer:latest postgres:16-alpine apache/kafka:3.9.1 \
    'grafana/k6:2.3.0@sha256:9c2dee7f8ed74d317e4027c06a10f169b625638189de8d4555d0b3486a5aeb34';do
    docker image inspect "$command" >/dev/null || { printf 'Imagem ausente: %s. Prepare antes da banca; nenhum build automático.\n' "$command" >&2;return 1; }
  done
  mkdir -p "$TCC_COMPARE_APP/.runtime/demonstracao"
  exec 9> "$TCC_COMPARE_APP/.runtime/demonstracao/.comparacao.lock"
  flock -n 9 || { printf 'Outra comparação já está em execução.\n' >&2;return 1; }
  compare_guard || return 1
  dataset=$(</proc/sys/kernel/random/uuid)
  TCC_COMPARE_OUTPUT="$TCC_COMPARE_APP/.runtime/demonstracao/comparacao-$dataset"
  mkdir "$TCC_COMPARE_OUTPUT"
  trap compare_cleanup EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM
  TCC_COMPARE_CLAIMED=1
  printf '\nCOMPARAÇÃO DE DEMONSTRAÇÃO — não é a campanha definitiva\n'
  printf 'Cenário: %s | %s eventos/s | %s s medidos por versão | aquecimento %s s\n' "$scenario" "$rate" "$measure" "$warm"
  printf 'Execuções SEQUENCIAIS em banco/tópicos isolados. Swagger e dados do projeto principal não são alterados.\n'
  printf 'Preparação, coleta e exportação acrescentam minutos. Para a banca, execute antes e use a opção 14.\n'
  [[ $scenario != consumer-stop ]] || printf 'Consumidor não existe na síncrona: sua coluna será NÃO SE APLICA neste cenário.\n'
  for variant in "${variants[@]}";do
    TCC_COMPARE_RUN=$(</proc/sys/kernel/random/uuid)
    output_parent="$TCC_COMPARE_APP/.runtime/entrega04/$TCC_COMPARE_RUN-$variant"
    printf '\nExecutando %s... log: %s/%s-console.txt\n' "$variant" "$TCC_COMPARE_OUTPUT" "$variant"
    # A new process group lets Ctrl+C terminate the runner and its children before cleanup.
    KIND=validation PROFILE="$profile" RATE="$rate" WARMUP_SECONDS="$warm" MEASURE_SECONDS="$measure" DRAIN_SECONDS="$drain" \
      VUS="$vus" OBSERVE=1 STATS=1 TELEMETRY=full FAULT_SECONDS="$fault" RUN_ID="$TCC_COMPARE_RUN" DATASET_ID="$dataset" \
      setsid timeout --signal=TERM --kill-after=20s 480s bash "$TCC_COMPARE_APP/experimento/run.sh" "$variant" \
      > "$TCC_COMPARE_OUTPUT/$variant-console.txt" 2>&1 &
    TCC_COMPARE_CHILD=$!
    code=0
    wait "$TCC_COMPARE_CHILD" || code=$?
    TCC_COMPARE_CHILD=''
    if ((code!=0));then
      printf 'Coleta %s falhou (código %s). Evidências preservadas; nenhum resultado será anunciado como válido.\n' "$variant" "$code" >&2
      tail -n 14 "$TCC_COMPARE_OUTPUT/$variant-console.txt" >&2
      return 1
    fi
    if [[ $variant == sync ]];then sync=$output_parent;else async=$output_parent;fi
    printf 'Coleta %s concluída.\n' "$variant"
  done
  compare_stop || return 1
  python3 "$TCC_COMPARE_APP/demo/comparison_report.py" --output "$TCC_COMPARE_OUTPUT" --scenario "$scenario" --sync "$sync" --async "$async" || return 1
  printf '\nRelatório no navegador: %s/relatorio.html\n' "$TCC_COMPARE_OUTPUT"
  if command -v wslpath >/dev/null;then wslpath -w "$TCC_COMPARE_OUTPUT/relatorio.html";fi
  printf 'Use a opção 14 para reapresentar esta comparação sem gerar carga.\n'
}

if [[ ${BASH_SOURCE[0]} == "$0" ]];then compare_main "$@";fi
