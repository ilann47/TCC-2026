#!/usr/bin/env bash
# Unit tests with shell doubles. No real Docker, HTTP calls or load generation.
set -euo pipefail
source "$(dirname "$0")/../apresentacao.sh"
passed=0
ok() { passed=$((passed+1));printf 'ok %s - %s\n' "$passed" "$1"; }

validate_settings
ok 'default bounded load'
if (TCC_DEMO_RATE=11;validate_settings) >/dev/null 2>&1;then exit 1;fi
if (TCC_DEMO_SECONDS=31;validate_settings) >/dev/null 2>&1;then exit 1;fi
if (TCC_DEMO_RATE='1+1';validate_settings) >/dev/null 2>&1;then exit 1;fi
ok 'invalid or unbounded settings rejected'
if (TCC_DEMO_DASHBOARD=maybe;validate_settings) >/dev/null 2>&1;then exit 1;fi
for invalid_port in 0 80 65536 05665 '5665:80' '1+5665';do
  if (TCC_DEMO_DASHBOARD_PORT=$invalid_port;validate_settings) >/dev/null 2>&1;then exit 1;fi
done
(TCC_DEMO_DASHBOARD_PORT=5666;validate_settings)
ok 'dashboard settings reject invalid or nonlocal port syntax'
(
  dashboard_options
  [[ ${TCC_DEMO_DASHBOARD_ARGS[0]} == --publish && ${TCC_DEMO_DASHBOARD_ARGS[1]} == '127.0.0.1:5665:5665' ]]
  [[ " ${TCC_DEMO_DASHBOARD_ARGS[*]} " == *' K6_WEB_DASHBOARD=true '* ]]
  [[ " ${TCC_DEMO_DASHBOARD_ARGS[*]} " == *' K6_WEB_DASHBOARD_HOST=0.0.0.0 '* ]]
  [[ " ${TCC_DEMO_DASHBOARD_ARGS[*]} " == *' K6_WEB_DASHBOARD_PERIOD=1s '* ]]
  [[ " ${TCC_DEMO_DASHBOARD_ARGS[*]} " == *' K6_WEB_DASHBOARD_EXPORT=/output/painel-k6.html '* ]]
)
ok 'dashboard binds only the host loopback and exports an offline report'
(
  TCC_DEMO_DASHBOARD=0;dashboard_options
  [[ ${#TCC_DEMO_DASHBOARD_ARGS[@]} == 2 && ${TCC_DEMO_DASHBOARD_ARGS[1]} == K6_WEB_DASHBOARD=false ]]
  dashboard_port_available
)
ok 'disabled dashboard does not publish any port'
(
  docker() { printf 'existing-demo\n'; }
  if no_demo_load >/dev/null 2>&1;then exit 1;fi
)
ok 'another demo load or waiting dashboard blocks concurrent load'
(
  docker() { return 1; }
  if no_demo_load >/dev/null 2>&1;then exit 1;fi
)
ok 'Docker failure does not bypass concurrent demo guard'
(
  docker() { return 0; }
  no_demo_load
)
ok 'no active demo permits the next bounded load'
(
  TCC_DEMO_APP=$(mktemp -d)
  no_experiment() { return 0; }
  run_k6_locked() { return 7; }
  if run_k6 sync;then exit 1;else [[ $? == 7 ]];fi
  run_k6_locked() { return 0; }
  run_k6 async
)
ok 'demo lock is released even when the load fails'
(
  TCC_DEMO_APP=$(mktemp -d)
  mkdir -p "$TCC_DEMO_APP/.runtime/demonstracao"
  exec {held_lock}>"$TCC_DEMO_APP/.runtime/demonstracao/k6.lock"
  flock -n "$held_lock"
  no_experiment() { return 0; }
  run_k6_locked() { echo 'unexpected concurrent load' >&2;exit 1; }
  if run_k6 sync >/dev/null 2>&1;then exit 1;fi
  flock -u "$held_lock"
  exec {held_lock}>&-
)
ok 'exclusive demo lock prevents a second load'
(
  no_experiment() { return 0; }
  no_demo_load() { return 1; }
  if compare_menu >/dev/null 2>&1;then exit 1;fi
)
ok 'comparison menu refuses to start while a demo dashboard or load is active'

(
  docker() { printf 'active-experiment\n'; }
  if no_experiment >/dev/null 2>&1;then exit 1;fi
)
ok 'active experimental project blocks mutation'
(
  docker() { return 1; }
  if no_experiment >/dev/null 2>&1;then exit 1;fi
)
ok 'Docker lookup failure is not interpreted as no experiment'

(
  dc() { printf '0123456789abcdef\n'; }
  docker() {
    case $3 in
      *com.docker.compose.project*) printf 'another-project\n';;
      *com.docker.compose.service*) printf 'consumer\n';;
      *) return 1;;
    esac
  }
  if owned_service consumer >/dev/null 2>&1;then exit 1;fi
)
ok 'foreign container rejected before stop/start'
(
  dc() { printf '0123456789abcdef\n'; }
  docker() {
    case $3 in
      *com.docker.compose.project*) printf 'tcc-java-2026\n';;
      *com.docker.compose.service*) printf 'consumer\n';;
      *) return 1;;
    esac
  }
  [[ $(owned_service consumer) == 0123456789abcdef ]]
)
ok 'owned container accepted'

(
  count=0
  TCC_DEMO_CONSUMER_PAUSED=1
  owned_service() { printf '0123456789abcdef\n'; }
  docker() { [[ $* == 'start 0123456789abcdef' ]];count=$((count+1)); }
  cleanup >/dev/null
  [[ $count == 1 && $TCC_DEMO_CONSUMER_PAUSED == 0 ]]
)
ok 'exit restores consumer paused by this menu'
(
  TCC_DEMO_CONSUMER_PAUSED=0
  docker() { echo 'unexpected mutation' >&2;exit 1; }
  cleanup >/dev/null
)
ok 'exit does not change an untouched consumer'
(
  no_experiment() { return 0; }
  owned_service() { printf '0123456789abcdef\n'; }
  docker() { printf 'false\n'; }
  dc() { echo 'unexpected stop' >&2;exit 1; }
  pause_consumer >/dev/null
  [[ $TCC_DEMO_CONSUMER_PAUSED == 0 ]]
)
ok 'already stopped consumer is not claimed as paused by menu'

(
  curl() { printf '202'; }
  http_call POST http://127.0.0.1:18003/audit unused unused
  [[ $TCC_DEMO_HTTP_CODE == 202 ]]
)
ok 'HTTP code remains separate from body'
(
  curl() { printf '000';return 7; }
  if http_call POST http://127.0.0.1:18003/audit unused unused >/dev/null 2>&1;then exit 1;fi
  [[ $TCC_DEMO_HTTP_CODE == 000 ]]
)
ok 'transport failure is not success'
bash "$TCC_DEMO_APP/demo/apresentacao.sh" --help >/dev/null
ok 'help does not need Docker or start services'
printf '%s shell checks passed; no live service was called.\n' "$passed"
