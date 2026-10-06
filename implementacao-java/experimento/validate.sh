#!/usr/bin/env bash
# Functional/instrument validation, deliberately not the repeated final campaign.
set -euo pipefail
cd "$(dirname "$0")/.."
dataset=$(</proc/sys/kernel/random/uuid)
export KIND=validation RATE=5 WARMUP_SECONDS=5 MEASURE_SECONDS=18 DRAIN_SECONDS=5 VUS=32 FAULT_SECONDS=5
for variant in sync async; do
  PROFILE=model DATASET_ID="$dataset" bash experimento/run.sh "$variant"
done
for profile in postgres-stop burst; do
  dataset=$(</proc/sys/kernel/random/uuid)
  for variant in sync async; do PROFILE="$profile" DATASET_ID="$dataset" bash experimento/run.sh "$variant"; done
done
PROFILE=consumer-stop bash experimento/run.sh async
