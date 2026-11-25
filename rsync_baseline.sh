#!/usr/bin/env bash
# The real-tool baseline: rsync between the same two folders, bytes logged.
#
#   ./rsync_baseline.sh SRC MIRROR_ROOT [OUT_JSON]
#
# Keeps two mirrors under MIRROR_ROOT so both of rsync's transfer modes can be
# measured day after day against the same change set:
#
#   delta  rsync -a --no-whole-file   the delta algorithm (what rsync is for;
#                                     it is what rsync does over a network, and
#                                     it is the number we treat as the baseline)
#   whole  rsync -a --whole-file      what rsync does by default on local paths
#
# Bytes logged are rsync's own "Total bytes sent" + "Total bytes received",
# both directions, matching how the dial counts its own traffic.
set -euo pipefail

SRC=${1:?usage: rsync_baseline.sh SRC MIRROR_ROOT [OUT_JSON]}
ROOT=${2:?usage: rsync_baseline.sh SRC MIRROR_ROOT [OUT_JSON]}
OUT=${3:-$ROOT/rsync_bytes.json}

mkdir -p "$ROOT/delta" "$ROOT/whole" "$(dirname "$OUT")"

run_one() {           # mode dest extra-flag
  local mode=$1 dest=$2 flag=$3 stats sent recv files
  stats=$(rsync -a --stats $flag --exclude '.dial' "$SRC"/ "$dest"/)
  sent=$(sed -n 's/^Total bytes sent: *//p'     <<<"$stats" | tr -d ',')
  recv=$(sed -n 's/^Total bytes received: *//p' <<<"$stats" | tr -d ',')
  files=$(sed -n 's/^Number of regular files transferred: *//p' <<<"$stats" | tr -d ',')
  printf '"%s":{"bytes_sent":%s,"bytes_received":%s,"total":%s,"files":%s}' \
         "$mode" "${sent:-0}" "${recv:-0}" "$(( ${sent:-0} + ${recv:-0} ))" "${files:-0}"
}

{
  printf '{"ts":"%s","src":"%s",' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$SRC"
  run_one delta "$ROOT/delta" --no-whole-file
  printf ','
  run_one whole "$ROOT/whole" --whole-file
  printf ',"baseline":"delta"}\n'
} > "$OUT"

cat "$OUT"
