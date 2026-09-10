#!/usr/bin/env bash
set -euo pipefail

selection="${1:-all}"
config_dir="${2:-}"
case "$selection" in
  all) iogs=(1 2) ;;
  1|2) iogs=("$selection") ;;
  *) echo "usage: $0 [all|1|2] [asic-config-directory]" >&2; exit 2 ;;
esac

mkdir -p log
stamp=$(date +%Y_%m_%d_%H_%M_%S_%Z)
pids=()
for iog in "${iogs[@]}"; do
  args=(--pacman_config "io/pacman_io${iog}.json" --pid_logged)
  if [[ -n "$config_dir" ]]; then
    args+=(--asic_config "$config_dir" --config_subdir "iog${iog}")
  fi
  python configure_larpix.py "${args[@]}" \
    >"log/configure-iog${iog}-${stamp}.log" 2>&1 &
  pid=$!
  pids+=("$pid")
  sed -i "s/IOG${iog}_PID=[0-9]*/IOG${iog}_PID=${pid}/" .envrc
  echo "IOG ${iog}: PID ${pid}, log/configure-iog${iog}-${stamp}.log"
done

status=0
for pid in "${pids[@]}"; do wait "$pid" || status=$?; done
exit "$status"
