# Experiment log

## 001 — fixed computational relationship (prior work, not ours)
Matrix precomposition. 3,000 distinct inputs, 100% agreement, ~6.6x wall-time
improvement. Established technique (operator fusion). Recorded as a candidate
component, not as evidence of a novel architecture.

## 002 — discovered reusable substructure
**Question 001 left open:** 001 was handed its relationship. Can the system
*discover* which relationships to keep, and does that help on compositions it
has never seen?

Workload: K=40 operators over GF(65521), experiences = 12-operator sequences
applied to one novel input each. Every full sequence unique, so whole-result
caching is worthless by construction. Structure parameter alpha controls how
much of each sequence comes from recurring motifs. Discovery sees train only;
evaluation on held-out sequences generated afterwards.

| alpha | kept | steps/seq | MAC speedup | breakeven seqs | exact |
|---|---|---|---|---|---|
| 0.00 | 0 | 12.00 | 1.00 | — | yes |
| 0.25 | 4 | 10.82 | 0.97 | 272 | yes |
| 0.50 | 8 | 6.41 | 0.87 | 263 | yes |
| 0.75 | 8 | 5.17 | 0.96 | 216 | yes |
| 1.00 | 8 | 4.28 | 1.06 | 182 | yes |

Naive per-sequence fusion — the 001 technique at batch size 1 — costs **59x**
sequential execution.

### Predictions vs actual
| | prediction | actual | verdict |
|---|---|---|---|
| P1 | alpha=0 within 5% of sequential | 1.00, nothing kept | hit |
| P2 | alpha=1.0 gives >= 2.5x | 1.06x | **miss, -58%** |
| P3 | crossover near alpha 0.5 | no crossover at all; 0.87x there | **miss** |
| P4 | naive fusion >100x worse | 59x worse | **miss, right sign** |
| P5 | 100% exact everywhere | 100% in all 5 configs | hit |
| P6 | keep-threshold is count > N | built in, not tested; later broke N=128 | not a result |

## 002b — was 002 undersized?
002's held-out set (200) sat inside its own breakeven range (182–272), so the
one-time fusion cost ate the coverage win.

| held-out | steps/seq | MAC speedup | execution-only speedup |
|---|---|---|---|
| 200 | 4.46 | 1.04 | 2.69 |
| 500 | 4.46 | 1.65 | 2.69 |
| 1000 | 4.47 | 2.04 | 2.69 |
| 2000 | 4.49 | **2.31** | 2.67 |

| N | steps/seq | MAC speedup | breakeven |
|---|---|---|---|
| 8 | 4.27 | 0.44 | 596 |
| 16 | 4.59 | 0.89 | 240 |
| 32 | 4.63 | 1.37 | 113 |
| 64 | 4.46 | 1.04 | 187 |
| 128 | 12.00 | 1.00 | — (nothing kept) |

| | prediction | actual | verdict |
|---|---|---|---|
| Q1 | >= 2.3x at 2000 held-out | 2.31x | hit, barely |
| Q2 | breakeven linear in N | non-monotonic, confounded | **miss** |
| Q3 | N=16 wins at 200 seqs | 0.89x, loses | **miss** |
| Q4 | ceiling = coverage ratio | 2.67–2.69 flat while total rose 1.04→2.31 | hit |

## What was learned
1. **The mechanism has a hard ceiling equal to the coverage ratio.** Fusion
   buys *fewer* operations, never cheaper ones. Execution-only speedup is
   pinned at 2.67–2.69x no matter how long the workload runs.
2. **There is an amortisation floor set by the operator dimension.** Fusing an
   m-motif costs (m-1)N^3 once and saves (m-1)N^2 per use, so a primitive
   repays after ~N uses. Viability is a function of workload length over
   operator size, not of whether structure exists.
3. **The selection rule is defective.** Keeping a motif when its *training*
   count exceeds N starves at large N: at N=128 nothing was kept from 300
   training sequences and the mechanism degenerated to sequential. Selection
   must be driven by projected lifetime uses, not training-set frequency.
4. **A known-good technique can be catastrophically wrong in context.** 001's
   fusion, applied per sequence at batch size 1, is 59x worse than doing
   nothing. Established mechanisms are conditional, not free.

## Harness defects found
- The workload generator exhausts the space of unique motif-compositions and
  spins when asked for more sequences than the motif set can compose (hit at
  5,000). Needs a bounded generator before any long-workload run.

## Next, and materially different
002/002b only reduce operation count inside a fixed representation, and only
on the distribution they were mined from. The architectural claim needs two
things neither experiment touches:
- **Recursive composition** — primitives built from primitives, testing
  whether the substrate gets cheaper to extend as it grows.
- **Cross-workload transfer** — discover on workload A, evaluate on workload
  B drawn from a different motif set over the same operators, testing whether
  accumulated structure helps with experiences from a distribution it has
  never seen. That is the difference between compressing a known distribution
  and accumulating reusable capability.

## 003 — measured vs structural extraction cost
**Why:** PRIOR_ART.md showed cost-driven selection already exists three times
over, all three selecting against a structural proxy their own docs say need
not predict runtime. 002 reproduced that defect independently. So the open
question is whether a *measured* cost function beats a structural one, and
whether measuring repays itself.

**Domain:** convolution. `conv(a,b)` and `ifft(fft(a)·fft(b))` are exactly
equal; direct wins small, FFT wins large, and the crossover is a property of
the machine. An algorithmic choice, so no backend compiler rescues it.
Selection runs through egglog's `DagCostModel`, with only the weight table
differing between arms.

| arm | matches oracle | worst regret |
|---|---|---|
| ast_size (fewest nodes) | 4/10 | **x94.44** |
| static_weight (one scalar per operator) | 6/10 | x10.24 |
| measured (per-machine, per-n) | **10/10** | x1.00 |

Crossover n* = 256. Exact at every n.

### Predictions vs actual — 6 of 6
| | prediction | actual | verdict |
|---|---|---|---|
| R1 | crossover exists, 64 <= n* <= 4096 | n* = 256 | hit |
| R2 | ast_size picks direct everywhere, margin grows | 10/10 direct, regret 1.00 -> 94.44 | hit |
| R3 | one static table cannot be right across the range | wrong at the small end, 6/10 | hit |
| R4 | measured matches oracle within 5% | 10/10, regret exactly 1.00 | hit |
| R5 | calibration costs more than one resolution | 0.04 ms vs 0.0009 ms at n=16; 73 ms vs 0.25 ms at n=8192 | hit |
| R6 | bit-exact at every n | true at every n | hit |

### The result I did not predict
R5 is right but the shape of it is more useful than the prediction. Break-even
on calibration:

| n | waste per request under the static table | calibration | break-even |
|---|---|---|---|
| 16 | 0.0087 ms | 0.04 ms | **4.7 requests** |
| 32 | 0.0087 ms | 0.04 ms | 4.6 |
| 64 | 0.0084 ms | 0.05 ms | 5.7 |
| 128 | 0.0054 ms | 0.07 ms | 13.0 |
| 256+ | 0 | 0.14–73 ms | **never** |

Measuring repays inside ~5–13 requests exactly where the static table is
wrong, and never repays where the static table is already right — and that is
also where measurement is most expensive, because calibration scales with n
while the saving goes to zero.

So the mechanism is not "always measure". It is **measure where the static
model is uncertain, and only there**. That is a design rule the literature's
framing of this problem does not supply, and it came out of charging for the
measurement instead of assuming it free.

### Honest limits
This domain was *chosen* because the proxy must fail in it. The 94x figure is
an existence proof that structural cost can be catastrophically wrong — it
says nothing about how often that happens in real workloads. Single machine,
single numeric kernel family, NumPy's FFT rather than a tuned library, and
the e-graph carries one rule. Nothing here establishes that measured costing
helps on a workload nobody picked in advance.
