# Handoff

Read this first. It is the state of the work, what is proven, what is not,
and the one experiment that comes next.

**For status, run the ledger, not this file:**

```
.venv-research/bin/python -I experiments/objectives_status.py          # table + "Done when"
.venv-research/bin/python -I experiments/objectives_status.py --drift  # + supersession watch
```

`research/OBJECTIVES.json` is the single source of truth for *where each
objective stands*; this document is for *what the results mean*. The split
exists because status kept drifting when it lived in prose: 005's
recommendation was reversed by 006 while 005's own findings section still read
as current advice, an earlier version of this file introduced an experiment as
pending after it had been done, and three documents each claimed to name "the
next experiment". The script fails if an objective marked closed cites
evidence that does not exist, so a stale status is now an error rather than
something a reader has to notice. **When an experiment closes an objective,
update the ledger in the same commit.**

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
| `research/OBJECTIVES.json` | **the objective ledger — what each objective is and where it stands** |
| `experiments/objectives_status.py` | renders and validates the ledger; run it first |
| `experiments/FINDINGS.md` | experiment log, 002 / 002b / 003 / 004 / 005 / 006 |
| `experiments/EXP004_PREREGISTRATION.md` | 004's ten predictions, committed before the run |
| `experiments/EXP005_PREREGISTRATION.md` | 005's seven predictions, and its ship criterion |
| `experiments/EXP006_PREREGISTRATION.md` | 006's seven predictions, with its hinge declared |
| `experiments/exp006_candidate_exprs.json.gz` | every admitted candidate's srepr, for re-timing on another backend |
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
- **Experiment 005** — the targeting question. The 4.3% tail cannot be flagged
  economically: best cheap rule needs **854.8 requests per expression** against
  **1216.9** for not targeting at all and a bar of 200. A logistic over nine
  zero-timing predicates reaches out-of-fold AUC 0.749 and still fails. The
  cause is measured: `corr(oracle cost, waste) = 0.146`, so cheap predicates
  track expression size, which drives what measuring costs but not how much
  error there is. 5 of 7 predictions hit. **Superseded by 006 — its
  recommendation to drop measured costing no longer stands.**
- **Experiment 006 — reverses 005.** 005 assumed one oracle price. Lower it and
  the problem dissolves: ranking candidates on **256-element probe arrays with
  a single repeat** costs 55 ms across 536 decisions and breaks even in
  **4.7 requests per expression**, bootstrap [1.9, 24.0], against the same
  200-request bar. 5 of 7 predictions hit.

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

005 then looked for the exit and 006 found it somewhere else entirely.

005 established that the tail cannot be *targeted*: no cheap predicate
separates it, because expression size drives what measuring costs but not how
much error there is (`corr(oracle cost, waste) = 0.146`), so flagging spends
budget in proportion to price rather than return. That finding stands.

006 showed the question was wrong. 005 was trying to target a price that
should simply have been lowered. **A single-repeat oracle ranking candidates
on 256-element arrays recovers ~90% of the available waste for ~1/550th of the
cost, breaking even in 4.7 requests per expression.** A cheap oracle on *every*
decision (4.7) beats perfect targeting of the expensive one (11.7). The
detector problem 005 could not solve does not need solving.

So the standing recommendation is now: **keep measured costing, run a cheap
oracle everywhere, and do not build a detector.** The operating point is
probe arrays two orders of magnitude smaller than the deployed size, one
timing repeat, and no targeting.

The mechanism behind it is worth stating because it generalises: **a noisy
oracle mis-picks among near-ties, and near-ties are by definition the choices
with nothing to lose.** At R=1 the oracle picks a non-best candidate on 22.9%
of decisions and still captures 91.6% of the waste. Mis-pick rate is the wrong
metric. Recovered waste is the right one.

## Next experiment

004, 005 and 006 settled the measured-cost line: structural cost is wrong 4.3%
of the time, the tail cannot be targeted, and it does not need to be because a
cheap oracle applied everywhere repays in ~5 requests.

**One experiment is queued. B is the only thing standing between this and a
defensible claim**, and
it threatens 004 and 006 together.

**B. Does any of this survive a backend where operator count stops tracking
cost?** Everything measured so far lives in one regime: vectorised NumPy with
no CSE, where runtime is near-linear in operator count including temporaries.
Two of the programme's load-bearing results may be artifacts of exactly that.
004's inversion — node counting beating measured per-operator cost — is
suspicious precisely because counting nodes nearly counts memory passes there.
And 006's probe-transfer result needs the small-array ranking to predict the
large-array ranking, which is plausible when cost is linear in operator count
and much less so when a compiler fuses the whole expression into one pass.

Re-time the identical candidate sets (their `srepr`s are saved, so no
regeneration) through Numba, JAX, or C via Cython, and re-run 004's three arms
and 006's probe grid. Pre-register separately for the two claims, because they
can fail independently. Charge compilation this time: 006 charged evaluation
time only, which is right for an already-compiled candidate and wrong for a
JIT where compiling each candidate in order to time it could dominate the
oracle's entire cost — and that single term could undo 006 on its own.

If the arms re-rank there, 004's conclusion shrinks to "the cost model must
match the backend's cost structure," and 006's operating point becomes
NumPy-specific rather than architectural.

**Superseded, do not redo:** the frequency question (004), the targeting
question (005 — and 006 makes targeting unnecessary, so do not look for better
tail predicates), and the oracle-price question in this backend (006).

**Also worth knowing before the next run:** the waste is pathologically
concentrated — one decision holds 38.8% of it, the top ten hold 85.9%. Every
recovered-waste fraction in 006 therefore has a wide bootstrap interval, and
the ranking among probe sizes is not resolvable at this sample size. Only the
headline survives it, because its margin is 8x even at the interval's worst
end. A backend comparison will need either many more decisions or a
waste-weighted design that stops treating 536 decisions as 536 independent
observations.

## Older items never closed

These predate 004 and are dormant, not finished. They concern **different
mechanisms** from the cost-model line, so B does not subsume them.

- **Recursive composition** (named in 002's follow-up, never run) — primitives
  built from primitives, testing whether the substrate gets cheaper to extend
  as it grows.
- **Cross-workload transfer** (same) — discover on workload A, evaluate on
  workload B from a different motif set over the same operators. The
  difference between compressing a known distribution and accumulating
  reusable capability.
- **Economic benefit beyond an optimised cache**
  (`research/benchmarks/NEXT_EXPERIMENT.md`, "designed, not executed") — the
  whole architecture against a strong memoisation baseline, not just the cost
  model. This is the one that would test the *architecture's* claim rather
  than one component of it.

`research/ARCHITECTURAL_GAPS.md` lists 8 further gaps, but those are
specification work rather than measurements. Gaps #3 (resolution policy) and
#4 (end-to-end economics) are now partly answered by 004–006 and should be
rewritten to say what those experiments settled.

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

**006 broke the pattern, and in the opposite direction.** Both its misses
(V5, V6) *under*-credited the mechanism: it predicted small probe arrays would
transfer poorly and they transferred at 91.9%, and it named repeat reduction
as the rescue when small probes beat that by 27x. After three experiments of
over-optimism, the correction had over-shot into pessimism about a cheapening
it had not tested. The durable lesson is narrower than "Claude is optimistic":
**its errors cluster wherever it has not actually measured the thing, in
whichever direction its last correction pointed.** The fix is not a standing
prior about direction. It is noticing which quantity in the design has never
been measured and measuring that one first — in 006 that was the oracle's own
price, which three experiments had carried as a constant without ever asking
what set it.

One more habit earned its place in 006: **report the bootstrap, not just the
point estimate.** Its headline survives resampling (4.7 requests, worst end
24, against a bar of 200) while three of its subsidiary claims do not. Without
that check the write-up would have asserted a probe-size ranking the data
cannot support.

## Environment facts

- `git clone` from GitHub works; crate downloads work; PyPI works.
- **arxiv.org is blocked** by the network policy — papers need another route.
- GitHub MCP access is scoped to this repository only.
