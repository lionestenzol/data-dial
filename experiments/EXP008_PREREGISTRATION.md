# Experiment 008 — pre-registration

Committed **before any arm is implemented and before any measurement**, as
`research/benchmarks/NEXT_EXPERIMENT.md` requires: *"Before implementing this
benchmark, commit numerical predictions for every arm."*

Closes `O-007-prereg`'s successor for this line. Objective under test:
**`O-memo-baseline`** — four of the programme's six exit criteria depend on it,
and it is the first experiment in this programme that tests the architecture's
own claim rather than a component of it.

## The claim being tested

From `NEXT_EXPERIMENT.md`:

> Choosing among equivalent executable recipes and dependency reuse yields
> lower total cost than a strong existing optimized memoization baseline on
> related workloads.

## Workload (built, not yet measured against)

`experiments/exp008_workload.py`, seed 8008, 314 requests. All arithmetic over
**Z/2^64 with `+ - *` only** — division, shifts and bitwise operations are
excluded because they would break the ring identities the
algebraically-equivalent cases rely on. Over this ring every identity used is
exact, so "zero mismatches" is decidable rather than a tolerance.

| case | n | what it tests |
|---|---|---|
| `exact_repeat` | 140 | plain memoisation hits |
| `changed_leaves` | 70 | same shape, new values — nobody should hit |
| **`equiv_form`** | **70** | **different syntax, same value — the decisive cell** |
| `unrelated` | 28 | the regression workload: normalisation overhead undiluted |
| `adversarial` | 6 | products of 7 binomials, expanding to 128 terms |

100 distinct syntax forms across 314 requests. Five families; `repeated_square`
and `mixed_chain` appear **only** in the held-out split, so evaluation is not
on cosmetic variants. Every `equiv_form` variant was verified equivalent to its
origin by exact evaluation on random inputs before entering the workload — 0 of
70 rejected.

## Arms

| arm | description |
|---|---|
| 1 `direct` | evaluate every request, no cache |
| 2 `memo` | cache keyed on (exact syntax, env) — plain result memoisation |
| 3 **`memo_canon`** | **constant-fold + sort commutative operands, then key. THE STRONG BASELINE** |
| 4 `memo_sympy` | SymPy simplify/CSE normalisation, then key |
| 5 `memo_egglog` | egglog equality saturation + extraction, then key |
| 6 `stitch` | **not run.** Optional in the design, and `stitch-core` is not installed. Declared, not silently skipped. |

Arm 3 is not in `NEXT_EXPERIMENT.md`'s list. It is added because working
practice 2 says *"the baseline must be the strongest existing tool, not a naive
one"*, and constant folding plus commutative sorting is free, standard, and
captures some algebraic equivalence without any of the architecture's
machinery. Leaving it out would have let arms 4 and 5 beat a straw man — the
mistake the v1 document result already taught this project once, when rsync
turned out to match the dial.

## Costs charged

Execution time, normalisation/optimisation time, cache lookup and hashing,
retained cache entries and their serialised bytes, descriptor bytes against
result bytes, peak RSS, and primitive operation counts. Cold start reported
separately. **Memory cap declared in advance: 2 GB peak RSS; any arm exceeding
it is reported as failed rather than tuned.**

Primitive operation count is the noise-free metric and is reported alongside
time, because this machine has no PMU and unobservable CPU frequency. Wall time
is still the metric the threshold is stated on.

## Decision thresholds, from NEXT_EXPERIMENT.md

- **zero mismatches**
- **≥10% total-time improvement** over the best applicable baseline on the
  declared primary workload
- **≤10% median regression** on the unrelated workload
- declared memory cap

> "Otherwise narrow or stop the claimed advantage."

## Predictions

| | prediction |
|---|---|
| **Y1** | Zero mismatches: all five implemented arms return bit-identical results on all 314 requests. |
| **Y2** | Arm 2 avoids re-execution on 70–75 requests (the exact repeats) and no more. |
| **Y3** | **Arm 3, which is free, captures ≥50% of the `equiv_form` misses arm 2 suffers.** Most of the available win needs no architecture. |
| **Y4** | **THE HEADLINE. No normalising arm reaches ≥10% total-time improvement over the best of arms 1–3 on the primary split.** The declared threshold is not met and the claimed advantage must be narrowed or stopped. |
| **Y5** | Arms 4 and 5 are **>10x slower** in total time than arm 3, because normalisation costs milliseconds per request while execution costs microseconds. |
| **Y6** | On the unrelated split, arms 4 and 5 regress **>10%** in median latency against arm 2, violating the declared regression threshold. |
| **Y7** | **The useful number.** The break-even cost per primitive operation at which arm 4 beats arm 3 is **≥100 µs/op** — four or more orders of magnitude above real integer arithmetic. |
| **Y8** | On the 6 adversarial requests, at least one of arms 4/5 times out or yields a normalised expression ≥10x the input node count. |
| **Y9** | Arm 3 retains **≥10% fewer** cache entries than arm 2, because canonicalisation merges keys. |

## What each outcome means

- **Y4 holds** (expected): the architecture does not beat a strong memoisation
  baseline on this workload, and `NEXT_EXPERIMENT.md`'s own rule says to narrow
  or stop the claim. Y7 then says *what would have to be true* instead: the
  mechanism needs operations expensive enough that avoiding execution pays for
  normalising. That is a scoping result, not a dead end, and it is the honest
  version of the architecture's claim.
- **Y4 fails** — a normalising arm clears 10%: the architecture's central claim
  gets its first supporting measurement, four exit criteria move, and the
  programme has a result worth defending.
- **Y3 fails** (cheap canonicalisation captures little): algebraic
  normalisation is doing real work that free tricks cannot, which strengthens
  the case for the machinery even if Y4 still fails on time.
- **Y1 fails**: an arm is not semantics-preserving. That is a correctness bug
  and outranks every economic question here.

## The honest risk in this design, stated up front

Integer arithmetic over Z/2^64 executes in **microseconds**. Normalisation
costs **milliseconds**. On that ratio no normalising arm can pay for itself,
and Y4 is close to arithmetic rather than a genuine open question — the
workload may doom the mechanism by construction. `NEXT_EXPERIMENT.md`
nevertheless specifies this workload, so it is run as written rather than
quietly replaced.

Y7 is what makes the experiment worth running anyway: by scaling the cost of a
primitive operation and finding where arm 4 overtakes arm 3, the result becomes
*"recipe normalisation pays when operations cost more than X"* instead of
*"recipe normalisation lost on cheap arithmetic"*. If X lands near real costs
for expensive operators — image decode, model inference, compilation, network
retrieval — the architecture has a domain. If X is absurd, it does not.

## Known bias being guarded against

Across 004–007 this assistant's prediction errors clustered wherever a
quantity had never been measured. The never-measured quantity here is the
**ratio of normalisation cost to execution cost**, which is exactly what Y5 and
Y7 pin down. Y3 and Y4 are both framed so that the programme's own thesis is
the thing that fails, because the prior four experiments all ran the other way.
