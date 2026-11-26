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

## 004 — how often is structural cost wrong on a corpus nobody picked?
**Why:** 003 proved structural cost *can* be 94x wrong, in a domain chosen so
the proxy had to fail. HANDOFF.md set the frequency question as the honest
next step, and designed it so the answer could be "rarely, so the mechanism is
niche."

**Corpus:** 913 FPCores, FPBench @090d8198 + Herbie bench @884621aa, pinned by
SHA256. Mined from Hamming ch.3, LULESH, CoolProp, mathjs, Octave, Rust libm,
PBRT, basilisk, exasim, and the Rosa/Daisy/Salsa/FPTaylor suites. Both suites
were assembled by the floating-point **accuracy** community years before this
project; neither was selected for how cost models behave on it. 802 in scope,
111 excluded by category (array/tensor 38, while 21, if 18, user-defined calls
17, oversized 7, other 10). 743 cores evaluated, **539 decisions** (a decision
is a core with ≥2 accuracy-admitted equivalent candidates), 2,483 candidates.

Candidates come from SymPy's own simplification API plus integer-power
expansion. Accuracy admits (relative error ≤ 1e-6 against a 30-digit
reference), cost selects — a candidate that is faster but wrong is never a
candidate.

### The distribution, not the maximum

| arm | =oracle | ≤1.05 | p50 | p90 | p95 | p99 | max | ≥1.5 |
|---|---|---|---|---|---|---|---|---|
| ast_size | **65.3%** | **78.7%** | 1.000 | 1.221 | **1.451** | 3.572 | 48.30 | **4.3%** |
| static_weight | 61.0% | 73.8% | 1.000 | 1.297 | 1.517 | 2.819 | 48.30 | 5.6% |
| measured | 60.9% | 74.0% | 1.000 | 1.274 | 1.512 | 2.592 | 48.30 | 5.4% |

Tree counting instead of DAG counting improves every arm: ast_size p95
1.451 → **1.309**, static 1.517 → 1.444, measured 1.512 → 1.404.

Timing noise floor over 743 re-timings of the *same* candidate: p50 1.0000x,
p95 1.0375x, p99 1.1230x, max 1.3643x. **No re-timing reached 1.5x**, so the
≥1.5 column is clean of noise. The p90 band near 1.2 sits above the 99th
percentile of noise and is meaningful in aggregate, but a single decision
there is weak evidence.

### Answer to the question
**Structural cost is exactly optimal at the median and materially wrong on
4.3% of decisions.** The 003 phenomenon is real outside its chosen domain —
worst case here is **48.30x** on `sineOrder3`, where the as-written form has
fewer nodes and runs 0.983 ms against 0.020 ms for SymPy's simplification —
but it is a tail event, not a typical one.

So measured costing is a **tail-risk fix, not a throughput win**, and the
architecture should say so. On this corpus, 95% of decisions have nothing to
win.

### The result that inverts the programme's assumption
**Plain node counting beat both the textbook table and measured per-operator
cost** — smaller tail, more exact-oracle matches, less waste per decision
(0.01380 ms against 0.01862 and 0.01746). Measuring per-operator latency made
selection *worse*. T5, T9 and T10 all missed on this.

The mechanism is not that node count is a better cost model. It is the
opposite, and the dissociation is the finding:

| model | Spearman r with runtime | p95 regret |
|---|---|---|
| ast_size (tree) | 0.8357 | **1.309** |
| static (tree) | **0.9131** | 1.444 |
| measured (tree) | 0.9037 | 1.404 |

**The weighted models predict runtime better and select worse.** Selection
only has to rank the handful of equivalent forms inside one candidate set —
a local, near-tie comparison — not to predict runtime globally. A model can be
better calibrated overall and still systematically mis-rank exactly those
near-ties. Global fit is the wrong figure of merit for a selector, and this
experiment would have reported the opposite conclusion had it measured fit
instead of regret.

Two concrete mechanisms behind the weighted arms' losses, on 46 of 539
decisions:
- NumPy computes `a**2` in 3.2 µs but `a*a` in 7.2 µs, while `a**3` takes
  41.9 µs against 14.6 µs for `a*a*a`. One `pow_int` weight is wrong at one
  end of the exponent range **by construction** — 003's structural
  impossibility, arising here with nobody choosing it. On the 153 decisions
  holding an `x*x` candidate, exact-oracle match collapses: ast_size 35.3%
  (from 77.2%), static and measured **20.3%** (from 77.2%).
- `JAX exp2 as exp(log(2)*x)`: simplification rewrites it to `2**x`, which the
  weighted models price as cheaper and which runs 5.08x slower.

### Predictions vs actual — 7 of 10
| | prediction | actual | verdict |
|---|---|---|---|
| T1 | ≥400 decisions | 539 | hit |
| T2 | ast_size p50 ≤ 1.05 | 1.0000 | hit |
| T3 | ast_size p95 ≥ 1.25, max ≥ 2.0 | 1.451, 48.30 | hit |
| T4 | frac(regret ≥ 1.5) in 2–25%, est 10% | **4.3%** | hit, est 2.3x high |
| T5 | static beats ast_size; measured adds <1.20x | static 1.517 **worse** than ast 1.451 | **miss, inverted** |
| T6 | measured matches oracle <90% | 60.9% | hit |
| T7 | tree counting beats DAG on ≥2 arms | all 3 improved | hit |
| T8 | x*x decisions degrade every arm | 35.3/20.3/20.3% vs ~77% | hit |
| T9 | calibration repaid within 50 decisions | **never repays** | **miss, inverted** |
| T10 | ordering survives without power expansion | p50 1.0000 ✓, second clause assumed T5 | **miss, mis-specified** |

T9's miss is stronger than "725 decisions". Measured's waste per decision
(0.01746 ms) *exceeds* ast_size's (0.01380 ms), so the 13.5 ms calibration has
no break-even at all here — it buys negative value. 003's rule was "measure
where the static model is uncertain"; this adds **and only if the thing you
measure is the thing that drives cost.** Per-operator latency measured in
isolation is not that thing for this backend.

T10 was mis-specified by me, not merely wrong: its second clause silently
assumed T5. The artifact question it was meant to ask answers **no** — with
power expansion removed, ast_size p50 is still 1.0000x and ast_size is still
the best of the three arms (p95 1.251 against static 1.412, measured 1.435).
Power expansion amplified the tail (≥1.5 from 2.6% to 4.3%) but did not
create the ordering. The predicate stands as a miss; only its interpretation
was corrected.

Also recorded: the analysis script's test of the memory-pass hypothesis is
**tautological** — ast_size weights are 1.0 per operator and 0.0 per leaf, so
ast_size *is* the interior-node count. It is left in the script labelled as
such rather than deleted. The hypothesis that cost is driven by intermediate
arrays remains untested.

### The oracle is not a policy
Timing every admitted candidate costs **30.454 ms per decision** against
0.1878 ms to simply run the best form — **162x**. Perfect selection by
measurement is unaffordable per request, which is what makes the cheapness of
the cost model the whole game.

### Honest limits
Single machine, single backend, and that backend decides a lot: vectorised
NumPy over 16 K-element L2-resident arrays, where `lambdify` performs no CSE
(228.8 µs against 118.5 µs with it) and cost is near-linear in operator count
including temporaries. Scalar code, a fused compiler, or cache-resident sizes
would re-rank the arms, and the DAG-vs-tree result is specifically an artifact
of this backend's lack of CSE. Candidates come from one CAS, so the candidate
sets are SymPy-shaped. Accuracy admission at 1e-6 against a 30-digit reference
excludes rewrites that trade accuracy for speed, which is deliberate but
narrows the candidate space. 111 of 913 cores are out of scope, including all
control flow. Timings were taken in a shared cloud container; the noise floor
is measured and reported rather than assumed away.

### Harness defects found
- First full run crashed at ~150 cores: 13 in-scope cores declare `:pre`
  domains spanning many orders of magnitude (Hamming's large-x examples reach
  1e308, one demo core declares the whole float range) and `rng.uniform`
  overflows once `hi-lo` exceeds the float range. Uniform sampling was wrong
  there regardless — every draw lands in the top decade. Now log-uniform for
  sign-consistent wide domains, as Herbie's own sampler does.
- The FPCore tokenizer initially treated `[` and `]` as ordinary symbol
  characters, so every `(let ([x 1]) ...)` binding parsed as malformed. This
  silently cost 165 cores (634 parsed, then 799) and would have passed
  unnoticed as a plausible scope exclusion. Rejections must be itemised by
  reason, or a parser bug reads as a corpus property.
