#!/usr/bin/env bash
# Execute an explicitly supplied frozen plan. This script is NOT run by calibration.
set -euo pipefail
cd "$(dirname "$0")/.."
plan=${1:?Usage: bash experimento/campaign.sh experimento/calibracao/DATE/plan.csv}
[[ -f experimento/FROZEN-PROTOCOL.json && -f $plan ]] || exit 1
[[ -z $(git status --porcelain) ]] || { echo 'Commit the reviewed frozen configuration before definitive runs.' >&2;exit 1; }
while IFS=, read -r block scenario variant rate run dataset vus; do
  [[ $block == block ]] && continue
  [[ $block =~ ^([1-9]|10)$ && $scenario =~ ^(steady|burst|postgres-stop|consumer-stop)$ ]] || exit 1
  echo "Definitive block=$block profile=$scenario variant=$variant run=$run"
  KIND=definitive PROFILE="$scenario" RATE="$rate" RUN_ID="$run" DATASET_ID="$dataset" VUS="$vus" \
    WARMUP_SECONDS=60 MEASURE_SECONDS=300 DRAIN_SECONDS=90 FAULT_SECONDS=40 \
    TELEMETRY=full OBSERVE=1 STATS=1 bash experimento/run.sh "$variant"
done < "$plan"
