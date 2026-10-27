#!/usr/bin/env bash
# Safety tests; no real Docker/load calls.
set -euo pipefail
source "$(dirname "$0")/../comparar.sh"
(
  docker() { printf 'foreign-active-run\n'; }
  if compare_guard >/dev/null 2>&1;then exit 1;fi
)
(
  docker() { return 1; }
  if compare_guard >/dev/null 2>&1;then exit 1;fi
)
(
  TCC_COMPARE_CLAIMED=0
  compare_dc() { echo 'unexpected mutation' >&2;exit 1; }
  compare_stop
)
(
  TCC_COMPARE_CLAIMED=1
  TCC_COMPARE_OUTPUT=$(mktemp -d)
  count=0
  compare_dc() { [[ $* == 'stop -t 5' ]];count=$((count+1)); }
  docker() { [[ $* == 'ps -q --filter label=com.docker.compose.project=tcc-entrega04' ]]; }
  compare_stop
  [[ $TCC_COMPARE_CLAIMED == 0 && $count == 1 ]]
)
bash "$TCC_COMPARE_APP/demo/comparar.sh" --help >/dev/null
printf '5 comparison safety checks passed; no live service called.\n'
