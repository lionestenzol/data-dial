# Run: 45 photos, 24 documents, two days

Batch: 12 MP JPEGs from `photogen.py` plus real documentation files taken off
this machine (`/usr/share/vim/vim91/doc`, `/usr/share/doc`). Day 1 is the
starting library; day 2 is the spec's daily task — 15 photos added, 3
documents edited, 5 new photos opened on B.

Reproduce with the commands in the README. Logs: `bench/runs/day{1,2}.jsonl`.

## The three numbers

| | day 1 (30 photos, 24 docs) | day 2 (+15 photos, 3 edits) | both days |
|---|---:|---:|---:|
| **dial** | **12.90 MB** | **10.97 MB** | **23.88 MB** |
| full sync | 67.43 MB | 32.51 MB | 99.94 MB |
| rsync (delta) | 67.45 MB | 32.46 MB | 99.91 MB |
| saving vs full sync | 80.9% | 66.3% | 76.1% |
| saving vs rsync | 80.9% | 66.2% | 76.1% |
| deferred (not opened yet) | 53.26 MB | 27.91 MB | 81.17 MB |

Checker: 100% pass over 156 messages, 0 failures, 0 fallbacks.
`dial_sim.py verify`: 34 originals byte-exact, 35 previews, 0 missing, 0 mismatched.
The logger's full-sync column equalled the real Raw Sync bytes on both days
(67,429,833 and 32,513,856).

## Where the dial's day-2 bytes went

| form | bytes |
|---|---:|
| raw chunks (5 opened originals + document deltas) | 10.52 MB |
| thumbnails (15 new photos) | 0.30 MB |
| recipes | 0.10 MB |
| chunk queries, manifest, have-answers | 0.05 MB |

## The honest parts

**The win is previews, not dedupe.** Unique photos do not shrink: the 5
originals B opened cost 10.4 MB of the day's 10.97 MB. What saves the day is
that the other 10 new photos arrived as 20 KB thumbnails instead of 2.2 MB
files.

**On documents the dial is level with rsync, not ahead.** The 3 edited
documents cost the dial 13.3 KB (recipe plus the one changed chunk each);
rsync's delta algorithm spent about 14.2 KB on the same three files. Within
noise. The spec predicted this.

**If B opened everything, the dial would lose on day 2.** Dial plus deferred
is 38.88 MB against rsync's 32.46 MB — a 6.4 MB loss, because a photo fetched
after its thumbnail costs the thumbnail twice over. The dial's edge is real
only while most photos stay unopened. Day 1 stays ahead even in that worst
case (66.16 MB against 67.45 MB), but only barely.

**rsync's delta mode barely matters here.** Whole-file and delta differ by
69 KB over the whole day-2 change set, because 15 of the 18 changed files are
new photos with nothing on the far side to delta against.
