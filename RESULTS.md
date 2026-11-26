# Day 0 plus a 7-day run

Batch: 12 MP JPEGs from `photogen.py` plus real documentation files taken off
this machine (`/usr/share/vim/vim91/doc`, `/usr/share/doc`). Day 0 is the
starting library — 30 photos, 24 documents. Days 1–7 are the spec's daily
task: 10–20 photos added, 1–3 documents edited, 3–5 photos opened on B.

One deviation from the spec's wording, worth knowing before reading the
table: the spec says "open 3-5 *new* photos", and the driver opened 3-5
photos B had no original of — new ones, or ones deferred on an earlier day.
22 of the 34 opens were of earlier days' photos. That is arguably the more
realistic pattern, and it exercises the deferred mechanic harder, but it is
not what the spec asked for. `dial_sim.py sync --open-new` restricts opens to
the day's own additions.
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

At the end of the week, 96 of 130 photos — **206.48 MB** — exist on A and
have never been anything but a thumbnail on B. Those bytes are owed, not
saved. They land on the dial the day someone opens them, which is what days
1–7 keep doing: most of a day's dial bytes are old originals being fetched,
not new content arriving.

**Correction.** An earlier version of this file added up the per-day deferred
column (251.70 MB) and called that the outstanding liability. It is not: that
column charges a photo on the day its thumbnail goes out and never retracts
it once the original is fetched and paid for in dial bytes, so it
double-counted 45.22 MB. The worst case it produced — "16% behind full sync
if B opened everything" — was wrong.

The real worst case is **+0.1%**. Open every one of the 96 remaining
originals and the week costs 285.05 MB against full sync's 284.83 MB.

That is not luck, it is the shape of the thing: a photo that gets opened
costs its original plus a thumbnail that turned out to be wasted, and a
thumbnail is about 1% of an original. So the dial's downside against full
sync is bounded at roughly the thumbnail overhead no matter how B behaves,
while its upside is however much of the library nobody opens — 72% on this
week's data. The risk is asymmetric in the dial's favour.

## Limits of this run

- No link: timings in the summaries are engine time, not transfer time.
- The photos are generated, not photographed — this machine has no camera and
  the network is closed. They are built to behave like camera JPEGs (~2.2 MB
  at 12 MP, ~110× thumbnail ratio), which is what the byte counts turn on.
  The documents are real files.
- Opening a document is a no-op here: documents always arrive as originals in
  the library phase, so the spec's "open 1 edited document" costs nothing
  extra. Only photos are preview-first.
