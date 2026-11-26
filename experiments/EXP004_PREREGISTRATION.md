# Experiment 004 — pre-registration

Committed **before the first full run**. No regret number has been looked at.
Harness development used a `--probe` mode that prints coverage, timing cost and
the noise floor and deliberately prints no arm comparison.

## The question

HANDOFF.md, after 003:

> How often is structural cost wrong on a workload nobody picked in advance?

003 showed structural cost can be 94x worse than optimal, in a domain *chosen*
so the proxy had to fail. That is an existence proof. This is the frequency
question, and it is designed so the answer can be "rarely, so the mechanism is
niche."

## Setup, fixed in advance

| Thing | Value |
|---|---|
| Corpus | 913 FPCores, FPBench @090d8198 + Herbie bench @884621aa, pinned by SHA256 |
| In scope | 802 (111 excluded: array/tensor 38, if 18, user-defined calls 17, while 21, ref 6, oversized 7, other 4) |
| Candidates | SymPy `simplify, expand, factor, together, cancel, powsimp, radsimp, logcombine, trigsimp, horner` + integer-power expansion, applied to each distinct form |
| Admission | relative error vs a 30-digit reference ≤ `1e-6` at every valid sample point, 32 points |
| Timing | 16384 float64 (L2-resident vectorised NumPy), best of 11 |
| Noise floor | measured before predictions: p50 1.004x, p95 1.024x, max ~1.08x on re-timing the same candidate |
| Near-optimal | regret ≤ 1.05, i.e. at or below the noise max |
| Arms | `ast_size` (all weights 1), `static_weight` (textbook latencies, fixed in the source, never tuned), `measured` (per-operator microbenchmark on this machine, one calibration amortised over the corpus), `oracle` (time every candidate) |
| Counting | DAG primary (continuity with 003's `DagCostModel`), tree reported beside it |
| Seed | 4004 |

Three facts about the machine were measured during harness development and are
stated here because they shape the predictions:

- NumPy computes `a**2` in 3.2 µs but `a*a` in 7.2 µs, while `a**3` takes
  41.9 µs against 14.6 µs for `a*a*a`. A single `pow_int` weight is therefore
  wrong at one end of the exponent range **by construction** — the 003
  phenomenon, arising in a corpus nobody selected for it. The measured arm
  calibrates at operator granularity, so this defeats the measured arm too.
- `lambdify` performs no CSE: it emits `(sin(x)+1)*(sin(x)+2)` literally and
  NumPy evaluates `sin(x)` twice (228.8 µs against 118.5 µs with CSE). The
  tree count is the faithful model of this backend; the DAG count
  under-charges shared work.
- Runtime is close to linear in operator count including temporaries
  (`a+b` 6.8 µs, `((a+b)+a)+b` 20.1 µs), so an additive per-operator cost
  model is a reasonable shape here.

## Predictions

Scored hit/miss with the **sign** of each miss, per working practice 1.

| | prediction |
|---|---|
| **T1** | Decision coverage: ≥ 400 of the 802 in-scope cores yield ≥ 2 admitted candidates. |
| **T2** | **Structural cost is usually fine.** `ast_size` p50 regret ≤ 1.05 — at the median, counting nodes is not measurably worse than optimal. |
| **T3** | **But it has a real tail.** `ast_size` p95 regret ≥ 1.25 and max ≥ 2.0. |
| **T4** | **The headline frequency.** Fraction of decisions where `ast_size` regret ≥ 1.5 falls in **2%–25%**; point estimate **10%**. |
| **T5** | **A good static table captures most of the available gain.** `static_weight` p95 < `ast_size` p95, and `measured` p95 improves on `static_weight` p95 by **less than 1.20x**. Measuring buys little over a textbook table on this corpus. |
| **T6** | **No arm matches the oracle often.** `measured` picks the oracle's form on **< 90%** of decisions, against 003's 10/10, because a per-operator additive model cannot represent exponent-dependent power cost, allocation, or absent CSE. |
| **T7** | **Counting granularity rivals the weight vector.** Tree counting beats DAG counting on p95 regret for at least two of the three arms; specifically tree-`measured` p95 < DAG-`measured` p95. |
| **T8** | **The exponent-2 inversion hits every arm.** On decisions containing a squared power-expansion candidate, all three arms match the oracle *less* often than on decisions without one. |
| **T9** | **Calibration amortises, the oracle does not.** The ~14 ms calibration is repaid within 50 decisions (003's per-n calibration never repaid above n=256). The oracle's own timing cost per decision exceeds the best form's runtime by > 10x, so the oracle is not a deployable policy. |
| **T10** | **Power expansion is not what produces the result.** With power expansion removed, the ordering survives: `ast_size` p50 still ≤ 1.05 and its p95 still ≥ `static_weight` p95. If this fails, the headline is an artifact of the one transform we added by hand. |

## What each outcome means

- **T2 and T4 both hold at the low end** (say ≤ 5% of decisions materially
  wrong): structural cost is fine in practice, 003 was a curiosity, and
  measured costing should be scoped to declared-uncertain operators or
  dropped. The architecture must say so.
- **T4 lands high** (≥ 20%): the 94x case is not exotic, and measured costing
  earns a place in the resolution policy.
- **T5 fails in the direction of `measured`** (large margin over the static
  table): measurement is doing real work, not just correcting magnitudes.
- **T5 holds and T6 holds**: the honest reading is that neither a static nor a
  measured per-operator model is good enough, and the interesting variable is
  cost-model *granularity*, not whether the numbers were measured. That would
  redirect the programme.

## Known bias being guarded against

HANDOFF.md records that this assistant's prediction errors share a direction:
over-optimism about when a mechanism starts paying, and collapsing the big idea
into whatever is easiest to measure. T2, T5 and T6 are deliberately framed
*against* the programme's thesis for that reason. T10 exists because power
expansion is the one transform added by hand, and it is exactly the sort of
addition that would manufacture the desired result.
