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

> **AMENDED by 004, then REPLACED by 006 (`O-003-measured`).** 004 added the
> condition this rule was missing — *and only if the thing you measure is the
> thing that drives cost* — after measured per-operator cost turned out worse
> than counting nodes on a real corpus. 006 then replaced the rule outright:
> the standing recommendation is **run a cheap oracle everywhere**, which is
> explicitly *not* "only where uncertain". What survives from 003 is that an
> *asymptotic* difference (O(n²) vs O(n log n)) is invisible to any weight
> table; that is why 003's domain worked, and it is a narrower claim than the
> rule as stated above.

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
> **CORRECTED by 006.** The 162x below is real but it is a property of *this*
> oracle, not of oracles — 006's first line is "that price is a design choice,
> not a fact". Timing every candidate once, on 256-element probes rather than
> best-of-11 at full size, costs ~1/550th as much and still recovers ~90% of
> the waste. "Perfect selection by measurement is unaffordable per request" is
> false as written; it is unaffordable *at best-of-11 on deployed-size arrays*.

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

## 005 — can the regret tail be flagged without paying the oracle?
**Why:** 004 left measured costing resting on 4.3% of decisions while the
oracle costs 162x simply running the best form. A mechanism that is wrong 4%
of the time is worth having only if you can tell *which* 4% cheaply. If not,
measured costing cannot be targeted and should be dropped from the resolution
policy rather than scoped.

No new measurement: this re-uses 004's 539 decisions, so its risk is
overfitting, which is what the grouped cross-validation addresses. Policy under
test is 004's best cheap arm (`ast_size`, tree counting). Primary target is
regret ≥ 1.2 — 52 positives holding 87.8% of all waste, above the measured
noise p99 of 1.123; the 20 positives at ≥ 1.5 cannot support a stable precision
estimate and are secondary. Grouped 5-fold CV with whole source files assigned
to folds; thresholds fit on training folds only.

### The criterion was economic, not statistical
Flagging a decision recovers **all** of its waste whatever its regret, so
precision matters only through the quantity that decides deployment:

> break-even requests per expression = Σ(oracle cost over flagged) / Σ(waste recovered)

Ship criterion, fixed in advance: ≤ 200 requests per expression while flagging
≤ 20% of decisions.

### Result — FAIL, and not because the oracle is too expensive

| rule | flagged | waste kept | break-even (requests) | ship |
|---|---|---|---|---|
| perfect detector ≥1.5 | 3.7% | 83.1% | **107.9** | would pass |
| perfect detector ≥1.2 | 9.6% | 87.8% | **117.5** | would pass |
| `dag_vs_tree` | 11.3% | 74.3% | 854.8 | fail |
| `disagree_ast_meas` | 13.5% | 62.3% | 1158.3 | fail |
| `disagree_any` | 14.5% | 62.5% | 1159.9 | fail |
| **flag everything** | 100% | 100% | **1216.9** | fail |
| `sq_powexp` | 28.4% | 56.3% | 1485.9 | fail |
| `disagree_ast_static` | 10.8% | 10.0% | 5505.4 | fail |
| `pow_gen` | 8.2% | 9.0% | 6742.6 | fail |

The best cheap rule reaches 854.8 requests against a 200 bar — and against
1216.9 for flagging everything. **Cheap targeting buys a 1.4x improvement on
doing no targeting at all**, where perfect targeting would buy 10.4x.

A combined logistic over all nine predicates, scored out-of-fold, reaches
AUC 0.749 — better than every single predicate (best 0.652) and nowhere near
enough. At a 20% flagging budget it achieves precision 0.215, recall 0.442,
and a break-even of 426.3.

So the failure is **not** that the oracle is unaffordable: a perfect detector
passes at 117.5 requests. The failure is in detection, and the gap is 7.3x.

### Why cheap predicates fail here — tested, not asserted
Every predicate flags decisions whose mean oracle cost is far above average,
while correlating weakly with the waste it would recover:

| rule | corr with oracle cost | corr with waste | mean oracle cost, flagged | unflagged |
|---|---|---|---|---|
| `disagree_ast_meas` | 0.174 | 0.130 | 133.4 ms | 14.3 ms |
| `dag_vs_tree` | 0.168 | 0.182 | 140.4 ms | 16.4 ms |
| `disagree_ast_static` | 0.146 | **-0.002** | 128.6 ms | 18.6 ms |
| `pow_gen` | 0.199 | **0.003** | 186.8 ms | 16.6 ms |

Across all 539 decisions, `corr(oracle cost, waste) = 0.146`. So:

**Expression size drives the oracle's cost but not the waste. The cheap
structural predicates correlate with size. Targeting on them therefore spends
measurement budget in proportion to what measuring costs rather than in
proportion to what it recovers.** Flagged decisions cost 7–11x more to measure
than unflagged ones while holding no more error. That is the mechanism, and it
is a property of the predicates available, not of the oracle's price.

### Predictions vs actual — 5 of 7
| | prediction | actual | verdict |
|---|---|---|---|
| U1 | best single precision ≤0.35 at recall ≥0.5 | `sq_powexp` 0.211 at recall 0.584 | hit |
| U2 | disagreement beats `sq_powexp` | AUC 0.646 vs 0.652 at ≥1.2 | **miss, by 0.006** |
| U3 | combined beats singles on AUC, precision at recall .5 still <0.5 | 0.749 vs 0.652; 0.232 | hit |
| U4 | held-out precision ≥15% below train for tuned predicates | `_spread` +1.7%, `_ncand` −60.8% | **miss** |
| U5 | perfect detector still needs >100 requests | 117.5 | hit |
| U6 | best realistic detector 1.5–10x worse than perfect | 7.3x | hit |
| U7 | at ≤20% budget, recall ≤0.75 and residual waste ≥25% | 0.442, 50.6% | hit |

U2's miss is 0.006 of AUC, inside noise, and reverses decisively at the ≥1.5
secondary target (0.837 against 0.519) — so model disagreement does carry the
signal for *large* regret, just not for the 1.2–1.5 band that holds most of the
positives. U4's miss is methodologically welcome: the threshold search was
constrained by the 20% flagging budget, which kept it conservative enough that
held-out matched train. At ≥1.5 both tuned predicates did drop ~50%, so the
overfitting effect exists, just not at the primary target.

### What this does to the architecture
> **SUPERSEDED by 006 (`O-005-targeting` → `O-006-oracle-price`).** The
> recommendation below no longer stands. 006 showed the question was wrong:
> this section tried to *target* an oracle price that should simply have been
> *lowered*. A single-repeat oracle on 256-element probes breaks even in 4.7
> requests per expression applied to every decision, so no detector is needed.
> Point 3 below invites a search for better tail predicates — **do not do
> that**; it is withdrawn. What survives here is the measured reason cheap
> predicates fail (expression size drives measurement cost but not error,
> `corr = 0.146`), which is why 006 did not try to fix the detector.

**Measured costing should be dropped from the resolution policy**, with the
door left open on one specific condition. Stated precisely:

1. Structural cost is optimal at the median and materially wrong on 4.3% of
   real decisions (004).
2. The resulting waste cannot be recovered economically, because no cheap
   predicate separates the tail: 854.8 requests per expression against 1216.9
   for not targeting at all.
3. The blocker is detector quality, not oracle price. A perfect detector would
   pass at 117.5 requests. Anyone who finds a tail predicate that is **not
   confounded with expression size** reopens this; the confound is the thing to
   defeat, and it is now measured.

### Honest limits
Inherits all of 004's limits — single machine, vectorised NumPy with no CSE,
SymPy-shaped candidate sets. Adds three of its own. The positive class is
small (52 at ≥1.2, 20 at ≥1.5), so precision estimates are noisy and the ≥1.5
column should not be read as stable. The predicate family is the nine cheap
signals listed; a richer feature set or a learned model over expression
structure is untested and is exactly where the size confound would have to be
broken. Most importantly, **the oracle's own price is treated as fixed at
best-of-11 timing of every candidate**, and it need not be: a cheaper, noisier
oracle (fewer repeats, smaller arrays) would scale every break-even down
roughly linearly. 004 recorded only best-of-11 times, so a noisy oracle's pick
quality is not recoverable from this data. That is the single most promising
way to rescue the mechanism and it requires a new measurement run.

## 006 — what is the cheapest sufficient oracle? (reverses 005)
**Why:** 005 recommended dropping measured costing, but every break-even in it
assumed one oracle price — best-of-11 timing of every candidate, 30.454 ms per
decision. That price is a design choice. 004 kept only best-of-11 *minima*, so
a noisy oracle's pick quality was unrecoverable; this run records **48
individual timings per candidate**, split alternately into disjoint simulation
and truth pools so neither is biased by drift, plus 12 samples at each of three
smaller probe sizes. 536 decisions.

### Repeat reduction: cost falls linearly, quality barely moves

| R | oracle ms | waste recovered | % of R=24 | mis-pick rate | break-even, no targeting |
|---|---|---|---|---|---|
| **1** | 1,614 | 13.014 ms | **91.6%** | **22.9%** | **124.1** |
| 2 | 3,205 | 13.542 | 95.3% | 14.4% | 236.6 |
| 4 | 6,355 | 13.805 | 97.1% | 11.0% | 460.4 |
| 12 | 19,106 | 14.152 | 99.6% | 5.6% | 1350.0 |
| 24 | 38,209 | 14.211 | 100% | 4.5% | 2688.7 |

The hinge held. **A single-repeat oracle mis-picks on 22.9% of decisions and
still recovers 91.6% of the waste**, because oracle noise flips near-ties and
near-ties are by definition the decisions with almost nothing to lose. Mis-pick
*rate* is the wrong metric; recovered waste is the right one — which is why V3
was pre-registered to predict a high mis-pick rate alongside V2.

### Size reduction: the result I predicted wrong, and the one that matters

| config | oracle ms | waste recovered | break-even |
|---|---|---|---|
| **probe=256, R=1** | **55** | 86.9% | **4.7** |
| probe=1024, R=1 | 125 | 87.5% | 10.2 |
| probe=256, R=3 | 160 | 89.5% | 13.2 |
| probe=4096, R=1 | 419 | 82.0% | 36.2 |

I predicted (V5) that ranking on 256-element arrays would transfer poorly
because per-call overhead dominates there. It transfers at **91.9%** of full-size
R=12 quality for ~1/31 of the cost. V6 named repeat reduction as the rescue;
small probes beat it by ~27x.

### The decision, with uncertainty attached

| | break-even | bootstrap 95% | verdict |
|---|---|---|---|
| 005's baseline: R=11, full size, no targeting | 1280.7 | [532, 3903] | FAIL |
| R=1 full, no targeting | 132.3 | [51.5, 497] | marginal |
| R=1 full, **perfect** targeting | 11.7 | [7.1, 19.9] | pass |
| **probe=256, R=1, no targeting** | **4.7** | **[1.9, 24.0]** | **PASS** |

**005's recommendation is reversed.** And the shape of the reversal is the
finding: *a cheap oracle applied to every decision (4.7 requests) beats perfect
targeting of an expensive one (11.7 requests)*. 005 spent itself trying to
target a price that should have been lowered instead. The detector problem
005 could not solve turns out not to need solving.

Break-even of ~5 requests also lands exactly where 003 put calibration ("repays
within ~5 requests where the static table is wrong"), from a completely
different direction.

### Predictions vs actual — 5 of 7
| | prediction | actual | verdict |
|---|---|---|---|
| V1 | oracle cost linear in R within 10% | within 1.6% at every R | hit |
| V2 | **hinge:** R=1 recovers ≥90% of R=24 | 91.6% | hit, but see below |
| V3 | mis-pick rate at R=1 ≥ 20% | 22.9% | hit |
| V4 | R=1 break-even ≤20 perfect, ≤100 cheap rule | 11.6 and 82.0 | hit |
| V5 | small probes transfer poorly (≤70%) | 91.9% | **miss, optimistic** |
| V6 | cheapest passing config is R≤3 at full size | probe=256, R=1 | **miss, wrong mechanism** |
| V7 | R=1 no-targeting ≤150 requests | 124.1 | hit, not robust |

### What is NOT established
**The waste is pathologically concentrated: one decision holds 38.8% of it, the
top three hold 66.6%, the top ten hold 85.9%.** Every "fraction of waste
recovered" number therefore has a wide interval — V2's 91.6% is [70.7%, 96.6%]
under a bootstrap over decisions, and the probe-size ranking above is **not
resolvable at all** (probe=256 R=1 at [56.4%, 94.3%] overlaps probe=4096 R=1 at
[30.2%, 95.5%]). So:

- **Robust:** a cheap oracle clears the 200-request bar by a wide margin. The
  worst case of the best config's interval is 24 requests, still 8x under the
  bar. That conclusion does not depend on the fragile fractions.
- **Not robust:** that 256 is the *best* probe size, that R=1 recovers
  specifically 91.6%, and V7's point estimate of 124.1 for full-size R=1
  (interval [51.5, 497] straddles the bar).
- The concentration itself is a finding about this corpus and a warning for the
  next experiment: with waste this concentrated, 536 decisions is a small
  sample however many expressions it came from.

### Honest limits
Inherits 004's and 005's: single machine, vectorised NumPy with no CSE,
SymPy-shaped candidate sets, accuracy admission at 1e-6. The probe transfer
result is specific to a backend whose cost is near-linear in operator count —
on a fusing backend small probes may rank quite differently, which is now the
most important untested question (HANDOFF item B). Oracle cost is charged as
evaluation time only, excluding compilation, which is right for a deployed
candidate already compiled but wrong if candidates must be compiled to be
timed; for a JIT backend that term could dominate and would have to be charged.
The reversal is bounded to the same single-machine regime as everything else
in this programme.

### For reuse
`exp006_candidate_exprs.json.gz` holds every admitted candidate's `srepr`, so
item B can re-time the identical candidate sets on another backend without
regenerating them through SymPy.

## 007 — does charging compilation undo 006? (yes)
**Why:** 006 concluded a cheap oracle applied to every decision breaks even in
4.7 requests per expression, and on that basis the standing recommendation
became "keep measured costing, run a cheap oracle everywhere, do not build a
detector." That number charges **evaluation time only**. On any compiling
backend you cannot time a candidate without first compiling it. `HANDOFF.md`
flagged the hole when the result was written and said the term could undo 006
on its own. It does.

**Backend:** `sympy.ccode` scalar body + a hand-written loop, `gcc -O2 -shared
-fPIC -march=native`, loaded with `ctypes`. Zero new dependencies. The compile
charge is the wall time of the `gcc` subprocess. 538 decisions, 2,287
candidates, 605 s. Accuracy re-admitted on the C output at 1e-6 against a
30-digit reference.

### The accounting is the result

| accounting | break-even (requests per expression) | vs 200 bar |
|---|---|---|
| 006's, evaluation only, on this backend | 63.7 | — |
| **marginal — `k−1` compiles charged** | **5,733** `[4,247, 7,928]` | **29x over** |
| gross — all `k` compiles charged | 7,440 | 37x over |

Charging every compile to the oracle would have been the easy move and it is
wrong: a no-oracle policy must still compile whatever form it chose, so only
`k−1` compiles are the oracle's *marginal* cost. **006 fails by 29x even on
that generous reading**, and the bootstrap interval does not come near the bar.

### Predictions vs actual — 6 of 6
| | prediction | actual | verdict |
|---|---|---|---|
| W1 | compile ≥ 100x evaluation | 46.8 ms vs 403.7 µs = **116x** | hit |
| W2 | gross break-even > 200 | 7,440 | hit |
| W3 | **marginal** break-even > 200 | **5,733** `[4,247, 7,928]` | hit |
| W4 | marginal in [1,000, 50,000] | 5,733 | hit |
| W5 | C waste within 3x of NumPy's | 16.31% vs 14.91% = **1.09x** | hit |
| W6 | break-even varies <1.2x across probe sizes | **1.011x** | hit |

### The finding worth carrying forward
**The waste is real and backend-independent; the method for finding it is not.**

W5 is the one that makes this more than a negative result. Structural selection
leaves **16.31% of runtime** on the table under compiled C against **14.91%**
under NumPy — the prize is essentially the same size on both. What changes by
three orders of magnitude is the *price of discovering it*. So 006's conclusion
was never about measurement being good; it was about NumPy evaluation being
cheap. Stated as a rule:

> **Measured cost selection is viable only where evaluation is cheap relative
> to compilation.** On an interpreted or vectorised backend that holds and the
> oracle repays in ~5 requests. Where candidates must be compiled to be timed,
> it does not hold, and the structural model is the only affordable selector —
> which is the one 004 found was the better selector anyway.

W6 closes the obvious escape. 006's cheap-probe trick was its whole advantage,
and it is now worthless: break-even varies **1.011x** across probe sizes
256/1024/4096, because one compiled artifact serves both probe and deployment,
so shrinking the probe shrinks a term that is no longer dominant.

### Two things that did not go as expected
- **`-ffast-math` disqualified nothing.** 2,287 candidates admitted under
  `-O2`, 2,287 under `-O2 -ffast-math`, with the same 86 rejected by both. The
  flag was held out of the primary arm because it was expected to interact with
  the 1e-6 admission; at that tolerance it does not.
- **gcc already does the strength reduction that drove much of 004.** In C,
  `as_written` and `powexp/as_written` time within 1% of each other, because
  `pow(x,2)` is compiled to `x*x` regardless. The pow-vs-mul inversion that
  collapsed exact-oracle match to 20.3% in 004 is a property of NumPy's
  dispatch, not of arithmetic. This matters for `O-008`: a whole candidate
  family that mattered on NumPy is inert under a compiler.

### Honest limits
One machine, one compiler, one flag set. `gcc -O2` is not an aggressive fuser —
and the smoke test measured hand-fused C at only **0.97x NumPy** at 16,384
elements, because NumPy's per-operator loops are already L2-resident and
bandwidth-bound at that size. So this experiment establishes what charging
compilation does to the *economics*; it does **not** establish a backend where
operator count stops tracking cost, which is what `O-008` needs and what
`O-fusion-premise` now tracks. A JIT with a cheaper compile step (numba's
~50–200 ms is in the same range as gcc's 46.8 ms, so probably not) or a
persistent compilation cache would change the arithmetic, and neither is tested.

### Harness defects found
- **SIGBUS killed two full runs at exactly core 50.** The build filename came
  from `len(rows)`, which only advances when a decision is *kept*, so the first
  skipped core made the next one reuse the same paths; `gcc -o` then rewrote a
  `.so` that a loaded `ctypes.CDLL` still had mmap'd. Overwriting a mapped file
  in place is a bus error, and it kills the interpreter with no traceback.
  Unlinking a mapped file would have been fine. Fixed with a monotonic counter.
  The diagnostic lesson: both runs died at the *same* core, which means
  deterministic, and one foreground run to capture the exit signal (135) was
  cheaper than the process-group theory it was first blamed on.

## Primary-source audit — the premise was ours, not egg's
Not an experiment. A verification of the claim every experiment from 003
onward was built on, prompted by asking what a reviewer would check that we
had not.

`research/findings/SELECTOR_GAP.md` framed the programme's opening as a gap the
upstream authors had identified and left open:

> egg's limitation field reads: **"extracted cost need not predict latency"**
> … both documents warn that the proxy does not track the physical quantity

**Both quotations are ours.** They are the `limitations` field of our own
prior-art cards — editorial compression we wrote — promoted into statements by
egg and Stitch.

Checked at source. **egg @`73975c9`** (2026-09-28), whole repository and
rustdoc: exactly **one** mention of cost beside any performance word, and it is
the verb "perform" — `src/extract.rs:51`, *"requires a cost function to
performs its greedy search"*. The `CostFunction` documentation covers the
`Cost` type's `PartialOrd` requirement, `NaN` panics, how to write a cost
function, the `AstSize`/`AstDepth` built-ins, and exactly one caveat: that
`AstSize` **"might overflow `usize`"**, so use `saturating_add` to stay
monotonic. An arithmetic caveat. Nothing about latency, runtime, or any
physical quantity. **Stitch @`350804b`**: every runtime and speed mention is
about *Stitch's own* search time against DreamCoder, plus a note that
`--max-arity` raises runtime. Nothing about whether learned abstractions
execute faster.

Unverified: both POPL papers. arxiv.org is blocked by this environment. But the
retracted sentence claimed *documentation*, and the documentation does not say
it.

### What this breaks and what it does not
The underlying claim is probably **true** — AST size does not track runtime,
and 004 measured exactly that. The empirical findings of 002–007 rest on our
own measurements and are untouched.

What falls is the *warrant*: the argument that this was a known, citable gap
its own authors had flagged, which is what made it look like an opening rather
than a hunch. It was a hunch. A good one, but ours, and it was carried through
four experiments and a research report as though someone else had said it.

The irony is on the record in 004: when finally measured, the structural proxy
turned out to be the **better** selector than measured per-operator cost. The
premise attributed to egg is one our own data partly contradicts.

### Two further holes found in the same pass
- **The screen has no floating-point prior art at all.** All 33 cards are
  incremental computation, build systems, e-graphs, synthesis and compression,
  while the corpus is FPBench/Herbie. Absent: OpTuner ("Choosing Function
  Implementations for Speed and Accuracy"), Herbie as prior art, Saiki,
  FPTuner, Daisy, Precimonious, FP-Salsa. The card titled "Salsa" is
  `salsa-rs`, the Rust incremental-computation crate — a **name collision**
  with the floating-point tool. Our own `CORPUS_MANIFEST.json` names
  Rosa/Daisy/Salsa/FPTaylor/Precimonious as corpus provenance and the screen
  never carried them over. We adopted the accuracy community's corpus while
  screening the incremental-computation community's tools. Tracked as
  `O-fp-prior-art`; if OpTuner already selects by measured speed and error on
  FPBench, this programme's novelty claim is gone.
- **The measurements cannot bear the weight put on them.** 004's headline is a
  p95 regret gap of 1.451 vs 1.517 — **4.5%** — from best-of-N `perf_counter`
  in a single process, with every noise floor measured back-to-back in that
  same process, which is the narrowest noise that exists. This machine has
  **no virtualised PMU** (`perf_event_open(PERF_TYPE_HARDWARE)` → ENOENT, no
  `cpu` node under `/sys/bus/event_source/devices/`), so hardware counters are
  permanently unavailable; and **no `cpufreq`, no `intel_pstate`**, so
  frequency and throttling are not merely uncontrolled but **unobservable**.
  Two zero-noise instruments are installed and unused: **llvm-mca 18.1.3**
  (host `sapphirerapids`) and **cachegrind 3.22** (deterministic `I refs`).
  Tracked as `O-measurement-validity`.

### Corrections applied
`SELECTOR_GAP.md` carries the retraction at the point of the claim. The two
card `limitations` fields in `PRIOR_ART.md`, `RESEARCH_INDEX.json` and
`RESEARCH_INDEX.csv` are annotated `[OUR INFERENCE, not stated by …]` with the
verified commit. `exp003_measured_cost_extraction.py`'s docstring, which quoted
both lines as upstream statements, carries the correction. The CSV is now
generated from the JSON rather than hand-synced, so those two copies cannot
diverge again.

## 008 — economic benefit beyond an optimised cache (the architecture's own claim)
**Why:** `research/benchmarks/NEXT_EXPERIMENT.md` had carried *"Status:
designed, not executed"* since import. Four of the six exit criteria depend on
it, and 001–007 all tested components rather than the thesis. This is the first
experiment in the programme to test the claim itself:

> Choosing among equivalent executable recipes and dependency reuse yields
> lower total cost than a strong existing optimized memoization baseline on
> related workloads.

**Workload:** 314 requests, seed 8008, Z/2^64 with `+ - *` only so every
identity is exact and "zero mismatches" is decidable. All five required case
types; 100 distinct syntax forms; two of five families held out. The decisive
cell is `equiv_form` — 70 requests where exact-key memoisation must miss and
normalisation should hit. Every variant was verified equivalent before entering
the workload, 0 of 70 rejected.

### Verdict against the design's own declared thresholds

| threshold | result |
|---|---|
| zero mismatches | **PASS** — all five arms, 0/314 |
| ≥10% total-time improvement on primary | **FAIL** — best baseline 1.09 ms against best normalising arm 45.37 ms, **−4080%** |
| ≤10% median regression on unrelated | **FAIL** — `memo_sympy` +443%, `memo_egglog` +29449% |
| within the declared 2 GB cap | PASS — 81 MB |
| persistent e-graph completed | **FAIL** — process aborted (SIGABRT) |

`NEXT_EXPERIMENT.md`'s own rule: *"Otherwise narrow or stop the claimed
advantage."* **The claimed advantage must be narrowed or stopped.**

### Why it lost, and it is not the obvious reason

| arm | executed | hits | norm cost | ops executed |
|---|---|---|---|---|
| 1 direct | 314 | 0 | — | 4,983 |
| 2 memo (exact key) | 244 | 70 | 0.2 ms | 3,849 |
| **3 memo_canon (free)** | **187** | **127** | **27 ms** | **2,866** |
| 4 memo_sympy | 174 | 140 | 377 ms | **8,612** |
| 5 memo_egglog | 210 | 104 | 1,964 ms | 3,536 |

**A free trick captured 81% of the prize.** Constant folding plus sorting
commutative operands — no algebra engine, no e-graph — converted 57 of the 70
equivalent-formulation misses into hits. SymPy bought the remaining 13 for 14x
the normalisation cost; egglog bought fewer for 73x. Arm 3 was not in the
design's arm list; it was added because working practice 2 demands the
strongest existing baseline, and it is the arm that beat the architecture.

**And normalisation made execution worse.** SymPy's expanded normal form
executes **8,612 operations against direct evaluation's 4,983** — 73% more
work. Net node growth across the workload was **+12,998**. So the mechanism
pays a large normalisation cost to produce a *more expensive* program.

### CORRECTION — the mechanism stated below was wrong
Raised by the user, not found by me: if the fancy arm is optimising for the
wrong thing, then "normalisation makes execution worse" is a fact about my
chosen normal form, not about the idea. **That objection is correct.**

`sympy.expand` produces a CANONICAL form, not a CHEAP one; expanding
`(a+b)*(c+d)` into four products is more work by construction. The
architecture's claim is *choose among equivalent recipes* — pick the cheapest.
I implemented *pick the canonical one* and then generalised from it.

The data separates the two, because egglog extracts the **smallest** term and
is therefore already cost-aware:

| arm | ops executed | vs direct | node growth |
|---|---|---|---|
| `memo_sympy` (expand) | 8,612 | 1.73x | **+12,998** |
| `memo_egglog` (smallest term) | 3,536 | **0.71x** | **−110** |

So normalisation does **not** inherently inflate the program. A cost-aware
normaliser shrinks it. Every sentence below that attributes the loss to
normalisation producing a more expensive program is **retracted**, and Y7's
note is wrong as written.

**The verdict is unchanged, for a better reason.** `memo_canon` — the free
trick — executes **2,866 operations, fewer than any other arm**, including the
cost-aware one at 3,536. So on this workload the algebra engine has no form
advantage to sell: constant folding plus sorting commutative operands already
finds the cheaper program. And it charges 73x the normalisation time (1,964 ms
against 27 ms) to deliver a form that is 1.23x worse. Recomputing the sweep
against the cost-aware arm rather than `expand`: egglog is 1,910x, 296x, 44.5x,
7.31x, 1.87x, 1.29x of the best baseline across 0 to 10,000 µs/op, converging
to its 1.23x operation-count ratio. **No break-even at any cost, because its
form is worse than the free trick's, not because normalisation inflates
anything.**

### The prediction that missed, and it missed downward
Y7 asked where the break-even lies if operations cost more than integer
arithmetic — the scaling that was supposed to rescue the mechanism. Predicted
≥100 µs/op. **There is no break-even at any cost.** The ratio of
`memo_sympy` to the best baseline plateaus:

| op cost | 0 µs | 1 µs | 10 µs | 100 µs | 1 ms | 10 ms |
|---|---|---|---|---|---|---|
| ratio | 64.1x | 10.0x | 3.43x | 2.96x | 2.99x | **3.00x** |

The curve converges to the operation-count ratio and stops. **Expensive
operations cannot save this mechanism** — but see the correction above for
*why*: not because normalisation inflates the program (false in general; true
only of `expand`), but because the free canonicalisation already produces the
cheapest form of any arm, so there is no form advantage left for an algebra
engine to win back at any operation price.

### The feasibility finding
The architecture's own description is accumulating structure, so the faithful
arm is **one persistent e-graph** asked whether each new request is already
equal to something it holds. A fresh e-graph per request cannot do the job at
all: egglog *proves* `a*b == b*a` yet extracts different representatives from
two separate e-graphs, so it yields no cache key.

The persistent version does not run. With ring axioms including distributivity
and i64 constant folding it exhausts memory hard enough that the Rust side
aborts the interpreter. Budget probe on **six two-term expressions**:

| saturation iterations | outcome |
|---|---|
| 1 | survives, fails to prove `2x+3x == 5x` |
| 2 | survives, canonicalises all three pairs, 11 ms |
| 3 | survives, 120 ms |
| 4 | **memory exhausted** |

At 2 iterations it works on six expressions and still aborts on 314. So there
is a narrow band where the accumulating e-graph both canonicalises and fits,
and this workload is already outside it.

### Predictions vs actual — 8 of 9
| | prediction | actual | verdict |
|---|---|---|---|
| Y1 | zero mismatches | 0/314, all arms | hit |
| Y2 | arm 2 avoids 70–75 | exactly 70 | hit |
| Y3 | free canonicalisation takes ≥50% of equiv_form | **81%** | hit |
| Y4 | **no arm reaches +10% on primary** | **−4080%** | hit |
| Y5 | arms 4/5 >10x slower than arm 3 | 11.3x and 57.6x | hit |
| Y6 | arms 4/5 regress >10% on unrelated | +443%, +29449% | hit |
| Y7 | break-even ≥100 µs/op | **no break-even exists** | **miss, downward** |
| Y8 | adversarial blow-up | +12,998 nodes; 117 egglog skips | hit |
| Y9 | arm 3 retains ≥10% fewer entries | 23% fewer | hit |

### Where this leaves the architecture
On its own declared workload, against the strongest free baseline, the
mechanism loses by three orders of magnitude and cannot be rescued by making
operations expensive. That is a real answer to the thesis, not a null result.

It also closes a loop with 003–007. The one thing that could stop normalisation
making execution worse is **cost-aware** extraction — choosing a cheap
representative rather than a canonical one. That is exactly what 003–007
studied, and they found it is barely better than counting nodes (004) and
unaffordable where candidates must be compiled (007). The component line and
the architecture line meet here, and both say the same thing: the selection
machinery is not where the value is.

### Honest limits
One workload, specified by the design: integer arithmetic over Z/2^64 with
`+ - *`. SymPy's `expand` is one normal form and a deliberately canonical one;
a cost-aware or factored normal form would execute better, and that variant is
untested. The persistent e-graph was run with one axiom set — dropping
distributivity makes it fit but then it cannot prove the equivalences that
matter. `stitch` (arm 6) was declared not run: optional in the design and not
installed. Transferred bytes are reported but near-meaningless here, because an
integer result is smaller than any descriptor of it; that term only bites on
workloads where the artifact is large, which is the v1 sync case rather than
this one.

## 009 — the crossover benchmark: the first positive result for the actual thesis
**Why:** 002–008 tested tactics inside the thesis. DR-001 identified the real
gap — a general selector across transfer / delta / recompute / cache — and said
*benchmark before building it*, because rsync might already capture the value.
This is that benchmark, and the first experiment to test the thesis itself.

**Corpus:** 72 real local items across four regimes — 20 photogen JPEGs
(recompute), 24 consecutive git versions of repo text (delta), 14 source files
(compressible), 8 held files (cache), 6 random/`.gz` (incompressible). Bytes is
the primary metric; receiver compute is a declared budget swept 0–10 s (GIR §3,
units kept separate). No rsync binary here, so the Tridgell–Mackerras
block-delta was implemented directly.

### The result
**The generalized selector beats rsync by 4.0x on this workload, and the entire
margin is the recompute regime.** At a 1 s compute budget:

| policy | bytes | vs selector |
|---|---|---|
| always-transfer | 2,418,637 | 4.1x |
| always-delta (rsync) | 2,350,382 | 4.0x |
| **selector** | **582,958** | — |
| selector **without** recompute | 2,255,789 | within **4%** of rsync |

Remove the recompute arm and the selector collapses to within 4% of rsync. So
the 4x margin is **structural, not tuning**: rsync cannot exploit "B can
regenerate X," because it needs a *similar file* at B, and a freshly generated
JPEG has none. The dial is real per regime — cache 32 B when B holds X,
**recompute 59 B for an 86 KB photo (1464x)**, delta 42% on versioned text,
transfer everywhere else.

**The boundary held exactly.** On incompressible data (random bytes, the `.gz`
artifacts) no mechanism beat transfer by more than 0.0% — GIR §6 observed, not
assumed. Recompute was byte-exact on all 20 photos; 0 disqualified.

### Predictions — 5 of 7
| | prediction | actual | verdict |
|---|---|---|---|
| Z1 | all four mechanisms used | cache/delta/recompute/transfer all pick | hit |
| Z2 | selector ≤10% of transfer (≥10x) | 4.1x | **miss, corpus mix** |
| Z3 | **≤50% of rsync AND margin is all recompute** | 0.248 of rsync; 0.96 without recompute | **hit** |
| Z4 | at T=0 within 5% of rsync | 1.029 | hit (artifact) |
| Z5 | incompressible: nothing beats transfer >5% | 0.0% | hit |
| Z6 | 0 recompute disqualified | 0/20 | hit |
| Z7 | per-file compute break-even varies ≥10x | 1.87x | **miss, by design** |

Z2 missed because the aggregate reduction depends on how much of the pile is
regenerable — 20 of 72 here gives 4x, though per-photo recompute is 1464x. Not
a weaker mechanism; a smaller regenerable fraction than 10x needs. Z7 missed by
corpus design: all photos were one fixed size, so regen *time* barely varied
(the *byte* crossover is enormous). Z4 is a T=0 artifact — at literally zero
budget even delta/cache are inadmissible (nonzero apply/hash), so the selector
drops to transfer; the clean null holds at T=1 ms (0.960).

### The caveat that bounds the result
**The selector here had oracle knowledge of B's state** — which files B can
regenerate, has a related version of, or holds exactly. A deployable selector
must *discover* that cheaply, and that discovery cost is not measured here. So
4x is an **upper bound under free perfect knowledge of B**. DR-001's P1 question
— "can receiver resource discovery be performed cheaply enough to justify
mechanism selection?" — is now the binding next question. The structural finding
(recompute is a regime rsync cannot reach, and a selector captures it) does not
depend on the oracle; the 4x magnitude does.

### What this does to the programme
First positive, pre-registered evidence that the generalized dial beats the best
single existing tool, for a structural reason. DR-001 said benchmark before
building; the benchmark says the recompute regime is real and rsync-proof.
`O-selection-layer` is now justified — conditional on the discovery-cost
question. The thesis (`O-bet`) has its second supporting data point, and unlike
the v1 sim this one isolates *why*: not compression, not sync — regeneration of
deterministic artifacts from recipes the receiver can run.

### Honest limits
Single machine; synthetic (but byte-exact, real-generator) photos; the 4x
aggregate is corpus-specific; discovery cost unmeasured (oracle B-state);
delta is a reimplementation, not the rsync binary - and reading rsync at source (research/TOOL_MECHANICS.md) later showed it is non-rolling and omits run-length token encoding, so it is mildly UNFAIR to rsync in the delta regime; the recompute-driven headline is unaffected; compute budget is
wall-clock on a shared container. The structural claims are robust; the
magnitudes are this-corpus-this-machine.

## 010 — does discovery eat the 4x? (no — and the real gate is provenance)
**Why:** 009's selector beat rsync 4x with oracle knowledge of B's state. The
binding question (DR-001 P1): can that state be discovered cheaply enough to
keep the gain? Reuses 009's per-item costs; charges each policy its own
discovery; separates the discovery *message* from *provenance* (whether A kept
the recipe).

### The gate held. 5 of 5 predictions hit.

| provenance p | selector/rsync | beats rsync | picks |
|---|---|---|---|
| 0.00 | 0.960 | 1.04x | no recompute → ≈ rsync |
| 0.50 | 0.628 | 1.59x | recompute 9 |
| 1.00 | **0.248** | **4.03x** | recompute 20 |

- **The discovery message is 272 bytes — 0.012% of the payload.** B advertising
  its content hashes and installed generators is negligible. (rsync's own
  signature cost is already inside the delta bytes; the manifest is the
  selector's only *extra* discovery, and it is nothing.)
- **The 4x survives discovery intact** at full provenance (V2, the kill
  condition): 4.03x after the manifest is charged.
- **The binding constraint is provenance, not message cost** (V4): varying p
  moves the result by 1,672,831 bytes; the manifest is 272. Provenance has
  **6,150x more leverage** than the discovery message.

### The reframe this establishes
"Can we discover B's state cheaply?" — yes, trivially. The real question was
never a runtime message. It is **did the sender keep the recipe** — provenance
coverage `p` — and the win scales with it: p=0 reverts to rsync, p=1 gives the
full 4x, roughly linear between. That is not a networking cost; it is an
architecture discipline, and it is **the project's founding premise** ("keep the
generator, don't throw it away") now measured as the actual gate.

So the deployability question resolves cleanly: the selector is deployable, its
discovery overhead is negligible, and its value is bounded by how disciplined
the system is about retaining the generative processes of the objects it sends.

### The frontier this opens (the real-world analog of 004's frequency question)
`p` is a free parameter here. The unmeasured real-world quantity is: **of the
objects a real system transfers, what fraction were produced by a deterministic
process whose recipe the sender could retain?** 009 used a corpus 28% generated.
If real workloads are 2% generated, the dial is a niche win; if 50%, it is
large. This is exactly the shape of 004's "how often is structural cost wrong" —
an existence-and-magnitude result here (the mechanism works, 4x at p=1), with
the frequency on unpicked real workloads still open. Tracked as `O-provenance-freq`.

### Honest limits
Inherits 009's (single machine, synthetic-but-byte-exact photos, faithful not
binary rsync). The provenance model is a coin flip at rate p, not a real
retention policy; a real sender's `p` is correlated with object type (generated
files have recipes, scanned/authored ones do not), which this does not model.
The manifest model assumes B can enumerate its state cheaply; for enormous
inventories the content-hash set grows and would need a sketch (IBLT, already
carded) — untested at scale here.
