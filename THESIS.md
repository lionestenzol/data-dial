# The thesis

Read this before `HANDOFF.md`. It is what the project is actually about. Every
experiment so far (002–008) tested a sub-tactic and kept getting mistaken for
the thesis itself; this page exists so that stops happening.

## The claim

**The generator is the primary object. The artifact is a cached render of it.**

Almost everything was produced by some process — a build, a draw call, a
decode, a query. We keep the output and throw the process away, then spend
enormous effort moving outputs around and noticing they are similar. If the
*generator* is the primary object, the output is just a cache you can rebuild.

## The rule

**For each artifact, send whichever is cheaper: the bytes, or the generator
plus the cost of regenerating.**

- Cheap artifact → send the bytes. The generator's overhead is not worth it.
- Expensive artifact → send the generator. The render is dear to move or remake.

That is the whole system. It is a cost-driven switch, not a sync tool. The
project is named for it: **data-*dial*** — the dial between shipping the thing
and shipping the recipe.

    cost(ship artifact)  vs  cost(ship generator) + cost(regenerate) + cost(verify)
    send the cheaper side.

Reconstruction is **byte-exact and verified** — this is not lossy generative
media (see the prior-art cards for GenTrans / "To Store or To Regenerate",
which give up exactness; `research/RESEARCH_INDEX.json`). Exactness is the line
between this and that whole 2026 literature.

## Both ends are generators

The capture end and the transmit end are halves of one loop:

- **Transmit** (data-dial): you hold the generator, ship it, rebuild on the far
  side. recipe → artifact.
- **Capture** (sitepull, the author's other project): the generator was thrown
  away, so you stand in front of the deployed artifact and infer it back.
  artifact → recipe.

sitepull exists *because* the recipe was discarded. data-dial exists so it
never is. Same conviction, opposite directions.

## What this reframes

The project ran eight experiments on the wrong altitude of "selection":

- **002–008 selected among equivalent expression _forms_** — which rewriting of
  the same computation is cheapest to run. That is a sub-tactic (and a crowded
  one: OpTuner, semantic caching — see the registry). 008 showed it loses to a
  free canonicalisation on cheap artifacts.
- **The real selection is artifact-vs-generator, per item**, on a
  network-vs-compute cost model. That is the novel, unoccupied intersection
  three independent literature screens converged on, and it has been tested
  exactly once — the v1 sync sim, on day one, which won.

So every result to date is a **point on the cost curve**, not a verdict:

| experiment | regime | cheaper side |
|---|---|---|
| 008 (integers, µs to run) | left end — cheap | **bytes** |
| v1 sim (photos/docs) | right end — expensive | **generator**, 78 vs 285 MB |
| rsync ≈ dial on documents | near the crossover | tie |

## The experiment that was never run

Draw the curve. One workload spanning cheap→expensive artifacts; three arms —
**send artifact / send rsync-delta / send generator-and-rebuild**; metric total
bytes + receiver compute + verification; byte-exact throughout; baseline is
rsync, because rsync already nearly tied the dial on documents. Find the
crossover and show the dial picks the cheaper side at every point.

That is the first experiment that would test the thesis instead of a tactic
inside it. Tracked as `O-crossover` in `research/OBJECTIVES.json`.

## The standing caution

`HANDOFF.md` records that this assistant's recurring error is collapsing the
big idea into whatever is easiest to measure. This whole page is the correction
for one instance of that: the cost model was easy to measure, so eight
experiments measured it, while the thesis above — which is harder to measure
and is the actual bet — went untested after day one.
