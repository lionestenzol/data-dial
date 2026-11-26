# Experiment 005 — pre-registration

Committed **before any predicate was evaluated**. Setup facts below were
measured first (positive-class sizes, waste concentration, group structure);
they are declared as setup, not claimed as predictions, because they were seen
during feasibility checking.

## The question

004 answered the frequency question: structural cost is optimal at the median
and materially wrong on 4.3% of decisions. HANDOFF's follow-up A:

> The whole value of measured costing now rests on a small fraction of
> decisions. A mechanism that is wrong 4% of the time is worth having only if
> you can tell *which* 4% without paying the oracle's 162x.

If no cheap predicate separates the tail, measured costing cannot be targeted
and should be **dropped** from the resolution policy, not merely scoped.

## Setup facts, measured before predictions (not predictions)

Policy under test is 004's best cheap arm: `ast_size`, tree counting.

| regret ≥ | decisions | share | share of all waste |
|---|---|---|---|
| 1.1 | 77 | 14.3% | 96.1% |
| 1.2 | **52** | 9.6% | **87.8%** |
| 1.3 | 27 | 5.0% | 86.0% |
| 1.5 | 20 | 3.7% | 83.1% |
| 2.0 | 12 | 2.2% | 72.1% |

Waste is strongly concentrated, which is what makes targeting conceivable.

Primary target is **regret ≥ 1.2**: 52 positives, holding 87.8% of all waste,
and above the measured timing-noise p99 of 1.123. The ≥1.5 threshold is
reported as a secondary with an explicit small-n caveat — 20 positives cannot
support a stable precision estimate.

539 decisions span 67 source files, very unevenly (`haskell.fpcore` alone
holds 188). Evaluation is therefore **grouped 5-fold cross-validation with
whole files assigned to folds**, balanced by decision count, so a held-out
case is never a cosmetic variant of a training one. Threshold parameters are
fit on training folds only.

## Predicates — all computable from the candidate ASTs with zero timing

| name | fires when |
|---|---|
| `disagree_ast_static` | ast_size-tree and static-tree pick different candidates |
| `disagree_ast_meas` | ast_size-tree and measured-tree pick different candidates |
| `disagree_any` | any two of the three tree models disagree |
| `dag_vs_tree` | ast_size picks differently under DAG than under tree counting |
| `sq_powexp` | some candidate contains an `x*x` from power expansion |
| `pow_gen` | some candidate contains a general (non-integer) power |
| `near_tie(τ)` | best and second-best predicted cost differ by < τ relative |
| `spread(θ)` | max/min predicted cost across candidates exceeds θ |
| `many_cands(k)` | admitted candidate count ≥ k |
| `combined` | logistic regression over all of the above, fit on train folds |

`sq_powexp` is informed by 004's T8 result and is declared as a 004-derived
prior, not a discovery of 005. Six specific worst-case expressions were seen
during 004's analysis; they are 6 of 539 and are left in.

## Economics, and why precision is not the figure of merit

Flagging a decision means paying the oracle on it: timing every admitted
candidate, 30.454 ms on average against 0.1878 ms to simply run the best form.
Paying that once per *expression* and reusing the choice across requests gives
a break-even request count, the idiom 002/003 already use:

> **break-even = Σ(oracle cost over flagged) / Σ(waste recovered over flagged)**

Flagging a decision recovers **all** of its waste, whatever its regret. So the
detector's real job is to maximise waste recovered per oracle-millisecond
spent, and a detector with poor precision fails by spending oracle budget on
decisions that had little waste to recover. Precision and recall are reported,
but break-even is the decision criterion.

**Ship criterion, fixed in advance:** targeted measurement is worth keeping
only if the best detector reaches a break-even of **≤ 200 requests per
expression** while flagging **≤ 20%** of decisions. Otherwise the honest
recommendation is to drop measured costing from the resolution policy.

## Predictions

| | prediction |
|---|---|
| **U1** | Best *single* predicate reaches precision ≤ 0.35 at recall ≥ 0.5 on held-out folds. The tail is not cleanly separable by one cheap signal. |
| **U2** | `disagree_*` beats `sq_powexp` on held-out precision at matched recall. Model disagreement carries more information than the one operator family 004 identified. |
| **U3** | `combined` beats every single predicate on held-out AUC, but its held-out precision at recall 0.5 is still **< 0.5**. |
| **U4** | Overfitting is detectable: held-out precision for tuned-threshold predicates falls **≥ 15% relative** below train precision. |
| **U5** | **Even a perfect detector needs > 100 requests per expression to break even**, because the oracle's own cost dominates the waste it recovers. |
| **U6** | The best realistic detector's break-even is **1.5x–10x worse** than perfect detection's. |
| **U7** | At a ≤ 20% flagging budget, recall ≤ 0.75 and residual waste ≥ 25% of the original. |

## What each outcome means

- **U5 holds and the ship criterion fails**: the oracle is too expensive to
  target, not merely too expensive to apply everywhere. Measured costing
  should be dropped from the resolution policy, and the remaining open
  question is whether a *cheaper* oracle (fewer repeats, smaller arrays)
  changes the arithmetic — which this experiment cannot answer, because 004
  recorded only best-of-11 times and a noisy oracle's pick quality is not
  recoverable from them.
- **Ship criterion passes**: targeted measurement survives as a tail-risk
  mechanism with a stated operating point, and the architecture keeps it with
  the flagging rule attached.
- **U1 fails in the optimistic direction** (a single predicate separates the
  tail cleanly): the mechanism is simpler than expected and the predicate
  itself is the contribution.

## Known bias being guarded against

004's three misses all ran one way — over-crediting the mechanism this
programme is invested in — and T10 was written so that another prediction's
assumption was buried inside it. U1, U3, U5 and U7 are therefore all framed
pessimistically, each depends on exactly one claim, and scoring is again done
by a script that reads the results file rather than by reading numbers and
narrating.
