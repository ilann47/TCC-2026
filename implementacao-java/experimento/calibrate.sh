#!/usr/bin/env bash
# Confirm one candidate common stable reference; this does not seek maximum capacity.
set -euo pipefail
cd "$(dirname "$0")/.."
dataset=$(</proc/sys/kernel/random/uuid)
export KIND=calibration PROFILE=steady RATE=${RATE:-50} WARMUP_SECONDS=60 MEASURE_SECONDS=300 DRAIN_SECONDS=30 VUS=${VUS:-256}
for variant in sync async; do DATASET_ID="$dataset" bash experimento/run.sh "$variant"; done
