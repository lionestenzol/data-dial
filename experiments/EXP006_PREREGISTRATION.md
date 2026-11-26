# Experiment 006 — pre-registration

Committed **before any new timing was collected**.

## The question

005 recommended dropping measured costing, but every break-even in it assumed
one fixed oracle price: best-of-11 timing of every admitted candidate, 30.454
ms per decision. That price is a design choice, not a fact. HANDOFF's
follow-up C:

> One timing pass instead of eleven would cut the oracle ~11x, taking the best
> cheap rule from 854.8 requests to roughly 78 and perfect detection to ~11.
> The catch is that a cheap oracle is a noisy oracle and may pick the wrong
> candidate, and 004 recorded only best-of-11 minima, so a noisy oracle's pick
> quality cannot be recovered from the existing data.

So this run records **every repeat time per candidate**, and asks what the
cheapest sufficient oracle is.

## Two ways to cheapen an oracle

1. **Fewer repeats.** Oracle cost is linear in the repeat count R. Simulate
   best-of-R for R ∈ {1,2,3,4,6,8,12,24} at the deployed array size.
2. **Smaller probe arrays.** Time candidates at m ∈ {256, 1024, 4096} and use
   that ranking to choose for the deployed size of 16384. Much cheaper per
   evaluation, but the ranking has to transfer across a cache/overhead regime
   change.

## Measurement design

48 individual timings per candidate at the deployed size M=16384, assigned
**alternately** to a simulation pool and a truth pool (even indices simulate,
odd indices define truth) so the two are disjoint and neither is biased by
drift in CPU frequency or cache state over the run. Truth for a decision is
the candidate minimising its truth-pool minimum. Simulated best-of-R draws the
first R samples of the simulation pool, which is what actually running R
repeats would give. Probe sizes get 12 samples each, same alternating scheme.

Policy under test remains 004's best cheap arm: `ast_size`, tree counting.
Oracle cost is charged as evaluation time only — R × per-evaluation time summed
over admitted candidates — matching 004 and 005 so the numbers are comparable.

## The hinge

**V2 is the crux.** Noisy oracles mis-pick among near-ties, and near-ties are
by definition the decisions with little waste to lose. If waste recovered holds
up as R falls, cheapening by repeats works and 005's recommendation reverses.
If it does not, the recommendation stands and this line is closed for good.

## Predictions

| | prediction |
|---|---|
| **V1** | Oracle cost is linear in R: cost(R)/cost(1) within 10% of R for all R ≤ 24. |
| **V2** | **Hinge.** Waste recovered at R=1 is ≥ 90% of waste recovered at R=24. Oracle noise hurts most where it matters least. |
| **V3** | Mis-picks are nevertheless common: at R=1 the oracle picks a non-best candidate on ≥ 20% of decisions. Together with V2 this says mis-pick *rate* is the wrong metric and recovered waste is the right one. |
| **V4** | With an R=1 oracle, break-even is ≤ 20 requests under perfect targeting and ≤ 100 under 005's best cheap rule (`dag_vs_tree`). |
| **V5** | Size reduction transfers poorly: at m=256 with R=12, waste recovered is ≤ 70% of the m=16384 R=12 value, because at 256 elements per-call overhead dominates and the ranking collapses toward node count. |
| **V6** | The cheapest configuration passing the 200-request bar with the best cheap rule uses R ≤ 3 at full array size — repeat reduction rescues the mechanism, size reduction does not. |
| **V7** | **At R=1, flagging everything breaks even in ≤ 150 requests**, so a sufficiently cheap oracle makes targeting unnecessary and 005's detector problem stops mattering. |

## What each outcome means

- **V2 and V7 hold**: the correct conclusion is not "target the tail better"
  but "make the oracle cheap and apply it everywhere". 005's detector failure
  becomes irrelevant rather than fatal, and the standing recommendation to drop
  measured costing is **reversed**, with the operating point stated.
- **V2 fails**: pick quality degrades faster than price, there is no cheap
  sufficient oracle, and measured costing is closed — 005's recommendation
  stands as final.
- **V5 fails in the optimistic direction** (small probes transfer fine): the
  oracle gets cheaper than repeat reduction alone allows, and the right design
  is to rank on small arrays and run on large ones.

## Known bias being guarded against

004 and 005 each missed by over-crediting the mechanism this programme is
invested in. V4 and V7 are optimistic predictions, which is the direction this
assistant errs, so they are stated as arithmetic with an explicit hinge: they
follow almost mechanically **if** V2 holds, and V2 is the one being tested.
V3 is included precisely because a high mis-pick rate would look like failure
while costing nothing, and the reverse mistake — reading mis-pick rate as
damage — is the kind of metric substitution HANDOFF warns this assistant about.
