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
