#!/usr/bin/env bash
# Local, interactive presentation. Never starts the definitive campaign or deletes data.
set -uo pipefail
TCC_DEMO_APP=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
TCC_DEMO_PROJECT=tcc-java-2026
TCC_DEMO_K6='grafana/k6:2.3.0@sha256:9c2dee7f8ed74d317e4027c06a10f169b625638189de8d4555d0b3486a5aeb34'
TCC_DEMO_RATE=${TCC_DEMO_RATE:-5}
TCC_DEMO_SECONDS=${TCC_DEMO_SECONDS:-20}
TCC_DEMO_SESSION=''
TCC_DEMO_OUTPUT=''
TCC_DEMO_LAST_ID=''
TCC_DEMO_LAST_VARIANT=''
TCC_DEMO_CONSUMER_PAUSED=0
TCC_DEMO_LOAD=''
TCC_DEMO_HTTP_CODE=''
TCC_DEMO_SYNC=''
TCC_DEMO_ASYNC=''

dc() { docker compose --project-directory "$TCC_DEMO_APP" -f "$TCC_DEMO_APP/docker-compose.yml" -p "$TCC_DEMO_PROJECT" "$@"; }
json_helper() { python3 "$TCC_DEMO_APP/demo/json_helper.py" "$@"; }
demo_uuid() { local id; IFS= read -r id < /proc/sys/kernel/random/uuid; printf '%s\n' "$id"; }
demo_error() { printf '\nATENÇÃO: %s\n' "$*" >&2; }

validate_settings() {
  [[ $TCC_DEMO_RATE =~ ^[1-9][0-9]?$ && $TCC_DEMO_SECONDS =~ ^[1-9][0-9]?$ ]] &&
    ((TCC_DEMO_RATE<=10 && TCC_DEMO_SECONDS<=30)) || {
      demo_error 'Limites: TCC_DEMO_RATE=1..10 e TCC_DEMO_SECONDS=1..30.'; return 1;
    }
}

dependencies() {
  local command
  for command in docker curl python3; do
    command -v "$command" >/dev/null || { demo_error "Falta $command. Prepare o WSL antes da apresentação."; return 1; }
  done
  [[ -r /proc/sys/kernel/random/uuid ]] || { demo_error 'Execute com Bash no WSL/Linux, não no PowerShell/Git Bash.'; return 1; }
  docker compose version >/dev/null 2>&1 || { demo_error 'Docker Compose indisponível.'; return 1; }
  docker info >/dev/null 2>&1 || { demo_error 'Docker não está em execução ou não está acessível.'; return 1; }
}

no_experiment() {
  local ids
  ids=$(docker ps -q --filter label=com.docker.compose.project=tcc-entrega04) || return 1
  [[ -z $ids ]] || { demo_error 'Há um ensaio/campanha no projeto tcc-entrega04. Não vou interferir. Aguarde seu encerramento.'; return 1; }
}

owned_service() {
  local service=$1 id project label
  id=$(dc ps --all --quiet "$service") || return 1
  [[ $id =~ ^[0-9a-f]{12,64}$ ]] || { demo_error "Contêiner único de $service não encontrado. Use a opção 1."; return 1; }
  project=$(docker inspect -f '{{index .Config.Labels "com.docker.compose.project"}}' "$id") || return 1
  label=$(docker inspect -f '{{index .Config.Labels "com.docker.compose.service"}}' "$id") || return 1
  [[ $project == "$TCC_DEMO_PROJECT" && $label == "$service" ]] || { demo_error 'Identidade do contêiner não corresponde ao projeto autorizado.'; return 1; }
  printf '%s\n' "$id"
}

running_service() {
  local id
  id=$(owned_service "$1") || return 1
  [[ $(docker inspect -f '{{.State.Running}}' "$id") == true ]] || { demo_error "Serviço $1 está parado."; return 1; }
}

refresh_addresses() {
  local mapping
  mapping=$(dc port sync-api 8080) || return 1
  TCC_DEMO_SYNC=$(json_helper address "$mapping") || return 1
  mapping=$(dc port async-api 8081) || return 1
  TCC_DEMO_ASYNC=$(json_helper address "$mapping") || return 1
}

session() {
  [[ -n $TCC_DEMO_OUTPUT ]] && return 0
  TCC_DEMO_SESSION=$(demo_uuid) || return 1
  TCC_DEMO_OUTPUT="$TCC_DEMO_APP/.runtime/demonstracao/$TCC_DEMO_SESSION"
  mkdir -p "$TCC_DEMO_APP/.runtime/demonstracao" || return 1
  mkdir "$TCC_DEMO_OUTPUT" || return 1
  printf 'kind=presentation_demo_not_definitive\nsession_id=%s\nstarted_utc=%s\nproject=%s\n' \
    "$TCC_DEMO_SESSION" "$(date -u +%FT%TZ)" "$TCC_DEMO_PROJECT" > "$TCC_DEMO_OUTPUT/manifest.txt"
  printf 'utc\taction\tevent_id\thttp_code\tfile\n' > "$TCC_DEMO_OUTPUT/actions.tsv"
}

http_call() {
  local method=$1 url=$2 output=$3 payload=${4:-} timeout=${5:-15} result
  local args=(--silent --show-error --connect-timeout 3 --max-time "$timeout" --output "$output" --write-out '%{http_code}' -X "$method")
  [[ -z $TCC_DEMO_SESSION ]] || args+=(-H "X-Run-ID: $TCC_DEMO_SESSION")
  [[ $method != POST ]] || args+=(-H 'Content-Type: application/json' --data-binary "@$payload")
  TCC_DEMO_HTTP_CODE=$(curl "${args[@]}" "$url"); result=$?
  if ((result!=0));then
    demo_error "Sem confirmação HTTP (curl=$result). Não conclua perda nem reenvie cegamente; consulte o UUID."; return 1
  fi
}

record_action() {
  printf '%s\t%s\t%s\t%s\t%s\n' "$(date -u +%FT%TZ)" "$1" "$TCC_DEMO_LAST_ID" "$TCC_DEMO_HTTP_CODE" "$2" >> "$TCC_DEMO_OUTPUT/actions.tsv"
}

ensure_k6() {
  if ! docker image inspect "$TCC_DEMO_K6" >/dev/null 2>&1;then
    [[ ${1:-0} == 1 ]] || { demo_error 'Imagem k6 ausente. Use a opção 1 com internet antes da banca.';return 1; }
    printf 'Baixando a imagem fixada do k6. Faça esta preparação antes da banca.\n'
    docker pull "$TCC_DEMO_K6" || return 1
  fi
}

prepare() {
  no_experiment || return 1
  docker image inspect tcc-java-2026-sync-api:latest tcc-java-2026-async-api:latest tcc-java-2026-consumer:latest >/dev/null 2>&1 || {
    demo_error 'Faltam imagens Java. Siga o README para preparar o ambiente antes da banca. Este menu não recompila imagens.';return 1;
  }
  dc up -d --no-build || return 1
  refresh_addresses || return 1
  local deadline=$((SECONDS+90)) ready=0
  printf 'Aguardando as duas APIs ficarem prontas...\n'
  while ((SECONDS<deadline));do
    if curl -fsS --max-time 3 "$TCC_DEMO_SYNC/health" >/dev/null 2>&1 && curl -fsS --max-time 3 "$TCC_DEMO_ASYNC/health" >/dev/null 2>&1;then ready=1;break;fi
    sleep 1
  done
  ((ready==1)) || { demo_error 'As APIs não ficaram prontas; consulte os logs na opção 11.';return 1; }
  running_service consumer || return 1
  TCC_DEMO_CONSUMER_PAUSED=0
  ensure_k6 1 || return 1
  printf 'Serviços prontos. Swagger: %s/swagger-ui/index.html\n' "$TCC_DEMO_SYNC"
}

show_services() {
  dc ps --all || return 1
  printf '\nSÍNCRONA: cliente -> sync-api -> PostgreSQL -> HTTP 201\n'
  printf 'ASSÍNCRONA: cliente -> async-api -> Kafka -> HTTP 202; consumer -> PostgreSQL\n'
  printf 'audit-core e audit-storage são bibliotecas, não serviços para iniciar.\n'
  if refresh_addresses;then
    printf '\nSwagger: %s/swagger-ui/index.html\n' "$TCC_DEMO_SYNC"
    printf 'API síncrona: %s | API assíncrona: %s\n' "$TCC_DEMO_SYNC" "$TCC_DEMO_ASYNC"
  fi
}

send_event() {
  local variant=$1 base expected payload response
  no_experiment && refresh_addresses && session || return 1
  if [[ $variant == sync ]];then base=$TCC_DEMO_SYNC;expected=201;running_service sync-api || return 1
  else base=$TCC_DEMO_ASYNC;expected=202;running_service async-api || return 1;fi
  TCC_DEMO_LAST_ID=$(demo_uuid) || return 1
  TCC_DEMO_LAST_VARIANT=$variant
  payload="$TCC_DEMO_OUTPUT/evento-$TCC_DEMO_LAST_ID.json"
  response="$TCC_DEMO_OUTPUT/resposta-$TCC_DEMO_LAST_ID.json"
  json_helper payload "$TCC_DEMO_LAST_ID" "$TCC_DEMO_SESSION" "$variant" > "$payload" || return 1
  printf '\nPOST %s/audit\nJSON enviado:\n' "$base"
  json_helper pretty "$payload" || return 1
  if ! http_call POST "$base/audit" "$response" "$payload";then
    record_action POST_UNCONFIRMED "$response";return 1
  fi
  record_action "POST_$variant" "$response"
  printf '\nResposta HTTP %s:\n' "$TCC_DEMO_HTTP_CODE"
  json_helper pretty "$response" || { demo_error 'Resposta não é JSON válido.';return 1; }
  [[ $TCC_DEMO_HTTP_CODE == "$expected" ]] || { demo_error "Era esperado HTTP $expected. Preserve o arquivo e investigue.";return 1; }
  json_helper response "$response" "$TCC_DEMO_LAST_ID" "$expected" || return 1
  printf '\nUUID guardado automaticamente: %s\n' "$TCC_DEMO_LAST_ID"
  if [[ $variant == sync ]];then printf 'FALA: recebi 201 depois da transação. Posso consultar esse registro no banco.\n'
  else printf 'FALA: recebi 202 porque o Kafka confirmou a publicação. Isso ainda não comprova gravação no banco.\n';fi
}

query_last() {
  local quiet=${1:-0} output
  [[ -n $TCC_DEMO_LAST_ID ]] || { demo_error 'Envie um evento pelas opções 3 ou 4 primeiro.';return 1; }
  refresh_addresses && session || return 1
  output="$TCC_DEMO_OUTPUT/consulta-$(demo_uuid).json"
  http_call GET "$TCC_DEMO_SYNC/audit/$TCC_DEMO_LAST_ID" "$output" '' 3 || return 1
  record_action GET "$output"
  if [[ $quiet == 0 ]];then
    printf '\nGET %s/audit/%s -> HTTP %s\n' "$TCC_DEMO_SYNC" "$TCC_DEMO_LAST_ID" "$TCC_DEMO_HTTP_CODE"
    json_helper pretty "$output" || return 1
  fi
  case $TCC_DEMO_HTTP_CODE in
    200) json_helper response "$output" "$TCC_DEMO_LAST_ID" 200 || return 1
      [[ $quiet == 1 ]] || printf 'FALA: este UUID está persistido no PostgreSQL.\n';;
    404) [[ $quiet == 1 ]] || printf 'FALA: este UUID ainda não está no banco. 404 sozinho não prova perda.\n';;
    *) demo_error "Consulta indisponível ou inválida (HTTP $TCC_DEMO_HTTP_CODE).";return 1;;
  esac
}

pause_consumer() {
  no_experiment || return 1
  local id
  id=$(owned_service consumer) || return 1
  if [[ $(docker inspect -f '{{.State.Running}}' "$id") != true ]];then
    printf 'O consumidor já estava parado; não alterei seu estado.\n';return 0
  fi
  # Set before stopping so an interrupt during the operation also restores it.
  TCC_DEMO_CONSUMER_PAUSED=1
  dc stop consumer || return 1
  [[ $(docker inspect -f '{{.State.Running}}' "$id") == false ]] || return 1
  printf '\nFALA: parei só o consumidor. Kafka e APIs continuam ativos.\n'
  printf 'Agora use 4 para enviar um NOVO evento, 5 para observar 404 e 8 para ver o lag.\n'
}

wait_last() {
  local deadline=$((SECONDS+60))
  printf 'Aguardando este UUID aparecer no PostgreSQL (até 60 s)...\n'
  while ((SECONDS<deadline));do
    if query_last 1 && [[ $TCC_DEMO_HTTP_CODE == 200 ]];then
      printf 'Registro localizado. Use a opção 5 para mostrar o conteúdo.\n';return 0
    fi
    sleep 1
  done
  demo_error 'O registro não foi confirmado no prazo. Não declare perda: examine logs, lag e DLQ.';return 1
}

resume_consumer() {
  local id
  no_experiment || return 1
  id=$(owned_service consumer) || return 1
  # Start this verified container only, without rerunning Compose init dependencies.
  docker start "$id" || return 1
  running_service consumer || return 1
  TCC_DEMO_CONSUMER_PAUSED=0
  printf '\nFALA: retomei o consumidor; ele pode processar o que ficou aguardando no Kafka.\n'
  [[ -z $TCC_DEMO_LAST_ID || $TCC_DEMO_LAST_VARIANT != async ]] || wait_last || return 1
}

show_lag() {
  running_service kafka || return 1
  printf '\nGrupo audit-persistence-java, tópico audit-events. LAG = fim do tópico menos offset confirmado.\n'
  printf 'Grupo sem membros ativos é esperado quando o consumidor está parado. Lag zero sozinho não prova persistência.\n'
  dc exec -T kafka /opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server kafka:9092 --describe --group audit-persistence-java
}

run_k6() {
  local variant=$1 seconds=${2:-$TCC_DEMO_SECONDS} rate=${3:-$TCC_DEMO_RATE} target network id run folder code
  local pipeline_status=()
  no_experiment && refresh_addresses && ensure_k6 && session || return 1
  [[ $variant == sync || $variant == async ]] || return 1
  [[ $seconds =~ ^[1-9][0-9]?$ && $rate =~ ^[1-9][0-9]?$ ]] && ((seconds<=30 && rate<=10)) || return 1
  id=$(owned_service "$variant-api") || return 1
  running_service "$variant-api" || return 1
  network=$(docker inspect -f '{{range $name, $value := .NetworkSettings.Networks}}{{$name}}{{"\n"}}{{end}}' "$id") || return 1
  [[ -n $network && $network != *$'\n'* ]] || { demo_error 'Esperada uma única rede Compose.';return 1; }
  [[ $(docker network inspect -f '{{index .Labels "com.docker.compose.project"}}' "$network") == "$TCC_DEMO_PROJECT" ]] || return 1
  if [[ $variant == sync ]];then target=http://sync-api:8080/audit;else target=http://async-api:8081/audit;fi
  run=$(demo_uuid) || return 1
  folder="$TCC_DEMO_OUTPUT/k6-$run-$variant"
  mkdir "$folder" || return 1
  TCC_DEMO_LOAD="tcc-demo-load-$run"
  printf '\nFALA: k6 enviará %s eventos/s por %s s. Oito VUs disponíveis sustentam a taxa, não são concorrência fixa.\n' "$rate" "$seconds"
  printf 'Esta demonstração mede HTTP; não mede latência até commit nem substitui a campanha.\n'
  docker run --rm --name "$TCC_DEMO_LOAD" --label "tcc.demo.session=$TCC_DEMO_SESSION" \
    --network "$network" --cpus 2 --memory 2g --user "$(id -u):$(id -g)" \
    --mount "type=bind,src=$TCC_DEMO_APP/demo,dst=/scripts,readonly" \
    --mount "type=bind,src=$folder,dst=/output" \
    -e "RUN_ID=$run" -e "VARIANT=$variant" -e "TARGET_URL=$target" \
    -e "DEMO_RATE=$rate" -e "DEMO_SECONDS=$seconds" \
    "$TCC_DEMO_K6" run --out json=/output/amostras.jsonl.gz /scripts/load.js 2>&1 | tee "$folder/console.txt"
  pipeline_status=("${PIPESTATUS[@]}")
  code=${pipeline_status[0]}
  TCC_DEMO_LOAD=''
  printf 'k6_exit=%s\nrun_id=%s\nvariant=%s\nrate=%s\nseconds=%s\n' "$code" "$run" "$variant" "$rate" "$seconds" > "$folder/manifest.txt"
  printf 'Arquivos: %s\n' "$folder"
  ((${pipeline_status[1]:-1}==0)) || { demo_error 'Falha ao preservar o console do k6.';return 1; }
  ((code==0)) || { demo_error "k6 terminou com código $code; não apresente a execução como aprovada.";return 1; }
  json_helper k6 "$folder/resumo.json" || return 1
}

show_resources() {
  local service id ids=()
  for service in sync-api async-api consumer postgres kafka;do
    id=$(owned_service "$service") || return 1
    ids+=("$id")
  done
  printf '\nAmostra instantânea Docker; não é consumo global nem resultado estatístico.\n'
  docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}' "${ids[@]}"
  printf '\nMarcos recentes (request_received, broker_acknowledged, commit_completed):\n'
  dc logs --no-color --tail=8 sync-api async-api consumer
}

talktrack() {
  printf '\nROTEIRO SUGERIDO (ensaie antes da banca)\n'
  printf '1. Opção 1: preparar antes da apresentação; opção 2: mostrar os cinco serviços e o Swagger.\n'
  printf '2. Opção 3 e depois 5: síncrona devolve 201 após gravar.\n'
  printf '3. Opção 4, depois 7 e 5: 202 confirma Kafka; consumidor grava posteriormente.\n'
  printf '4. Opção 6, depois 4, 5 e 8: Kafka aceita, mas o novo UUID ainda não está no banco.\n'
  printf '5. Opção 7, depois 5 e 8: retomar, verificar o UUID e observar o lag.\n'
  printf '6. Opções 9 e 10: executar cargas curtas; explicar média/p95 HTTP e erros.\n'
  printf '7. Opção 11: mostrar uma amostra de recursos e marcos. Não inferir eficiência de contêiner parado.\n'
  printf '8. Opção 13: comparar com persistência/recursos medidos em projeto isolado; execute antes da banca.\n'
  printf '9. Opção 14: mostrar a última tabela pronta sem executar carga; abrir o HTML no navegador.\n'
  printf '10. Opção 0: sair. Se este menu pausou o consumidor, tentará retomá-lo.\n'
  printf 'Leia: %s/demo/README.md\n' "$TCC_DEMO_APP"
  printf 'Explicação de cada métrica, exemplos e falas: %s/demo/METRICAS-E-FALAS.md\n' "$TCC_DEMO_APP"
}

compare_menu() {
  local choice scenario
  no_experiment || return 1
  printf '\nComparação isolada (não são as 130 execuções):\n'
  printf '1 Carga normal — duas execuções curtas (preparação/coleta acrescentam minutos)\n'
  printf '2 PostgreSQL interrompido por 5 s — 90 s medidos por versão\n'
  printf '3 Consumidor interrompido por 5 s — somente assíncrona, 90 s medidos\n'
  printf '0 Voltar. Execute antes da banca e use 14 para reapresentar sem carga.\n'
  IFS= read -r -p 'Cenário: ' choice || return 1
  case $choice in 0) return 0;;1) scenario=normal;;2) scenario=postgres-stop;;3) scenario=consumer-stop;;*) demo_error 'Cenário inválido.';return 1;;esac
  bash "$TCC_DEMO_APP/demo/comparar.sh" "$scenario"
}

check_ready() {
  local service
  no_experiment || return 1
  for service in sync-api async-api consumer postgres kafka;do running_service "$service" || return 1;done
  refresh_addresses && ensure_k6 || return 1
  curl -fsS --max-time 3 "$TCC_DEMO_SYNC/health" >/dev/null && curl -fsS --max-time 3 "$TCC_DEMO_ASYNC/health" >/dev/null || return 1
  printf 'Pré-verificação aprovada: serviços e k6 disponíveis. Nenhum evento foi enviado.\n'
}

cleanup() {
  local label id
  if [[ -n $TCC_DEMO_LOAD ]];then
    label=$(docker inspect -f '{{index .Config.Labels "tcc.demo.session"}}' "$TCC_DEMO_LOAD" 2>/dev/null || true)
    if [[ -n $TCC_DEMO_SESSION && $label == "$TCC_DEMO_SESSION" ]];then docker stop -t 3 "$TCC_DEMO_LOAD" >/dev/null 2>&1 || true;fi
  fi
  if ((TCC_DEMO_CONSUMER_PAUSED));then
    printf '\nRetomando o consumidor que este menu pausou...\n'
    if id=$(owned_service consumer) && docker start "$id";then TCC_DEMO_CONSUMER_PAUSED=0
    else demo_error 'Retomada não confirmada. Execute: docker compose -p tcc-java-2026 start consumer';fi
  fi
  [[ -z $TCC_DEMO_OUTPUT ]] || printf '\nSessão preservada em %s\n' "$TCC_DEMO_OUTPUT"
}

smoke() {
  printf 'VALIDAÇÃO CURTA: grava dados sintéticos e pausa apenas o consumidor, que será retomado.\n'
  prepare && session && send_event sync && query_last && [[ $TCC_DEMO_HTTP_CODE == 200 ]] || return 1
  send_event async && wait_last && pause_consumer && send_event async && query_last || return 1
  [[ $TCC_DEMO_HTTP_CODE == 404 ]] || { demo_error 'Esperado 404 para o UUID enviado com consumidor parado.';return 1; }
  show_lag && resume_consumer && query_last && [[ $TCC_DEMO_HTTP_CODE == 200 ]] || return 1
  run_k6 sync 3 2 && run_k6 async 3 2 || return 1
  printf '\nVALIDAÇÃO APROVADA: 201/200; 202/404 com consumidor parado; 200 após retomada; k6 nas duas APIs.\n'
}

usage() {
  printf 'Uso no WSL/Linux: bash demo/apresentacao.sh [--check|--smoke|--help]\n'
  printf 'Sem argumento: menu interativo. --check: somente leitura. --smoke: validação curta com escrita/pausa.\n'
  printf 'Não executa campaign.sh nem recompila imagens. Comparação 13 reinicia somente a tabela experimental isolada.\n'
}

main() {
  local choice mode=${1:-menu}
  if [[ $mode == --help ]];then usage;return 0;fi
  [[ $mode == menu || $mode == --check || $mode == --smoke ]] || { usage;return 1; }
  validate_settings && dependencies && no_experiment || return 1
  if [[ $mode == --check ]];then check_ready;return $?;fi
  if [[ $mode == menu && ! -t 0 ]];then demo_error 'O menu precisa de terminal interativo. Use --check ou --smoke para validação.';return 1;fi
  trap cleanup EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM
  if [[ $mode == --smoke ]];then smoke;return $?;fi
  session || return 1
  while true;do
    printf '\n=== TCC: DEMONSTRAÇÃO LOCAL (não executa a campanha) ===\n'
    [[ -z $TCC_DEMO_LAST_ID ]] || printf 'Último evento: %s (%s)\n' "$TCC_DEMO_LAST_ID" "$TCC_DEMO_LAST_VARIANT"
    printf ' 1 Preparar/iniciar serviços e baixar k6 se necessário\n 2 Mostrar serviços, fluxos e endereço do Swagger\n'
    printf ' 3 Enviar evento síncrono (201)\n 4 Enviar evento assíncrono (202)\n 5 Consultar último evento no PostgreSQL\n'
    printf ' 6 Pausar consumidor\n 7 Retomar consumidor e aguardar último evento assíncrono\n 8 Ver offsets/lag no Kafka\n'
    printf ' 9 k6 síncrono (%s/s por %s s)\n10 k6 assíncrono (%s/s por %s s)\n' "$TCC_DEMO_RATE" "$TCC_DEMO_SECONDS" "$TCC_DEMO_RATE" "$TCC_DEMO_SECONDS"
    printf '11 Ver recursos e logs recentes\n12 Mostrar roteiro e falas\n13 Comparar síncrono × assíncrono lado a lado\n14 Mostrar última comparação pronta (sem carga)\n 0 Sair\n'
    IFS= read -r -p 'Escolha: ' choice || return 0
    case $choice in
      0) return 0;;
      1) prepare || demo_error 'Preparação incompleta; confira as mensagens acima.';;
      2) show_services || demo_error 'Não foi possível consultar todos os serviços.';;
      3) send_event sync || demo_error 'Envio não confirmado; UUID e arquivos foram preservados quando disponíveis.';;
      4) send_event async || demo_error 'Envio não confirmado; UUID e arquivos foram preservados quando disponíveis.';;
      5) query_last || demo_error 'Consulta não confirmada.';;
      6) pause_consumer || demo_error 'Pausa não confirmada.';;
      7) resume_consumer || demo_error 'Retomada/persistência não confirmada; consulte os logs.';;
      8) show_lag || demo_error 'Lag não disponível. Verifique a preparação e a existência do grupo.';;
      9) run_k6 sync || demo_error 'Demonstração k6 não aprovada.';;
      10) run_k6 async || demo_error 'Demonstração k6 não aprovada.';;
      11) show_resources || demo_error 'Recursos/logs não disponíveis.';;
      12) talktrack;;
      13) compare_menu || demo_error 'Comparação não concluída; evidências preservadas. Veja o log indicado.';;
      14) python3 "$TCC_DEMO_APP/demo/comparison_report.py" --latest || demo_error 'Nenhuma comparação completa disponível. Execute a opção 13 primeiro.';;
      *) printf 'Opção inválida.\n';;
    esac
    IFS= read -r -p 'Pressione Enter para voltar ao menu...' choice || return 0
  done
}

if [[ ${BASH_SOURCE[0]} == "$0" ]];then main "$@";fi
