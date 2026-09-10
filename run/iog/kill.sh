#!/usr/bin/env bash
set -euo pipefail
source .envrc
selection="${1:-all}"
case "$selection" in all) iogs=(1 2);; 1|2) iogs=("$selection");; *) echo "usage: $0 [all|1|2]" >&2; exit 2;; esac
for iog in "${iogs[@]}"; do
  var="IOG${iog}_PID"
  pid="${!var:-0}"
  if [[ "$pid" =~ ^[1-9][0-9]*$ ]] && kill -0 "$pid" 2>/dev/null; then kill "$pid"; fi
done
