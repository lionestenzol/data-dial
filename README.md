# dial_sim — a one-machine simulation of the v1 engine

Two local folders stand in for Device A and Device B. There is no network:
every message is handed straight to the other side, and its bytes are counted
as if they had been sent. Three numbers come out of each run — **dial bytes**,
**full-sync bytes** and **rsync bytes** — plus the deferred bytes the dial
still owes on originals nobody has opened yet.

Covers build-order steps 2–8 of the v1 spec, with the Raw Sync toggle (9) and
the rsync baseline (10) alongside, so the three numbers land side by side.

## Run it

```bash
python3 make_batch.py day1 --out bench/A              # 30 photos + 24 documents
python3 dial_sim.py  sync --a bench/A --b bench/B --open 5 \
                          --log bench/runs/day1.jsonl

python3 make_batch.py day2 --out bench/A              # the daily task: +15 photos, 3 edits
python3 dial_sim.py  sync --a bench/A --b bench/B --open 5 \
                          --log bench/runs/day2.jsonl

python3 dial_sim.py verify --a bench/A --b bench/B    # independent SHA-256 check
python3 -m pytest tests -q                            # the spec's Tests table
```

`sync` runs the dial, then Raw Sync, then `rsync_baseline.sh`, and prints the
day's summary. `--no-rsync` / `--no-rawsync` skip the baselines;
`dial_sim.py report --log F` re-prints a summary from a log.

Needs Python 3.11+, Pillow, zstandard, and rsync for the real-tool baseline.

## What is where

| file | build step | what it holds |
|---|---|---|
| `dial/keys.py` | 2 | the key model: file, chunk, thumb, manifest; canonical wire form; the rule that a preview never satisfies an exact want |
| `dial/chunker.py` | 3 | FastCDC, normalised chunking, 2 KiB / 8 KiB / 64 KiB |
| `dial/store.py` | 3 | the SHA-256 chunk pool, the key index, the per-file chunk cache |
| `dial/manifest.py` | 4 | scanning SyncSet into entries |
| `dial/device.py` | 4 | a device: folder, pool, have-check, path bindings |
| `dial/thumb.py` | 5 | thumb-v1: 512 px long edge, JPEG q70, deterministic |
| `dial/view.py` | 5 | B's preview-first library: original / preview / missing |
| `dial/router.py` | 6 | the four steps and 1 MiB packing |
| `dial/checker.py` | 7 | SHA-256 on every arrival, and what to do on a fail |
| `dial/engine.py` | 6–7 | one day: manifest, have-check, plan, retry, raw fallback |
| `dial/wire.py` | — | message framing, the byte ledger, zstd, the fault injector |
| `dial/jlog.py` | 8 | the JSONL log and the daily summary |
| `dial/rawsync.py` | 9 | the Raw Sync toggle: the full-sync baseline |
| `rsync_baseline.sh` | 10 | rsync on the same folder, both modes, bytes logged |
| `photogen.py`, `make_batch.py` | — | the test batch |

## How the bytes are counted

Everything the engine hands over is charged: manifests, have-questions and
have-answers, keys, recipes, thumbnails, raw chunks, and a 64-byte header per
message. Retries are charged again, because they cost again. A message the
link drops before it goes out is not charged, and the far side never saw it,
so a resumed run pays for content exactly once.

Non-photo chunks go over as zstd; photos go raw, being compressed already.

**Full-sync bytes** are what a tool that sends every new or changed file whole
would have spent today. The change set is kept on A's side
(`.dial/sent_manifest.json`): new or changed since A's last run. It has to be
A's side, because a full-sync tool already holds every original — a photo B
chose to defer is not something it would send again tomorrow.
`dial_sim.py sync` checks that column against a real Raw Sync copy each run
and says whether they match.

**Deferred bytes** are what the dial still owes: for a photo B has only seen a
thumbnail of, the original's size less what was sent for it. They are logged
apart from savings and count against the dial on the day the original is
opened. The summary's `dial + deferred` line is the worst case — the bill if B
opened every deferred original today.

**rsync bytes** are rsync's own `Total bytes sent` + `Total bytes received`,
both directions, same as the dial counts itself. The script measures both
`--no-whole-file` (the delta algorithm, what rsync does over a network — this
is the baseline) and `--whole-file` (what it does by default between local
paths).

## Shape of a log line

```json
{"ts":"2026-11-25T23:19:02.015Z","direction":"A->B","path":"Photos/IMG_0007.jpg",
 "form":"thumb","payload_bytes":20012,"header_bytes":64,
 "baseline_full_bytes":2203923,"deferred_bytes":2183911,
 "checker":"pass","elapsed_ms":0.006,"step":3,"kid":"v1:thumb:visual-preview:…"}
```

A path's full-sync cost is charged to the first message that mentions it and
its deferred bytes to the last, so summing a column over the log gives the
day's number without double counting.

## Known limits of the simulation

- No link: `elapsed_ms` and the timings in the summary are engine time
  (chunking, encoding, hashing, verifying), not transfer time.
- The photos in the batch are generated locally (`photogen.py`), since this
  machine has no camera and no network. They are built to behave like camera
  JPEGs — smooth field, hard edges, grain, q88, ~2 MB at 12 MP — but they are
  not photographs. The documents in the batch are real files off this machine.
- Two devices, one folder, no clock, no conflict resolution: v1 scope.
