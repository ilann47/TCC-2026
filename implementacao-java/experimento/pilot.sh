#!/usr/bin/env bash
# A bounded instrumentation pilot, not the definitive experimental campaign.
set -euo pipefail
cd "$(dirname "$0")/.."
project_dir=$(pwd)
variant=${1:-}
rate=${RATE:-2}
duration=${DURATION:-10s}
vus=${VUS:-4}
drain_seconds=${DRAIN_SECONDS:-5}
run_id=${RUN_ID:-$(</proc/sys/kernel/random/uuid)}
run_id=${run_id,,}
k6_image='grafana/k6:2.3.0@sha256:9c2dee7f8ed74d317e4027c06a10f169b625638189de8d4555d0b3486a5aeb34'
analyzer_image='tcc-pilot-analyzer:local'

[[ $variant == sync || $variant == async ]] || { printf 'Usage: bash experimento/pilot.sh sync|async\n' >&2; exit 1; }
[[ $run_id =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]] || { printf 'RUN_ID must be a UUID.\n' >&2; exit 1; }
[[ $rate =~ ^[1-9][0-9]?$ ]] && ((rate <= 20)) || { printf 'RATE must be 1..20.\n' >&2; exit 1; }
[[ $vus =~ ^[1-9][0-9]?$ ]] && ((vus <= 50)) || { printf 'VUS must be 1..50.\n' >&2; exit 1; }
[[ $duration =~ ^([1-9][0-9]?)s$ ]] && ((${BASH_REMATCH[1]} <= 60)) || { printf 'DURATION must be 1s..60s.\n' >&2; exit 1; }
[[ $drain_seconds =~ ^[1-9][0-9]?$ ]] && ((drain_seconds <= 30)) || { printf 'DRAIN_SECONDS must be 1..30.\n' >&2; exit 1; }
output="$project_dir/.runtime/pilot/$run_id-$variant"
[[ ! -e $output ]] || { printf 'Refusing to overwrite an existing run: %s\n' "$output" >&2; exit 1; }

container_ids=()
for service in postgres kafka sync-api async-api consumer; do
  container_id=$(docker compose ps -q "$service")
  [[ -n $container_id && $(docker inspect --format '{{.State.Running}}' "$container_id") == true ]] || {
    printf 'Service %s is not running. Start it with docker compose up -d.\n' "$service" >&2; exit 1;
  }
  if [[ $service == postgres || $service == kafka ]]; then
    [[ $(docker inspect --format '{{.State.Health.Status}}' "$container_id") == healthy ]] || {
      printf 'Service %s is not healthy yet.\n' "$service" >&2; exit 1;
    }
  fi
  container_ids+=("$container_id")
done
network=$(docker inspect --format '{{range $name, $value := .NetworkSettings.Networks}}{{$name}}{{"\n"}}{{end}}' "${container_ids[2]}")
[[ -n $network && $network != *$'\n'* ]] || { printf 'Expected one Compose network.\n' >&2; exit 1; }

# Build/tests and image download happen before the measurement window.
docker build -t "$analyzer_image" "$project_dir/experimento/analyzer"
if ! docker image inspect "$k6_image" >/dev/null 2>&1; then docker pull "$k6_image"; fi
mkdir -p "$output"
start_time=$(date -u +%Y-%m-%dT%H:%M:%SZ)
{
  printf 'kind=instrumentation_pilot\nrun_id=%s\nvariant=%s\nrate=%s\nduration=%s\nvus=%s\ndrain_seconds=%s\n' "$run_id" "$variant" "$rate" "$duration" "$vus" "$drain_seconds"
  printf 'start_utc=%s\ncommit=%s\n' "$start_time" "$(git rev-parse HEAD)"
  if [[ -z $(git status --porcelain) ]]; then printf 'working_tree=clean\n'; else printf 'working_tree=dirty\n'; fi
  printf 'k6_image=%s\nanalyzer_image_id=%s\nnetwork=%s\n' "$k6_image" "$(docker image inspect --format '{{.Id}}' "$analyzer_image")" "$network"
  docker version --format 'docker_client={{.Client.Version}} docker_server={{.Server.Version}}'
  docker compose version --short
  docker inspect --format 'container={{.Name}} image={{.Image}} nano_cpus={{.HostConfig.NanoCpus}} memory_bytes={{.HostConfig.Memory}}' "${container_ids[@]}"
  docker run --rm "$k6_image" version
} > "$output/manifest.txt"

sampler_pid=''
stop_sampler() {
  if [[ -n $sampler_pid ]]; then
    touch "$output/.sampling-stop"
    wait "$sampler_pid" || true
    sampler_pid=''
  fi
}
trap stop_sampler EXIT
printf 'batch_start_utc,container,cpu_percent,memory_usage\n' > "$output/resources.csv"
(
  while [[ ! -e $output/.sampling-stop ]]; do
    sampled_at=$(date -u +%Y-%m-%dT%H:%M:%S.%NZ)
    docker stats --no-stream --format "$sampled_at,{{.Name}},{{.CPUPerc}},{{.MemUsage}}" "${container_ids[@]}" >> "$output/resources.csv" 2>> "$output/resources-errors.log" || break
    sleep 1
  done
) &
sampler_pid=$!

if [[ $variant == sync ]]; then target_url='http://sync-api:8080/audit'; else target_url='http://async-api:8081/audit'; fi
k6_exit=0
docker run --rm --network "$network" --user "$(id -u):$(id -g)" \
  --mount "type=bind,src=$project_dir/experimento,dst=/scripts,readonly" \
  --mount "type=bind,src=$output,dst=/output" \
  -e "RUN_ID=$run_id" -e "VARIANT=$variant" -e "RATE=$rate" -e "DURATION=$duration" \
  -e "VUS=$vus" -e "TARGET_URL=$target_url" \
  "$k6_image" run --out json=/output/k6.jsonl /scripts/pilot.js 2>&1 | tee "$output/k6-console.txt" || k6_exit=$?
printf 'k6_exit=%s\nload_end_utc=%s\n' "$k6_exit" "$(date -u +%Y-%m-%dT%H:%M:%S.%NZ)" >> "$output/manifest.txt"

# Bounded observation window; absence after this wait is unresolved evidence, not loss.
sleep "$drain_seconds"
# Correlate by UUID instead of a daemon-side --since filter: collect only this
# run's milestones, even when client/daemon timestamp filtering differs.
for index in 2 3 4; do
  docker logs "${container_ids[index]}" 2>&1 | awk -v marker="\"run_id\":\"$run_id\"" 'index($0, marker) {print}'
done > "$output/app.log"
docker compose exec -T postgres psql -X -U audit -d auditdb -At -v ON_ERROR_STOP=1 -c \
  "SELECT row_to_json(r) FROM (SELECT event_id,event_type,entity_type,entity_id,actor_id,source,occurred_at,payload,content_hash,persisted_at FROM audit_records WHERE source='k6-pilot-$run_id' ORDER BY event_id) r" \
  > "$output/database.jsonl"
stop_sampler
printf 'collection_end_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%S.%NZ)" >> "$output/manifest.txt"

analysis_exit=0
docker run --rm --user "$(id -u):$(id -g)" --network none \
  --mount "type=bind,src=$output,dst=/evidence" "$analyzer_image" \
  "$run_id" "$variant" /evidence/k6.jsonl /evidence/app.log /evidence/database.jsonl /evidence \
  | tee "$output/analyzer-console.txt" || analysis_exit=$?
printf 'analyzer_exit=%s\n' "$analysis_exit" >> "$output/manifest.txt"
(cd "$output" && sha256sum manifest.txt k6.jsonl k6-console.txt app.log database.jsonl resources.csv resources-errors.log summary.json events.csv analyzer-console.txt > SHA256SUMS)
printf '\nEvidence preserved at: %s\n' "$output"
if ((k6_exit != 0)); then exit "$k6_exit"; fi
exit "$analysis_exit"
