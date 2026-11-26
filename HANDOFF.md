# Handoff

Read this first. It is the state of the work, what is proven, what is not,
and the one experiment that comes next.

## What the project is

An architecture where you send the **recipe** for something instead of the
thing, and the far side makes it locally. Not compression (nothing gets
squeezed), not sync (files are incidental), not caching (nothing has to
repeat). The bet is that almost everything was *generated* by some process,
that process is usually thrown away, and keeping it instead is worth more
than hunting for duplicate bytes.

Two background documents, both written in this project:
- Architecture comprehension: https://claude.ai/artifact/A1jGjw47Qgm2tg9TcAYpPv
- Substrate economics programme: https://claude.ai/artifact/HZivebhPo4JPsuy9bWcvVh

## Where things are

| Path | What |
|---|---|
| `dial/`, `dial_sim.py`, `tests/` | v1 sync simulator — the first day's task, finished |
| `RESULTS.md` | its 7-day run |
| `research/` | prior-art registry: 33 cards, capability matrix, gap list, verification ledger |
| `research/findings/SELECTOR_GAP.md` | the key literature finding |
| `research/findings/INDEPENDENT_RERUN.md` | the bundle's smoke test, re-run here |
| `experiments/FINDINGS.md` | experiment log, 002 / 002b / 003 / 004 / 005 |
| `experiments/EXP004_PREREGISTRATION.md` | 004's ten predictions, committed before the run |
| `experiments/EXP005_PREREGISTRATION.md` | 005's seven predictions, and its ship criterion |
| `bench/corpus/`, `bench/fetch_corpus.sh` | 004's corpus (gitignored; rebuild from pinned SHAs) |
| `research/benchmarks/CORPUS_MANIFEST.json` | corpus provenance + SHA256 |
| `.venv-research/` | Python env with egglog, redun, wasmtime, stitch-core (gitignored) |

Run experiments with `.venv-research/bin/python -I experiments/<file>.py`.
The venv was relocated, so its scripts' shebangs are broken — use
`python -m pip`, not `pip`.

## What is actually established

**Verified here, by running it:**
- v1 sync sim: 78.57 MB against 284.83 MB full sync and 282.88 MB rsync over
  8 days, 0 checker failures in 414 messages, 10/10 tests pass.
- egglog + redun + Wasmtime interoperate: three forms of `x+5` collapse to one
  Wasm module and one execution where the unnormalised baseline takes three.
  Reproduced on Python 3.13.18 against the bundle's 3.12.14.
- **Experiment 003** — structural cost can be 94x wrong. AST-size extraction
  can never choose the FFT convolution route (more nodes), so it is 94x
  slower than optimal at n=8192. One static weight table is wrong at one end
  of the range by construction. Measured per-machine costs match the oracle
  10/10. All six pre-registered predictions hit.
- **Experiment 004** — the frequency question, answered. 539 decisions over
  802 in-scope FPCores from FPBench and Herbie, suites assembled by the
  floating-point accuracy community years before this project. Structural
  cost is **exactly optimal at the median** and materially wrong (≥1.5x) on
  **4.3%** of decisions, worst case 48.30x. 7 of 10 predictions hit.
- **Experiment 005** — the targeting question, answered, and it closes the
  line. The 4.3% tail cannot be flagged economically. Best cheap rule needs
  **854.8 requests per expression** to repay, against **1216.9** for not
  targeting at all and a pre-registered bar of 200. A combined logistic over
  nine zero-timing predicates reaches out-of-fold AUC 0.749 and still fails.
  5 of 7 predictions hit.

**Measured, and negative — read this before building on 003:**
- **004 inverted the programme's central assumption.** Plain AST-size node
  counting beat *both* a textbook static latency table *and* per-operator
  measured cost: smaller tail (p95 1.451 vs 1.517 and 1.512), more
  exact-oracle matches, less waste per decision. The 13.5 ms calibration has
  **no break-even at all** — measured's waste per decision exceeds
  ast_size's, so measuring bought negative value.
- The reason is a dissociation worth carrying forward: the weighted models
  **predict runtime better** (Spearman 0.913 and 0.904 against ast_size's
  0.836) and **select worse**. Selection ranks a handful of equivalent forms
  inside one candidate set — local near-ties — and a globally better-calibrated
  model can systematically mis-rank exactly those. **Global fit is the wrong
  figure of merit for a selector.** 004 would have concluded the opposite had
  it scored fit instead of regret.
- Cost-model **granularity and counting discipline beat measurement**. Tree
  counting improved every arm (ast_size p95 1.451 → 1.309) because `lambdify`
  does no CSE and so really evaluates trees; one `pow_int` weight cannot
  encode that NumPy does `a**2` faster than `a*a` but `a**3` slower than
  `a*a*a`, and on the 153 decisions with an `x*x` candidate exact-oracle match
  fell to 20.3% for both weighted arms against ~77% elsewhere.

**Measured, and negative:**
- **Experiment 002** — automatic discovery of reusable substructure works
  structurally (12.00 -> 4.28 operators per task) but gained only 1.06x in
  real work. A fused primitive costs N^3 once and saves N^2 per use, so it
  repays after ~N uses; the workload sat inside its own break-even. 2 of 6
  predictions hit.

**Established by reading, not by us:**
- Cost-driven selection among equivalent representations already exists three
  times: Halide's autoscheduler, OpenTuner, egg/egglog extraction. Do not
  rebuild any of them.
- All three select against a *structural proxy*. egg's own docs: "extracted
  cost need not predict latency." Stitch's: "shorter programs need not
  execute faster."

## The finding that matters

The selector is not the gap. **The cost model feeding it is.** Resolution
policy and capability admission — the two gaps the literature screen and our
experiments reached independently — are one gap: structural proxies standing
in for measured cost.

And from 003, a design rule that is ours: **measure where the static model is
uncertain, and only there.** Calibration repays within ~5 requests where the
static table is wrong and never repays where it is right — and that is
exactly where measuring costs most, because calibration scales with the
problem while the saving goes to zero.

004 adds the condition that rule was missing: **and only if the thing you
measure is the thing that drives cost.** Per-operator latency, measured in
isolation on the real machine, is not that thing for array code — and
measuring it carefully made selection worse than counting nodes. 003's win
came from an *asymptotic* difference (O(n²) against O(n log n)) that no
weight table can encode; it did not come from knowing operator latencies
accurately. Those are different claims, and only the first survives 004.

The scope of the whole mechanism is now measured, not assumed: **a tail-risk
fix.** 95% of real decisions have nothing to win, and the 48x case exists but
is rare. Perfect selection is also unaffordable — timing every candidate costs
162x simply running the best form — so cheapness of the cost model, not its
accuracy, is the binding constraint.

And 005 closed the remaining exit. The tail is real but **not addressable**,
because no cheap predicate separates it. The reason is measured, not guessed:
**expression size drives what measuring costs but not how much error there is**
(`corr(oracle cost, waste) = 0.146`), and every cheap structural predicate
correlates with size. Flagged decisions cost 7–11x more to measure than
unflagged ones while holding no more error, so targeting spends the budget in
proportion to its price rather than its return.

The blocker is detector quality, not oracle price: a perfect detector would
repay in 117.5 requests and pass the bar. So the standing recommendation is
**drop measured costing from the resolution policy**, and the one condition
that reopens it is a tail predicate not confounded with expression size.

## Next experiment

004 and 005 together closed the measured-cost line as originally framed. What
remains are two specific, bounded questions, and **C is the one that could
still rescue the mechanism.**

**C. Does a cheaper oracle change the arithmetic?** Every break-even in 005
assumes the oracle is best-of-11 timing of every candidate — 30.454 ms per
decision. That price is a design choice, not a fact. One timing pass per
candidate instead of eleven would cut it ~11x, taking the best cheap rule from
854.8 requests to roughly 78 and perfect detection to ~11. The catch is that a
cheap oracle is a noisy oracle and may pick the wrong candidate, and **004
recorded only best-of-11 minima, so a noisy oracle's pick quality cannot be
recovered from the existing data.** This needs a new run that records every
repeat time per candidate, after which the trade-off between oracle price and
oracle accuracy is a direct calculation. Pre-register the break-even that
would make it worth shipping before running it. This is the cheapest
experiment left and the only one that can reverse the recommendation.

**B. Does the 004 inversion survive a backend where counting is not enough?**
004's result is entangled with one backend: vectorised NumPy with no CSE,
where cost is near-linear in operator count and so counting nodes is close to
counting memory passes. Re-run the same corpus and the same three arms through
a backend that fuses (Numba, JAX, or C via Cython) and where operator count
stops tracking cost. If the weighted arms win there, 004's conclusion is a
NumPy fact rather than an architectural one, and the honest claim shrinks to
"the cost model must match the backend's cost structure."

Do not re-run 004 with more corpora, and do not look for more tail predicates
in the same family — 005 measured why that family fails. The frequency number
and the targeting question are both settled.

## Working practices that are load-bearing

1. **Pre-register predictions in a commit before running anything.** Git
   history is the proof. Score hits and misses, and track the *sign* of the
   misses.
2. **The baseline must be the strongest existing tool**, not a naive one.
   rsync matched the dial on documents; the lesson repeats.
3. **Charge for everything**, including the measurement itself. The first
   sync benchmark measured only bytes and was therefore meaningless; 003's
   best finding came from charging for calibration.
4. **A known-good technique can be catastrophically wrong in context** —
   operator fusion applied per-sequence at batch size 1 is 59x worse than
   doing nothing.

## Known bias in the assistant's judgement

Across this project Claude's prediction errors shared a direction:
over-optimism about *when a mechanism starts paying*, and a habit of
collapsing the big idea into whatever is easiest to measure. It called the
document result "level with rsync" and reported a zero on photographs that
was an artifact of its own byte-level chunker. Treat its confidence about
individual pieces as reasonable and its judgement about whether combining
them is worth more than the sum as poorly calibrated.

004 and 005 continued the pattern and sharpened it. All three of its misses ran the
same way: it assumed a measured or hand-weighted cost model must beat counting
nodes (T5), that calibration would amortise (T9), and it wrote T10's predicate
so that T5's assumption was buried inside it — a prediction that could not
fail cleanly because it presupposed another one. It also over-estimated how
often structural cost is wrong, by 2.3x. The directional bias is now
**over-crediting the mechanism the programme is invested in**, including in
how the test itself is specified. Two safeguards earned their place in 004 and
should be kept: write each predicate so it depends on exactly one claim, and
score predictions with a script that runs off the results file rather than by
reading the numbers and narrating. 004's tautological hypothesis test, left
labelled in the analysis script, is what the unaided version looks like.

005 ran the same way on its two misses — both over-credited the cheap signals
— but its structural safeguards held: the ship criterion was economic and
fixed in advance, so FAIL was unarguable once the number came in, and the
mechanism behind the failure was *tested* (the size confound) rather than
asserted, which is the specific error 004 made. Keep pre-registering a
decision criterion with a number in it. It is what let 005 end a line of work
instead of extending it.

## Environment facts

- `git clone` from GitHub works; crate downloads work; PyPI works.
- **arxiv.org is blocked** by the network policy — papers need another route.
- GitHub MCP access is scoped to this repository only.
