#!/usr/bin/env bash
# All values are declared before exploration; no definitive repetitions are run here.
set -euo pipefail
cd "$(dirname "$0")/.."
batch=${CALIBRATION_BATCH_ID:-$(</proc/sys/kernel/random/uuid)}
[[ $batch =~ ^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$ ]] || exit 1
session="$PWD/.runtime/calibration-2026-10-26/$batch"
[[ ! -e $session ]] || { echo 'Existing session; use its catalog rather than overwriting.' >&2; exit 1; }
mkdir -p "$session"
cp experimento/calibration-policy.json "$session/policy.json"
printf 'stage,block,variant,rate,run_id,folder,exit_code\n' > "$session/runs.csv"
image=$(docker image inspect -f '{{.Id}}' tcc-pilot-analyzer:local)
printf 'batch_id=%s\nanalyzer_image_id=%s\ncommit=%s\nstarted_utc=%s\n' "$batch" "$image" "$(git rev-parse HEAD)" "$(date -u +%FT%T.%NZ)" > "$session/manifest.txt"
function run_case() {
  local stage=$1 block=$2 variant=$3 rate=$4 warm=$5 seconds=$6 telemetry=$7 profile=$8 drain=$9
  local run folder code
  run=$(</proc/sys/kernel/random/uuid);folder="$PWD/.runtime/entrega04/$run-$variant";code=0
  echo "Starting $stage block=$block variant=$variant rate=$rate telemetry=$telemetry run=$run"
  KIND=calibration RUN_ID="$run" DATASET_ID="$dataset" RATE="$rate" WARMUP_SECONDS="$warm" MEASURE_SECONDS="$seconds" \
    PROFILE="$profile" FAULT_SECONDS=10 DRAIN_SECONDS="$drain" VUS=128 TELEMETRY="$telemetry" \
    OBSERVE=$([[ $telemetry == full ]] && echo 1 || echo 0) STATS=$([[ $telemetry == full ]] && echo 1 || echo 0) \
    bash experimento/run.sh "$variant" > "$session/$run-console.txt" 2>&1 || code=$?
  printf '%s,%s,%s,%s,%s,%s,%s\n' "$stage" "$block" "$variant" "$rate" "$run" "$folder" "$code" >> "$session/runs.csv"
  echo "Finished $stage variant=$variant run=$run exit=$code"
  [[ $code == 0 ]] || { tail -20 "$session/$run-console.txt"; exit "$code"; }
  last_folder=$folder
}

# Recovery must be observable within active load, not inferred from a first commit.
for profile in consumer-stop postgres-stop; do
  dataset=$(</proc/sys/kernel/random/uuid)
  run_case recovery-validation 1 async 10 10 90 full "$profile" 30
done

highest=0;index=0
for rate in 10 25 50 100; do
  dataset=$(</proc/sys/kernel/random/uuid);eligible=1
  if ((index%2==0));then variants=(sync async);else variants=(async sync);fi
  for variant in "${variants[@]}"; do
    run_case exploration 1 "$variant" "$rate" 20 60 full steady 15
    docker run --rm --network none --user "$(id -u):$(id -g)" --mount "type=bind,src=$last_folder,dst=/evidence" \
      "$image" assess /evidence/summary.json > "$session/$(basename "$last_folder")-assessment.txt"
    if ! grep -Eq '"reference_eligible"[[:space:]]*:[[:space:]]*true' "$last_folder/calibration-assessment.json"; then eligible=0; fi
  done
  if ((eligible==0));then echo "Rate $rate was not eligible in both variants; retaining prior stable candidate.";break;fi
  highest=$rate;index=$((index+1))
done
((highest>0)) || { echo 'No eligible common candidate. Investigate instruments/target; do not freeze.';exit 2; }
reference=$((highest/4*4))
echo "Selected candidate $reference events/s (multiple of four, not a maximum-capacity estimate)."
printf 'reference_candidate=%s\n' "$reference" >> "$session/manifest.txt"

# Counterbalanced reduced/full telemetry pairs; application milestone logging remains enabled.
for block in 1 2; do
  for variant in sync async; do
    dataset=$(</proc/sys/kernel/random/uuid)
    if ((block==1));then modes=(control full);else modes=(full control);fi
    for mode in "${modes[@]}"; do run_case telemetry-control "$block" "$variant" "$reference" 60 60 "$mode" steady 15;done
  done
done

dataset=$(</proc/sys/kernel/random/uuid)
for variant in async sync; do
  run_case confirmation 1 "$variant" "$reference" 60 300 full steady 30
  docker run --rm --network none --user "$(id -u):$(id -g)" --mount "type=bind,src=$last_folder,dst=/evidence" \
    "$image" assess /evidence/summary.json > "$session/$(basename "$last_folder")-assessment.txt"
done
printf 'finished_utc=%s\n' "$(date -u +%FT%T.%NZ)" >> "$session/manifest.txt"
echo "Calibration data collected at $session. Review overhead, confirmations and recovery before freezing."
