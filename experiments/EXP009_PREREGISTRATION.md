# Experiment 009 — pre-registration (the P0 crossover benchmark)

Committed **before the full run**. The probe that confirmed photo regeneration
is byte-exact and that a JPEG is near-incompressible is declared as setup below,
not as a prediction. Closes `O-crossover`; bears on `O-selection-layer`,
`O-bet`, and GIR exit criteria.

## The question

This is the first experiment that tests the actual thesis instead of a tactic
inside it. DR-001's verdict: the one residual gap is a **general
mechanism-selection layer** — a chooser across transfer / delta / recompute /
cache that picks the cheapest per object. DR-001's own disposition: **benchmark
it before building it**, because maybe a single existing tool (rsync) already
captures the value. So:

> On a real workload spanning all four regimes, does a per-object selector move
> materially fewer bytes than the best single static policy — and is any margin
> over rsync-delta explained entirely by the one regime rsync cannot reach
> (recompute)?

## Setup (measured in the probe, declared not predicted)

- **Byte-exact regeneration confirmed.** `photogen.scene(seed)` → JPEG is
  bit-identical across runs (seed 7: two runs, same SHA-256), and different
  seeds differ. So recompute qualifies for `E_bitwise`. This is checked
  per-file in the run; any non-reproducible file is disqualified from the
  recompute arm and reported.
- **A generated JPEG is near-incompressible**: best of gzip/lzma/bz2 is 0.99x.
  So transfer and delta both cost ≈ full size on photos; recompute's recipe is
  the ~4-byte seed. ~10,000x gap where B holds the generator.
- Tools: no `rsync`/`xdelta` binary here, so the rsync block-delta algorithm
  (rolling checksum + strong hash, Tridgell–Mackerras) is implemented directly
  and its delta size counted faithfully (literals + copy refs + the signature
  bytes B sends A). Compression is real gzip/lzma/bz2.

## Corpus (real local data, four regimes, nobody picked it for the outcome)

| regime | source | B's state |
|---|---|---|
| recompute | photogen JPEGs from seeds | B has `photogen.py`; recipe = seed |
| delta | consecutive git versions of real repo text | B has version n−1 |
| cache | files B already holds exactly | B has exact X |
| incompressible | random bytes + the `.gz` artifacts | B has nothing related |
| compressible-text | repo source files | B has nothing related |

## Mechanisms and the decision rule

Per (file, B-state), cost in **bytes to realize X at B**:

- `cache`: 32 B if B has exact X, else N/A. receiver compute ≈ 0.
- `transfer`: min(gzip,lzma,bz2)(X) bytes. Always available. compute = decompress.
- `delta`: rsync block-delta size if B has a related X_old, else N/A.
- `recompute`: recipe bytes if B has the generator AND X regenerates byte-exact.
  compute = regeneration time.

Bytes is the primary metric (the bandwidth objective). **Receiver compute is a
declared budget, not converted to bytes** (GIR §3: keep units separate). A
mechanism is admissible if its receiver compute ≤ budget T; among admissible
mechanisms, minimise bytes. Sweep T ∈ {0, 1 ms, 10 ms, 100 ms, 1 s, 10 s}.

- **Selector(T)** = per-file min bytes over admissible mechanisms.
- Static policies: **always-transfer** (ignores B-state), **always-delta**
  (rsync; delta if B has X_old, else falls back to transfer).

## Predictions

| | prediction |
|---|---|
| **Z1** | Coverage: each of the four mechanisms is the unique cheapest for ≥1 file at some budget. |
| **Z2** | Bandwidth win: at T = 1 s, the selector moves ≤ 10% of always-transfer's bytes (≥10x reduction). |
| **Z3** | **THE CLAIM.** At T = 1 s the selector moves ≤ 50% of always-delta's (rsync's) bytes, AND removing the recompute arm collapses the selector to within 5% of always-delta. The entire margin over rsync is the recompute regime. |
| **Z4** | Null guard: at T = 0 (no receiver compute) the selector is within 5% of always-delta — rsync captures everything when B cannot compute. |
| **Z5** | The wall: on incompressible files with no generator and no related version, no mechanism beats transfer by > 5% (GIR §6, observed). |
| **Z6** | Every photogen file regenerates byte-exact; 0 disqualified from the recompute arm. |
| **Z7** | The dial is real: the per-file compute budget at which recompute becomes the cheapest admissible mechanism varies across files by ≥ 10x. |

## What each outcome means

- **Z3 holds**: the generalized selector is worth building — it beats the best
  single existing tool, and for a structural reason (rsync cannot exploit "B
  can regenerate"). `O-selection-layer` is justified. GIR's residual gap is a
  real, measured opportunity, not a taxonomy.
- **Z3 fails** (rsync ties the selector): the selector is NOT worth building;
  the honest answer to the whole project is "use rsync, plus recompute only
  where you already know it applies." DR-001's warning realized. This would be
  the most important negative result in the project.
- **Z5 fails** (something beats transfer on incompressible data): either a bug
  or a genuinely surprising structure; investigate before believing it.
- **Z6 fails**: recompute is not byte-exact and the whole recompute arm is
  `E_structural` at best — a correctness finding that outranks the economics.

## Known bias being guarded against

This project's documented failure is collapsing the objective into whatever is
easiest to measure, and this assistant's prediction errors cluster where a
quantity was never measured. The never-measured quantity here is **how much of
a real workload actually lives in the recompute regime** — the thing that
decides Z3. Z3 and Z4 are framed so the project's own thesis fails if rsync
ties, and the kill condition is stated above.
