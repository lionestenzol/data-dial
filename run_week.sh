#!/usr/bin/env bash
# Build order step 11: the Day 0 check, then the 7-day run.
#
#   ./run_week.sh [BENCH_DIR]
#
# Day 0 builds the starting library and checks the logger's full-sync number
# against a real Raw Sync copy before anything is measured.  Days 1-7 are the
# spec's daily task: add 10-20 photos, edit 1-3 documents, open 3-5 new photos
# on B, export the day's log.
set -euo pipefail

BENCH=${1:-bench}
RUNS=$BENCH/runs
PY=${PYTHON:-python3}

# photos added, documents edited, photos opened on B - one entry per day
PHOTOS=(15 12 18 10 14 20 11)
EDITS=(  3  1  2  3  1  2  3)
OPENS=(  5  3  4  5  3  5  4)

echo "### Day 0: starting library and the Raw Sync check"
$PY make_batch.py day1 --out "$BENCH/A" --photos 30 --docs 24
$PY dial_sim.py sync --a "$BENCH/A" --b "$BENCH/B" --open 5 \
    --log "$RUNS/day0.jsonl" --mirror "$BENCH/rsync_mirror" --rawdir "$BENCH/raw_mirror"
$PY dial_sim.py verify --a "$BENCH/A" --b "$BENCH/B" --record "$RUNS/verify.jsonl"

for d in 1 2 3 4 5 6 7; do
  i=$((d - 1))
  echo
  echo "### Day $d: +${PHOTOS[$i]} photos, ${EDITS[$i]} edits, open ${OPENS[$i]}"
  $PY make_batch.py day2 --out "$BENCH/A" --photos "${PHOTOS[$i]}" \
      --edits "${EDITS[$i]}" --seed "$((11 + d))" | tail -1
  $PY dial_sim.py sync --a "$BENCH/A" --b "$BENCH/B" --open "${OPENS[$i]}" \
      --seed "$d" --log "$RUNS/day$d.jsonl" \
      --mirror "$BENCH/rsync_mirror" --rawdir "$BENCH/raw_mirror"
  $PY dial_sim.py verify --a "$BENCH/A" --b "$BENCH/B" --record "$RUNS/verify.jsonl"
done

echo
$PY dial_sim.py week --runs "$RUNS"
