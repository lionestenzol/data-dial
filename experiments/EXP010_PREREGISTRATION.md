# Experiment 010 — pre-registration (does discovery eat the 4x?)

Committed before the run. Closes `O-discovery-cost`, the gate on
`O-selection-layer` and `O-bet` that 009 exposed. Reuses 009's per-item
mechanism costs (`experiments/exp009_results.json`); adds the discovery
protocol and provenance model.

## The question

009's selector beat rsync 4.0x but had **oracle knowledge of B's state** —
which files B holds exactly, has a related version of, or can regenerate. A
deployed selector must discover that, and if discovery costs more than it saves,
the 4x evaporates. DR-001's P1: *can receiver-state discovery be performed
cheaply enough to justify mechanism selection?*

## Two costs people conflate, separated here

1. **Discovery message** — B advertises its state to A: a manifest of (a) content
   hashes of files it holds (enables `cache`), (b) a list of generator ids it has
   installed (enables `recompute` eligibility), (c) block signatures of candidate
   files (enables `delta`). Charged in bytes, B→A, once per session of K objects.
2. **Provenance coverage `p`** — `recompute` also requires that **A retained a
   runnable recipe for X**. That is not a per-transfer message; it is an
   architecture discipline (did the sender keep the generator's inputs). Modeled
   as the fraction `p` of generated objects for which A holds the recipe. If A
   lacks it, `recompute` is unavailable for that object regardless of B.

Fair accounting: **each policy pays its own discovery.** always-transfer pays
nothing. always-delta (rsync) pays per-object block signatures (already inside
009's delta bytes). The selector pays the manifest (content hashes + capability
list; its delta-signature part is the same bytes rsync already pays).

## Model

- Session = the 72-item 009 corpus as one batch A realises at B.
- Manifest bytes = 32 × |files B holds exactly| + 16 × |generators B has|
  (the delta-signature bytes are already in each item's delta cost).
- `recompute` available for object X iff B has the generator (009 b_state) AND
  `random() < p` (A retained the recipe).
- realised_selector(p) = Σ chosen-mechanism bytes + manifest bytes.
- Compare against always-transfer (Σ transfer, no manifest) and always-delta
  (Σ delta). Sweep p ∈ {0, 0.25, 0.5, 0.75, 1.0}; compute budget fixed at 1 s.

## Predictions

| | prediction |
|---|---|
| **V1** | The discovery manifest (content hashes + capability list) is < 5% of the selector's realised bytes — the message cost is negligible. |
| **V2** | **The gate.** At full provenance (p=1), after charging discovery, the selector still beats rsync ≥ 3.5x. The 4x survives. |
| **V3** | The realised win scales ~linearly with p; at p=0 (A kept no recipes) the selector is within 10% of rsync — with no recompute it reverts to rsync. |
| **V4** | The binding constraint is provenance, not message cost: varying p moves realised savings far more (≥10x more) than varying the manifest size over any plausible session size does. |
| **V5** | Charging discovery symmetrically does not flip the ranking at p ≥ 0.5: selector still beats both static policies. |

## What each outcome means

- **V2 holds**: 009's 4x is deployable, not an oracle artifact, and the binding
  question shifts from "can we discover B's state" (cheap) to "did A keep the
  recipe" (provenance discipline). `O-selection-layer` stays justified; the
  architecture's real requirement is retaining generators, which is the project's
  founding premise.
- **V2 fails** (discovery eats the gain even at p=1): the selector is not
  deployable as modeled; 009's 4x was an oracle artifact; the honest answer
  reverts toward "use rsync." Most important possible negative.
- **V4 holds**: the useful reframe — the cost that matters is not a runtime
  message, it is whether the sender kept the recipe. That is the thing the whole
  project has been about (keep the generator).

## Bias guard

This assistant's errors cluster where a quantity was never measured. The
never-measured quantity is the discovery/provenance cost, which this experiment
exists to pin. V2 is the kill condition and is stated so the result can revert
the project to "use rsync" if the data says so.
