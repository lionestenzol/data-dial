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

egg's limitation field reads:

> **"extracted cost need not predict latency"**

And Stitch's reads:

> **"shorter programs need not execute faster"**

Those are the same defect in two different layers — selection and admission.
Both systems optimise a **structural proxy** (AST cost, program length) and
both documents warn that the proxy does not track the physical quantity the
architecture actually cares about.

## We hit this empirically before reading it

Experiment 002, run earlier today without knowledge of these cards, measured
exactly this failure:

- structural metric: operators per experience fell 12.00 to 4.28 — a 2.80x
  improvement by the proxy
- physical metric: 1.06x by multiply-accumulates

The structural proxy over-predicted real benefit by **2.6x**. 002's keep-rule
was a structural rule (`train count > N`), and it over-kept at N=8 and kept
nothing at N=128. That is egg's documented limitation and Stitch's documented
limitation, reproduced from scratch by hand.

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
