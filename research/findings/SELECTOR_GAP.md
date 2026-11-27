# The selector is not the gap. The cost model is.

Read of PRIOR_ART.md, prompted by the question: has anyone already built
cost-driven selection among equivalent ways of producing a result? If so, the
architecture's original contribution shrinks and we should know before
building.

## Answer: it exists three times over, each time crippled in the same way

| System | Selects among | By what cost | Scope |
|---|---|---|---|
| Halide autoscheduler | equivalent schedules | tree search + learned performance model | image pipelines only; time only; 75% avg reported improvement |
| OpenTuner | candidate strategies | multi-objective, ensemble search | offline tuning of a fixed search space, not per-request |
| egg / egglog extraction | equivalent expressions | **static cost function over the AST** | any DSL, but see below |

So the selection machinery is solved and should not be rebuilt. What none of
them has is a cost function grounded in *measured, multi-resource, per-device*
expenditure.

## The one line in the cards that matters most

> ## RETRACTED — verified against primary sources, 2026-11-27
>
> **The two quotations below are ours, not upstream's, and this section
> attributed them to egg and Stitch. That was wrong.**
>
> Both strings are the `limitations` field of **our own** prior-art cards in
> `research/PRIOR_ART.md` — editorial compression we wrote — and this section
> promoted them into warnings issued by the upstream projects
> (*"egg's limitation field reads"*, *"both documents warn"*).
>
> Checked at source: egg @`73975c9` (2026-09-28), full repository and rustdoc.
> The entire repo contains **one** mention of cost alongside any
> performance word, and it is the verb "perform" in
> `src/extract.rs:51` — *"requires a cost function to performs its greedy
> search"*. egg's `CostFunction` documentation covers the `Cost` type's
> `PartialOrd` requirement, `NaN` panics, how to write a cost function,
> the `AstSize` and `AstDepth` built-ins, and one caveat — that a cost
> function like `AstSize` **"might overflow `usize`"** on pathological inputs,
> so you may want `saturating_add` to keep it monotonic. That is an
> arithmetic caveat. **There is no statement anywhere about extracted cost
> predicting latency, runtime, or any physical quantity.**
>
> Stitch @`350804b`: every runtime and speed mention concerns *Stitch's own*
> search time against DreamCoder, plus a note that `--max-arity` raises
> runtime. **Nothing about whether learned abstractions execute faster.**
>
> Unverified: egg's POPL 2021 paper and Stitch's POPL 2023 paper. arxiv.org is
> blocked by this environment's network policy, so the papers were not read.
> But this section claimed *documentation*, and the documentation does not say
> it.
>
> **What this does and does not break.** The underlying claim is probably
> true — AST size demonstrably does not track runtime, and experiment 004
> measured exactly that, 4.3% of the time materially. That finding stands on
> our own measurements. What falls is the argument this section was built to
> make: that the gap was *already identified and left open by the authors of
> these systems*, which is what made it look like a known, citable opening
> rather than a hunch. It was a hunch. A correct one, but ours.
>
> Note the irony recorded in `experiments/FINDINGS.md` 004: when we finally
> measured it, the structural proxy turned out to be the **better** selector
> than measured per-operator cost. The premise we attributed to egg is one our
> own data partly contradicts.

The two lines, as they were quoted here, were:

> "extracted cost need not predict latency" — **our card's wording, not egg's**

> "shorter programs need not execute faster" — **our card's wording, not Stitch's**

They describe the same suspected defect in two layers — selection and
admission: both systems optimise a **structural proxy** (AST cost, program
length), and we believed the proxy does not track the physical quantity the
architecture cares about. Treat that as this project's analysis, requiring its
own evidence, which 004 later supplied and partly complicated.

## We hit this empirically before reading it

Experiment 002, run earlier today without knowledge of these cards, measured
exactly this failure:

- structural metric: operators per experience fell 12.00 to 4.28 — a 2.80x
  improvement by the proxy
- physical metric: 1.06x by multiply-accumulates

The structural proxy over-predicted real benefit by **2.6x**. 002's keep-rule
was a structural rule (`train count > N`), and it over-kept at N=8 and kept
nothing at N=128. That is the defect **we had hypothesised** for egg and
Stitch, reproduced from scratch by hand — and 002's measurement is the actual
evidence for it. Neither project documents the limitation; see the retraction
above.

## What this does to the gap

The gap narrows and sharpens. It is not "build a selector." It is:

> **Feed an existing extraction/scheduling engine a cost function over the
> measured multi-resource vector — bytes moved, receiver CPU, energy,
> latency, resident storage — instead of a structural proxy, and find out
> whether selection quality improves enough to pay for the measurement.**

That is a small integration against egg/egglog rather than a new system, and
it is the first experiment in this programme whose outcome is not already
documented somewhere in these 33 cards.

It also merges the two gaps that the literature screen and our own
experiments independently converged on — resolution policy (#3) and
capability admission (#5). They are one gap: **structural proxies standing in
for measured cost.**

## Research status

This question is now closed; no further broad screening is needed to answer
it. Cards consulted: egg, egglog, Stitch, DreamCoder, OpenTuner, Halide,
Build Systems a la Carte, gg, redun, SymPy, Ruler, Souper, partial
evaluation. All are documented-only except egglog, redun and Stitch, which
were locally executed and independently re-run here.
