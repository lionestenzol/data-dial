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
| `experiments/FINDINGS.md` | experiment log, 002 / 002b / 003 |
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

## Next experiment, and it is the honest one

003's domain was *chosen* because the proxy had to fail in it. 94x is an
existence proof, not a frequency claim. The next question cannot be stacked
in our favour:

> **How often is structural cost wrong on a workload nobody picked in
> advance?**

Take a corpus of real expressions or programs that somebody else wrote, run
all three cost arms, and report the distribution of regret — not the maximum.
If structural cost is near-optimal 95% of the time, the measured-cost
mechanism is a niche fix and the architecture should say so.

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

## Environment facts

- `git clone` from GitHub works; crate downloads work; PyPI works.
- **arxiv.org is blocked** by the network policy — papers need another route.
- GitHub MCP access is scoped to this repository only.
