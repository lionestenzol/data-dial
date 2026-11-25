# Day 0 plus a 7-day run

Batch: 12 MP JPEGs from `photogen.py` plus real documentation files taken off
this machine (`/usr/share/vim/vim91/doc`, `/usr/share/doc`). Day 0 is the
starting library — 30 photos, 24 documents. Days 1–7 are the spec's daily
task: 10–20 photos added, 1–3 documents edited, 3–5 new photos opened on B.
By day 7 SyncSet holds 154 files, 631 MB.

Reproduce: `./run_week.sh bench`. Logs in `bench/runs/day{0..7}.jsonl`,
per-day summaries beside them, the table from `dial_sim.py week --runs
bench/runs`. The run is deterministic — the same seeds give the same bytes.

## The three numbers, per day

| day | dial MB | full sync MB | rsync MB | vs full | vs rsync | deferred MB |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | **12.90** | 67.43 | 67.45 | 80.9% | 80.9% | 53.26 |
| 1 | **11.32** | 33.37 | 32.47 | 66.1% | 65.1% | 29.99 |
| 2 | **6.96** | 26.04 | 26.02 | 73.3% | 73.3% | 23.61 |
| 3 | **9.07** | 38.84 | 38.71 | 76.7% | 76.6% | 38.34 |
| 4 | **11.08** | 21.66 | 21.54 | 48.8% | 48.5% | 19.20 |
| 5 | **6.80** | 30.25 | 30.23 | 77.5% | 77.5% | 25.75 |
| 6 | **11.32** | 42.83 | 42.75 | 73.6% | 73.5% | 40.23 |
| 7 | **9.12** | 24.41 | 23.71 | 62.6% | 61.5% | 21.31 |
| **all** | **78.57** | **284.83** | **282.88** | **72.4%** | **72.2%** | **251.70** |

414 messages. Checker 100% pass, 0 failures, 0 fallbacks, every day.

## Done when

- [x] Used for the daily task 7 days in a row — days 1–7 after the day 0 library.
- [x] Every send logged against both baselines — and on all 8 days the
      logger's full-sync column equalled the bytes a real Raw Sync copy moved
      (67,429,833 · 33,368,541 · 26,040,767 · 38,841,506 · 21,660,889 ·
      30,248,518 · 42,831,013 · 24,410,009).
- [x] Checker passes every time, no uncorrected failures — 0 of 414 messages
      failed a check.
- [x] Beats full sync on data every day — 8/8.
- [x] Beats the real tool on at least one day — 8/8.
- [x] Library matches, opened originals byte-exact — `dial_sim.py verify` run
      after every day: 8 checks, 0 missing, 0 mismatched. At the end, 58
      originals byte-exact and 96 previews across 154 files.

## Where the bytes go

Day 4 is the worst day at 48.8%, and it says what the dial is: 10 photos
added, 5 opened. The five originals cost 10.7 MB of the day's 11.08 MB. Day 5
is the best at 77.5% — 14 added, 3 opened. The ratio of opens to adds sets
the saving almost on its own.

On documents the dial is ahead, but modestly, and only part of it is the
dial's design:

| | dial | rsync (delta) |
|---|---:|---:|
| day 0, 2.66 MB of documents, cold | 1.11 MB | 2.68 MB |
| days 1–7, 2.09 MB of edits | 0.09 MB | 0.12 MB |

The cold-start win is zstd on chunk payloads, not chunking — rsync was not
asked to compress. On the daily edits the two are within a few kilobytes of
each other: a recipe plus one changed chunk against rsync's rolling
checksums. The spec predicted this, and it holds.
(rsync's document figure is its day total less the photo bytes, so it is
approximate by rsync's own protocol overhead, a kilobyte or so a day.)

## What the deferred column means

251.70 MB of originals exist on A that B has only ever seen as thumbnails.
Those bytes are owed, not saved. They land on the dial the day someone opens
them — which is what days 1–7 keep doing, and why a day's dial bytes are
mostly originals being fetched rather than new content arriving.

If B opened every deferred original, the week would cost 330.27 MB against
full sync's 284.83 MB: the dial would finish **16% behind**, because a photo
fetched after its thumbnail pays for the thumbnail twice. Only day 0 wins
even in that worst case (66.16 MB against rsync's 67.45 MB). The dial's edge
is real, repeatable, and conditional on most photos staying unopened.

## Limits of this run

- No link: timings in the summaries are engine time, not transfer time.
- The photos are generated, not photographed — this machine has no camera and
  the network is closed. They are built to behave like camera JPEGs (~2.2 MB
  at 12 MP, ~110× thumbnail ratio), which is what the byte counts turn on.
  The documents are real files.
- Opening a document is a no-op here: documents always arrive as originals in
  the library phase, so the spec's "open 1 edited document" costs nothing
  extra. Only photos are preview-first.
