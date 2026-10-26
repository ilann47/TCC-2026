#!/usr/bin/env bash
# Full bounded calibration, controls and confirmations; never a definitive campaign.
set -euo pipefail
exec bash "$(dirname "$0")/calibration-session.sh"
