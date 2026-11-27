# Experiment 007 — pre-registration

Committed **before the first run**. Harness development was a mechanics-only
smoke test whose measurements are declared below as setup facts; no economic
quantity has been computed.

Closes `O-007-prereg`. Objective under test: `O-007-compile-charge`.

## The question

006 concluded that a cheap oracle applied to every decision breaks even in
**4.7 requests per expression** (bootstrap [1.9, 24.0]) against a 200-request
bar, and on that basis the standing recommendation became "keep measured
costing, run a cheap oracle everywhere, do not build a detector."

That number charges **evaluation time only**. `HANDOFF.md` flagged the hole in
it when the result was written:

> Charge compilation this time: 006 charged evaluation time only, which is
> right for an already-compiled candidate and wrong for a JIT where compiling
> each candidate in order to time it could dominate the oracle's entire cost —
> and that single term could undo 006 on its own.

On any compiling backend you cannot time a candidate without first compiling
it. So:

> **Does charging compilation push 006's break-even above the bar?**

This is the cheapest cut of HANDOFF item B and it is tested first because if
006 dies here, the rest of item B is moot.

## The accounting, which is the whole experiment

Charging every compilation to the oracle is the obvious move and it is
**wrong**: a no-oracle policy still has to compile whichever form it chose.
Both readings are pre-registered, and the generous one decides:

- **Gross** — the oracle pays `k` compilations for `k` admitted candidates.
- **Marginal** — the oracle pays `k − 1`, because one compilation is
  unavoidable under any policy. **This is the accounting that decides the
  question.** If 006 fails even here, it fails honestly.

A third effect is stated because it cuts *for* 006: one compiled artifact can
serve both the cheap probe and the deployed run, so 006's probe-size trick
costs nothing extra in compilation — but it then shrinks a term that is no
longer dominant. That is W6.

## Setup, fixed in advance

| Thing | Value |
|---|---|
| Backend | C via `sympy.ccode` scalar body + hand-written loop, `gcc -O2 -shared -fPIC -march=native`, loaded with `ctypes.CDLL`. Zero new dependencies. |
| Machine | 4x Xeon @2.10 GHz, AVX-512 + FMA, L2 8 MiB, gcc 13.3.0, Python 3.13.18 |
| Compile charge | wall time of the `gcc` subprocess, measured per candidate |
| Deployed size | 16384 float64, as in 004/006 |
| Probe sizes | 256, 1024, 4096, as in 006 |
| Candidates | **regenerated** with `exp004_regret_distribution.candidates_for`, not reloaded (see below) |
| Admission | relative error <= 1e-6 against a 30-digit reference, re-checked on the C outputs |
| Optimisation flags | `-O2` primary; `-O2 -ffast-math` as a secondary arm with admission re-checked |
| Ship criterion | <= 200 requests per expression, carried over from 005 and 006 |

### Measured during harness development, declared as setup, not predicted

- **Compilation is ~685x one evaluation.** gcc wall time 40.5-181.5 ms per
  candidate (5 repeats of one source: 47.1, 52.2, 57.6, 47.1, 40.5 ms, spread
  1.42x) against ~59 us for one evaluation at the deployed size.
- **`ccode` preserves the unevaluated repeated multiply.**
  `Mul(x,x,x,x,evaluate=False)` prints as `x*x*x*x` while `x**4` prints as
  `pow(x, 4)`. The `powexp/` candidate family therefore survives into C, which
  it does not survive through `srepr`.
- **Six C kernels agree with `lambdify` to <= 3e-16 relative**, including
  `Max`/`Abs` and a `powexp` form.
- **Hand-fused C is only 0.97x NumPy at 16384 elements** (59.1 us against
  57.3 us). This is declared because it cuts against the premise of the *later*
  claims: at this array size NumPy's per-operator loops are already
  L2-resident and bandwidth-bound, so a single fused pass wins nothing. It does
  not affect this experiment, which is about the price of compilation, but it
  means "a backend where operator count stops tracking cost" is **not yet
  demonstrated** and X1/X2 should not be run on the assumption that it is.

### Why candidates are regenerated rather than reloaded

006 saved every admitted candidate's `srepr` so item B would not have to
regenerate them, and both `HANDOFF.md` and `research/OBJECTIVES.json` claimed
"no regeneration is needed". **That claim is false and is corrected in this
commit.** `srepr` emits no `evaluate=False`, so all **322** `powexp/`
candidates reload as duplicates of their base sibling: 411 of 2286 entries
change structure, 174 of 536 decisions are contaminated, and 24 have a
`powexp/` form as their oracle pick. The tag-to-expression *mapping* is sound
(2286/2286 verified against full regeneration), but the expressions are not.
`candidates_for` is deterministic and reproduced all 536 decisions exactly in
88 s, so regeneration is both cheap and exact.

## Predictions

Each depends on exactly one claim. 004's T10 failed because another
prediction's assumption was buried inside it; that is not repeated here.

| | prediction |
|---|---|
| **W1** | Compilation dominates evaluation: mean per-candidate compile time >= 100x mean per-candidate evaluation time at the deployed size. |
| **W2** | Gross accounting (`k` compiles): break-even exceeds the 200-request bar. |
| **W3** | **The decisive one.** Marginal accounting (`k-1` compiles): break-even *also* exceeds 200. 006's operating point does not survive a compiling backend even on the generous reading. |
| **W4** | Marginal break-even lands between **1,000 and 50,000** requests per expression. |
| **W5** | Fusion does not rescue it: total recoverable waste as a fraction of total runtime on the C backend is within **3x** of NumPy's. |
| **W6** | Probe-size reduction cannot help: with one compiled artifact serving probe and deployment, break-even varies by less than **1.2x** across probe sizes 256/1024/4096, because the dominant term is compilation and compilation is probe-size independent. |

## What each outcome means

- **W3 holds** (the expected case): 006's conclusion is scoped to interpreted,
  per-operation backends. The standing recommendation reverts toward 005's —
  not because the tail can be targeted, but because the oracle cannot be
  afforded where candidates must be compiled. The architecture must then say
  that measured costing applies only where evaluation is cheap relative to
  compilation, which is a much narrower claim than 006's.
- **W3 fails** (marginal break-even stays under 200): 006 survives contact
  with a real compiler, and its operating point is stronger than expected.
  X1/X2 then become worth running, and `O-008` is written.
- **W5 fails** (waste is much larger under C): fusion changes the *size* of the
  prize, not just the price. That would be the most interesting outcome and
  would redirect item B toward measuring waste rather than oracle cost.
- **W1 fails**: the compile charge is not the dominant term after all and this
  whole experiment was mis-aimed; item B should go straight to X1/X2.

## Known bias being guarded against

004, 005 and 006 each missed by over-crediting the mechanism this programme is
invested in; 006's two misses then ran the other way, under-crediting a
cheapening it had not measured. The durable lesson recorded in `HANDOFF.md` is
that the errors cluster **wherever a quantity has never actually been
measured**. The never-measured quantity here is compilation, which three
experiments carried as zero. W1 and W4 are therefore stated as arithmetic over
a quantity now measured in the smoke test, and W5 — the one genuinely open
question, whether fusion enlarges the recoverable waste — is stated so that it
can fail in the direction that would *help* the programme.
