#!/usr/bin/env bash
# Execute only the reviewed plan; calibration never invokes this script.
set -euo pipefail
cd "$(dirname "$0")/.."
check_only=0
if [[ ${1:-} == --check ]];then check_only=1;shift;fi
plan=${1:?Usage: bash experimento/campaign.sh [--check] experimento/calibracao/DATE/plan.csv}
frozen=experimento/FROZEN-PROTOCOL.json
[[ -f $frozen && -f $plan ]] || exit 1
if python3 -c 'import json,sys;sys.exit(0 if json.load(open("experimento/FROZEN-PROTOCOL.json"))["schema_version"]==2 else 1)';then
  if ((check_only));then python3 experimento/check_reduced_plan.py "$plan";exit 0;fi
  python3 experimento/check_reduced_plan.py "$plan" --require-unused
  exec python3 experimento/reduced_campaign.py campaign
fi
[[ -z $(git status --porcelain) ]] || { echo 'Commit the reviewed frozen configuration before definitive runs.' >&2;exit 1; }
check_file() {
  local key=$1 file=$2 expected
  expected=$(awk -F '"' -v key="$key" '$2 == key {print $4}' "$frozen")
  [[ $expected =~ ^[0-9a-f]{64}$ && $(sha256sum "$file" | cut -d ' ' -f1) == "$expected" ]] || {
    echo "Frozen file/hash mismatch: $file" >&2;exit 1;
  }
}
check_file plan_sha256 "$plan"
check_file base_compose_sha256 docker-compose.yml
check_file observer_compose_sha256 experimento/compose.yml
if ((check_only));then echo 'Frozen plan and Compose hashes match; no load or state change performed.';exit 0;fi
if [[ -n $(docker ps -q --filter label=com.docker.compose.project=tcc-java-2026) ]];then
  echo 'Stop the interactive TCC project before measurement: docker compose -p tcc-java-2026 stop. Other projects must not be stopped without authorization.' >&2;exit 1;
fi
while IFS=, read -r block scenario variant rate run dataset vus; do
  [[ $block == block ]] && continue
  [[ $block =~ ^([1-9]|10)$ && $scenario =~ ^(steady|burst|postgres-stop|consumer-stop)$ ]] || exit 1
  echo "Definitive block=$block profile=$scenario variant=$variant run=$run"
  KIND=definitive PROFILE="$scenario" RATE="$rate" RUN_ID="$run" DATASET_ID="$dataset" VUS="$vus" \
    WARMUP_SECONDS=60 MEASURE_SECONDS=300 DRAIN_SECONDS=90 FAULT_SECONDS=40 \
    TELEMETRY=full OBSERVE=1 STATS=1 bash experimento/run.sh "$variant"
  summary=".runtime/entrega04/$run-$variant/summary.json"
  for role in generator observer;do
    cpu=$(awk -v role="$role" '$0 ~ "\""role"\"[[:space:]]*:" {inside=1;next} inside&&/"cpu_p95_percent_of_limit"/{sub(/^[^:]*:[[:space:]]*/,"");sub(/[,[:space:]]*$/,"");print;exit}' "$summary")
    memory=$(awk -v role="$role" '$0 ~ "\""role"\"[[:space:]]*:" {inside=1;next} inside&&/"memory_max_percent_of_limit"/{sub(/^[^:]*:[[:space:]]*/,"");sub(/[,[:space:]]*$/,"");print;exit}' "$summary")
    if [[ $role == generator ]];then cpu_max=70;memory_max=75;else cpu_max=80;memory_max=85;fi
    if [[ ! $cpu =~ ^[0-9]+([.][0-9]+)?$ || ! $memory =~ ^[0-9]+([.][0-9]+)?$ ]] || ! awk -v cpu="$cpu" -v memory="$memory" -v cpu_max="$cpu_max" -v memory_max="$memory_max" 'BEGIN {exit !(cpu<=cpu_max && memory<=memory_max)}';then
      echo "$role headroom insufficient; preserve this run and investigate before attributing results to the API." >&2;exit 2;
    fi
  done
done < "$plan"
