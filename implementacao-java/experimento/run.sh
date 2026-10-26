#!/usr/bin/env bash
# Isolated experimental run. No writes/deletes in the interactive tcc-java-2026 DB.
set -euo pipefail
cd "$(dirname "$0")/.."
root=$(pwd)
variant=${1:-}
profile=${PROFILE:-steady}
kind=${KIND:-validation}
rate=${RATE:-5}
warm=${WARMUP_SECONDS:-60}
measure=${MEASURE_SECONDS:-300}
drain=${DRAIN_SECONDS:-30}
vus=${VUS:-64}
observe=${OBSERVE:-1}
stats=${STATS:-1}
telemetry=${TELEMETRY:-full}
run=${RUN_ID:-$(</proc/sys/kernel/random/uuid)}
dataset=${DATASET_ID:-$(</proc/sys/kernel/random/uuid)}
project=tcc-entrega04
k6='grafana/k6:2.3.0@sha256:9c2dee7f8ed74d317e4027c06a10f169b625638189de8d4555d0b3486a5aeb34'
analyzer=tcc-pilot-analyzer:local
[[ $variant == sync || $variant == async ]] || { echo 'Usage: bash experimento/run.sh sync|async' >&2; exit 1; }
[[ $profile == steady || $profile == burst || $profile == postgres-stop || $profile == consumer-stop || $profile == model ]] || exit 1
[[ $variant == async || $profile != consumer-stop ]] || { echo 'Consumer-only fault applies to async.' >&2; exit 1; }
for value in "$run" "$dataset"; do [[ $value =~ ^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$ ]] || exit 1; done
for value in "$rate" "$warm" "$measure" "$drain" "$vus"; do [[ $value =~ ^[1-9][0-9]*$ ]] || exit 1; done
((rate<=2000 && warm<=600 && measure>=6 && measure<=1800 && drain<=600 && vus<=2000)) || exit 1
[[ $kind == validation || $kind == calibration || $kind == definitive ]] || exit 1
[[ $observe == 0 || $observe == 1 ]] && [[ $stats == 0 || $stats == 1 ]] || exit 1
[[ $telemetry == full || $telemetry == control ]] || exit 1
[[ $kind != definitive || ( $observe == 1 && $stats == 1 && $telemetry == full ) ]] || exit 1
if [[ $kind == definitive ]]; then
  [[ -f experimento/FROZEN-PROTOCOL.json && -z $(git status --porcelain) ]] || {
    echo 'Definitive runs require a frozen protocol and a clean checkout.' >&2; exit 1;
  }
fi
export EXPERIMENT_TOPIC="audit-$run"
dc=(docker compose -p "$project" -f docker-compose.yml -f experimento/compose.yml)
out="$root/.runtime/entrega04/$run-$variant"
[[ ! -e $out ]] || { echo 'Refusing evidence overwrite.' >&2; exit 1; }
mkdir -p "$out"
analyzer_id=$(docker image inspect -f '{{.Id}}' "$analyzer")
export EXPERIMENT_ANALYZER_IMAGE="$analyzer_id"
export EXPERIMENT_RUN_ID="$run" EXPERIMENT_DATASET_ID="$dataset" EXPERIMENT_VARIANT="$variant" EXPERIMENT_OUTPUT="$out"
export EXPERIMENT_UID="$(id -u)" EXPERIMENT_GID="$(id -g)"
fault_service=''
sampler=''
observer_id=''
load_name=''
cleanup() {
  if [[ -n $fault_service ]]; then "${dc[@]}" start "$fault_service" >> "$out/controller.log" 2>&1 || true; fi
  if [[ -n $sampler ]]; then touch "$out/.stop-stats"; wait "$sampler" || true; fi
  if [[ -n $observer_id ]]; then
    touch "$out/.stop-observer"
    docker stop -t 5 "$observer_id" >> "$out/controller.log" 2>&1 || true
  fi
  if [[ -n $load_name ]] && [[ $(docker inspect -f '{{.State.Running}}' "$load_name" 2>/dev/null || true) == true ]]; then
    docker stop -t 2 "$load_name" >> "$out/controller.log" 2>&1 || true
  fi
}
trap cleanup EXIT
{
  printf 'kind=%s\nrun_id=%s\ndataset_id=%s\nvariant=%s\nprofile=%s\nrate=%s\nwarmup_seconds=%s\nmeasure_seconds=%s\ndrain_seconds=%s\nvus=%s\n' "$kind" "$run" "$dataset" "$variant" "$profile" "$rate" "$warm" "$measure" "$drain" "$vus"
  printf 'instrumentation_version=2\nobserver_enabled=%s\nresources_enabled=%s\ntelemetry=%s\ngenerator_cpu_limit=2\ngenerator_memory_mib=2048\n' "$observe" "$stats" "$telemetry"
  printf 'analyzer_image_id=%s\nfault_seconds_requested=%s\n' "$analyzer_id" "${FAULT_SECONDS:-40}"
  printf 'application_images_sha256=%s\n' "$(docker image inspect -f '{{.Id}}' tcc-java-2026-sync-api:latest tcc-java-2026-async-api:latest tcc-java-2026-consumer:latest postgres:16-alpine apache/kafka:3.9.1 | sha256sum | cut -d ' ' -f1)"
  printf 'instrument_source_sha256=%s\n' "$(sha256sum experimento/run.sh experimento/load.js experimento/analyzer/src/main/java/br/com/ilan/tcc/experiment/*.java | sha256sum | cut -d ' ' -f1)"
  printf 'commit=%s\nstarted_utc=%s\n' "$(git rev-parse HEAD)" "$(date -u +%FT%T.%NZ)"
  if [[ -z $(git status --porcelain) ]]; then echo working_tree=clean; else echo working_tree=dirty; fi
  printf 'topic=%s\nk6_image=%s\n' "$EXPERIMENT_TOPIC" "$k6"
  docker version --format 'docker_client={{.Client.Version}} docker_server={{.Server.Version}}'
  docker compose version --short
  docker info --format 'docker_cpus={{.NCPU}} docker_memory_bytes={{.MemTotal}} kernel={{.KernelVersion}}'
  docker ps --format 'background_container={{.Names}}'
} > "$out/manifest.txt"
if [[ $kind == definitive ]]; then
  docker run --rm --network none --user "$(id -u):$(id -g)" \
    --mount "type=bind,src=$root/experimento/FROZEN-PROTOCOL.json,dst=/frozen.json,readonly" \
    --mount "type=bind,src=$out,dst=/evidence" "$analyzer_id" protocol /frozen.json /evidence/manifest.txt > "$out/protocol-check.txt"
fi
"${dc[@]}" --profile observation stop observer sync-api async-api consumer >> "$out/controller.log" 2>&1 || true
"${dc[@]}" up -d --no-build postgres kafka >> "$out/controller.log" 2>&1
for service in postgres kafka; do
  for ((i=0;i<120;i++)); do
    id=$("${dc[@]}" ps -q "$service")
    [[ $(docker inspect -f '{{.State.Health.Status}}' "$id") == healthy ]] && break
    sleep 1
  done
  [[ $(docker inspect -f '{{.State.Health.Status}}' "$id") == healthy ]] || exit 1
done
for topic in "$EXPERIMENT_TOPIC" "$EXPERIMENT_TOPIC-dlq"; do
  "${dc[@]}" exec -T kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka:9092 --create --topic "$topic" --partitions 1 --replication-factor 1 >> "$out/controller.log" 2>&1
done
if [[ $variant == sync ]]; then apps=(sync-api); target=http://sync-api:8080/audit;
else apps=(async-api consumer); target=http://async-api:8081/audit; fi
"${dc[@]}" up -d --no-build --force-recreate "${apps[@]}" >> "$out/controller.log" 2>&1
pg=$("${dc[@]}" ps -q postgres)
[[ $(docker inspect -f '{{index .Config.Labels "com.docker.compose.project"}}' "$pg") == "$project" ]] || exit 1
# Only generated records may be reset; no deletion of a user record is permitted.
for ((i=0;i<120;i++)); do
  exists=$("${dc[@]}" exec -T postgres psql -X -U audit -d auditdb -Atc "SELECT to_regclass('public.audit_records') IS NOT NULL" 2>/dev/null)
  [[ $exists == t ]] && break
  sleep 1
done
foreign=$("${dc[@]}" exec -T postgres psql -X -U audit -d auditdb -Atc "SELECT count(*) FROM audit_records WHERE source NOT LIKE 'experiment-%'")
[[ $foreign == 0 ]] || { echo 'Non-experimental data found; reset refused.' >&2; exit 1; }
"${dc[@]}" exec -T postgres psql -X -U audit -d auditdb -v ON_ERROR_STOP=1 -c 'TRUNCATE audit_records' >> "$out/controller.log"
ids=("$pg" "$("${dc[@]}" ps -q kafka)")
for app in "${apps[@]}"; do ids+=("$("${dc[@]}" ps -q "$app")"); done
network="$project"_default
docker inspect --format 'container={{.Name}} image={{.Image}} nano_cpus={{.HostConfig.NanoCpus}} memory_bytes={{.HostConfig.Memory}}' "${ids[@]}" >> "$out/manifest.txt"
printf 'analyzer_image_id=%s\n' "$analyzer_id" >> "$out/manifest.txt"
# Health check occurs before the run, with a bounded wait inside a short-lived k6 container.
ready=0
for ((i=0;i<90;i++)); do
  if docker run --rm --network "$network" --entrypoint sh "$k6" -c "wget -q -O /dev/null '${target%/audit}/health'"; then ready=1; break; fi
  sleep 1
done
((ready==1)) || exit 1
touch "$out/resources-errors.log" "$out/resources.tsv"
if [[ $observe == 0 ]]; then touch "$out/observation.jsonl.disabled"; fi
load_name="tcc-e04-load-$run"
k6_output=()
if [[ $telemetry == full ]]; then k6_output=(--out json=/output/k6.jsonl.gz); fi
docker create --name "$load_name" --network "$network" --cpus 2 --memory 2g --user "$(id -u):$(id -g)" \
  --mount "type=bind,src=$root/experimento,dst=/scripts,readonly" --mount "type=bind,src=$out,dst=/output" \
  -e "RUN_ID=$run" -e "DATASET_ID=$dataset" -e "VARIANT=$variant" -e "RATE=$rate" \
  -e "WARMUP_SECONDS=$warm" -e "MEASURE_SECONDS=$measure" -e "VUS=$vus" -e "TELEMETRY=$telemetry" \
  -e "PROFILE=$profile" -e "TARGET_URL=$target" "$k6" run --quiet "${k6_output[@]}" /scripts/load.js >> "$out/controller.log"
ids+=("$load_name")
if [[ $observe == 1 ]]; then
  "${dc[@]}" --profile observation up -d --no-deps --force-recreate observer >> "$out/controller.log" 2>&1
  observer_id=$("${dc[@]}" --profile observation ps -q observer)
  ids+=("$observer_id")
  observer_ready=0
  for ((i=0;i<30;i++)); do
    if [[ -f $out/observation.jsonl ]] && grep -q '"database_measured"' "$out/observation.jsonl"; then observer_ready=1; break; fi
    [[ $(docker inspect -f '{{.State.Running}}' "$observer_id") == true ]] || break
    sleep 1
  done
  ((observer_ready==1)) || { docker logs "$observer_id" > "$out/observer-console.txt" 2>&1; exit 1; }
fi
if [[ $stats == 1 ]]; then (
  while [[ ! -e $out/.stop-stats ]]; do
    at=$(date -u +%FT%T.%NZ)
    docker stats --no-stream --format "$at{{printf \"\\t\"}}{{.Name}}{{printf \"\\t\"}}{{.CPUPerc}}{{printf \"\\t\"}}{{.MemUsage}}" "${ids[@]}" >> "$out/resources.tsv" 2>> "$out/resources-errors.log" || break
    printf '{"batch_start":"%s","batch_end":"%s"}\n' "$at" "$(date -u +%FT%T.%NZ)" >> "$out/resource-batches.jsonl"
    sleep 1
  done
) & sampler=$!; fi
touch "$out/k6-console.txt"
docker start -a "$load_name" > "$out/k6-console.txt" 2>&1 & load_pid=$!
start_ms=''
for ((i=0;i<warm+120;i++)); do
  start_ms=$(sed -n 's/.*MEASUREMENT_START=\([0-9]*\).*/\1/p' "$out/k6-console.txt" | head -1)
  [[ -n $start_ms ]] && break
  kill -0 "$load_pid" 2>/dev/null || break
  sleep 1
done
[[ -n $start_ms ]] || { wait "$load_pid" || true; echo 'No measurement start marker.' >&2; exit 1; }
printf 'measurement_start_ms=%s\n' "$start_ms" >> "$out/manifest.txt"
if [[ $profile == postgres-stop || $profile == consumer-stop ]]; then
  offset=$((measure/3)); fault_seconds=${FAULT_SECONDS:-40}
  [[ $fault_seconds =~ ^[1-9][0-9]*$ ]] && ((fault_seconds+offset<measure)) || exit 1
  wait_until=$((start_ms/1000+offset))
  while (( $(date +%s)<wait_until )); do sleep 1; done
  if [[ $profile == postgres-stop ]]; then fault_service=postgres; else fault_service=consumer; fi
  printf 'fault_stop_command_utc=%s\nfault_seconds=%s\n' "$(date -u +%FT%T.%NZ)" "$fault_seconds" >> "$out/manifest.txt"
  "${dc[@]}" stop -t 0 "$fault_service" >> "$out/controller.log" 2>&1
  printf 'fault_stopped_utc=%s\n' "$(date -u +%FT%T.%NZ)" >> "$out/manifest.txt"
  sleep "$fault_seconds"
  "${dc[@]}" start "$fault_service" >> "$out/controller.log" 2>&1
  printf 'fault_restore_utc=%s\n' "$(date -u +%FT%T.%NZ)" >> "$out/manifest.txt"
  fault_service=''
fi
k6_exit=0
wait "$load_pid" || true
k6_exit=$(docker inspect -f '{{.State.ExitCode}}' "$load_name")
printf 'k6_exit=%s\nload_end_utc=%s\n' "$k6_exit" "$(date -u +%FT%T.%NZ)" >> "$out/manifest.txt"
docker inspect --format 'generator_image={{.Image}} generator_cpus={{.HostConfig.NanoCpus}} generator_memory={{.HostConfig.Memory}}' "$load_name" >> "$out/manifest.txt"
if [[ $profile == model ]]; then
  sleep 3
  docker run --rm --network "$network" --user "$(id -u):$(id -g)" \
    --mount "type=bind,src=$root/experimento,dst=/scripts,readonly" \
    -e "RUN_ID=$run" -e "DATASET_ID=$dataset" -e "VARIANT=$variant" -e "TARGET_URL=$target" \
    "$k6" run --quiet /scripts/contract.js > "$out/contract-console.txt" 2>&1
fi
sleep "$drain"
if [[ -n $observer_id ]]; then
  touch "$out/.stop-observer"
  observer_exit=''
  for ((i=0;i<15;i++)); do
    if [[ $(docker inspect -f '{{.State.Running}}' "$observer_id") == false ]]; then observer_exit=$(docker inspect -f '{{.State.ExitCode}}' "$observer_id"); break; fi
    sleep 1
  done
  [[ -n $observer_exit ]] || { docker stop -t 5 "$observer_id" >> "$out/controller.log"; observer_exit=$(docker inspect -f '{{.State.ExitCode}}' "$observer_id"); }
  printf 'observer_exit=%s\n' "$observer_exit" >> "$out/manifest.txt"
  docker logs "$observer_id" > "$out/observer-console.txt" 2>&1
  observer_id=''
fi
if [[ -n $sampler ]]; then touch "$out/.stop-stats"; wait "$sampler" || true; sampler=''; fi
docker rm "$load_name" >> "$out/controller.log"
for app in "${apps[@]}"; do
  docker logs "$("${dc[@]}" ps -q "$app")" 2>&1 | awk -v marker="\"run_id\":\"$run\"" 'index($0,marker) {print}'
done > "$out/app.log"
"${dc[@]}" exec -T postgres psql -X -U audit -d auditdb -At -v ON_ERROR_STOP=1 -c \
  "SELECT row_to_json(r) FROM (SELECT * FROM audit_records WHERE source='experiment-$dataset' ORDER BY event_id) r" > "$out/database.jsonl"
for spec in "$EXPERIMENT_TOPIC:retained" "$EXPERIMENT_TOPIC-dlq:dlq"; do
  topic=${spec%:*}; label=${spec#*:}
  # A timeout with zero messages is normal. Other exceptions are preserved and inspected.
  "${dc[@]}" exec -T kafka /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server kafka:9092 \
    --topic "$topic" --partition 0 --offset earliest --timeout-ms 3000 > "$out/$label.jsonl" 2> "$out/$label-export.log" || true
done
"${dc[@]}" exec -T kafka /opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server kafka:9092 \
  --describe --group "$EXPERIMENT_TOPIC-group" > "$out/kafka-lag-end.txt" 2>&1 || true
printf 'collection_end_utc=%s\n' "$(date -u +%FT%T.%NZ)" >> "$out/manifest.txt"
analysis_exit=0
docker run --rm --network none --user "$(id -u):$(id -g)" --mount "type=bind,src=$out,dst=/evidence" \
  "$analyzer_id" campaign /evidence > "$out/analyzer-console.txt" 2>&1 || analysis_exit=$?
printf 'analyzer_exit=%s\n' "$analysis_exit" >> "$out/manifest.txt"
(cd "$out"; find . -maxdepth 1 -type f ! -name SHA256SUMS ! -name '.stop-stats' -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)
echo "Evidence: $out (analyzer=$analysis_exit, k6=$k6_exit)"
cat "$out/summary.json" 2>/dev/null || cat "$out/analyzer-console.txt"
exit "$analysis_exit"
