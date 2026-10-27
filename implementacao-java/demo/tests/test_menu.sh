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
