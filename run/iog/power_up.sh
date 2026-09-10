#!/usr/bin/env bash
set -euo pipefail
selection="${1:-all}"
case "$selection" in all) iogs=(1 2);; 1|2) iogs=("$selection");; *) echo "usage: $0 [all|1|2]" >&2; exit 2;; esac
for iog in "${iogs[@]}"; do
  python configure_pacman.py --pacman_config "io/pacman_io${iog}.json" --verbose
done
