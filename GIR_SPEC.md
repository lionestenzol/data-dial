# GIR — the governing objective

This supersedes `THESIS.md` as the top-level frame. THESIS.md (the data-dial
"send the generator" idea) is now **one mechanism cell** inside the space this
document defines: `GENERATE`/`ACTIVATE` under `E_bitwise`. Read this first.

## The invariant

Given independent environments A and B and an object X in A, achieve X′ in B
with `E(X, X′) = true` under a chosen equivalence relation E — optimizing
end-to-end realization latency, fidelity, resource cost and infrastructure
dependence. **Transport of X is not a required intermediate step.** The project
concerns *destination-state realization*, not the preservation of any one
source-to-destination mechanism.

Receiver operation: `X′ = M(S, K_B, C_B, R_B)` — a mechanism M reconstructs X′
from a signal S plus the receiver's knowledge K_B, compute C_B and resources
R_B. S need not resemble X; it may be an address, instruction, constraint,
reference, parameter, synchronization event, or residual.

The full specification (objective invariant, generalized formulation,
optimization domain, the ten-node conceptual mechanism graph, mechanism
selection space, information-theoretic boundary, equivalence hierarchy,
research policy, disposition function, termination and semantic invariant) is
the project of record. It is reproduced in `research/GIR_SPEC_FULL.md`.

## The single judge (why this is actionable and not "all of computer science")

Stated at full generality the objective contains most of computer science.
What bounds it into a research programme is **§6, the information-theoretic
boundary**, and it is load-bearing:

> Every node of the mechanism graph is the same move — enrich `K_B`, or cheapen
> the shared map `D` — and there is exactly one judge across all of them:
> **does `K(X | K_B)` + resolution cost beat transmitting X?**

No mechanism *creates* information. Recursion (NODE_01), temporal addressing
(02), multi-state (03), relational (04), constraint intersection (05),
codebooks (07) — each exploits structure X already has. For incompressible X
the address into Ω\* that uniquely names X is itself ≈ |X| bits, so a large Ω
buys nothing (`ADDRESSABILITY ≠ EFFICIENT_RESOLUTION`). This is the rock the
project already hit: the day-one "zero on photographs" was a JPEG being
near-incompressible — no cheap recipe existed to find.

**The win exists precisely where X is the low-complexity output of a process B
can share or be told cheaply — i.e. `K(X | K_B)` is small.** That is
node-independent and it is the whole game. The dial (THESIS.md) is the
per-object decision of whether exploiting that structure pays; the recursion
(keyboards-in-keyboards, clocks-in-clocks) is the dial applied at every node of
a generation tree, bottoming out at leaves where bytes beat recipe.

## The prior art §9 demands be found before any synthesis

The objective's formal core is a **solved area the registry had not screened**:

- **Distributed source coding — Slepian–Wolf (1973), Wyner–Ziv (1976).** Proves
  X can be compressed to `H(X | K_B)` *even when the encoder at A lacks K_B*, so
  long as K_B is at the decoder. This is §2 and NODE_07 exactly, with a proven
  achievable bound. Any architectural synthesis must start from this, not
  reinvent it.
- **rsync (Tridgell) is a practical instance** — reconstructs X at B from B's
  existing similar file, sending only differences, without A holding B's copy.
  This is why rsync kept tying the dial on documents: it is already doing the
  general objective well. The competition is not "transmission"; it is the best
  existing exploiters of K_B.

See `research/RESEARCH_INDEX.json` for the cards.

## Node → established-mechanism map (first pass)

| node | established mechanisms | status in registry |
|---|---|---|
| 01 recursive info space | grammar/SLP compression (Sequitur, Re-Pair), L-systems, MDL/Kolmogorov | partially carded (grammar-compression, MDL) |
| 02 temporal address space | counter-based PRNGs (Random123/Philox/Threefry), jump-ahead LCG/PCG, fast exponentiation | **gap** |
| 03 multi-state config | residue number systems, CRT; **set reconciliation (IBLT)** for diffs | carded (DR-001) |
| 04 relational addressing | delta/diff coding, invariant features | partial (dial, rsync) |
| 05 constraint intersection | SAT/SMT, symbolic execution, program synthesis, egg/egglog | partially carded (egglog, Souper) |
| 06 exact realization | Slepian–Wolf; **rsync/RDC/casync delta family** | carded (DR-001) |
| 07 shared interpretive foundation | **distributed source coding**, channel simulation, semantic comms | carded (DSC) |
| 08 capability activation | RPC, content-addressable computation, **Named Function Networking** (closest whole-vision match) | carded (DR-001) |
| 09 shared capability provisioning | reproducible builds, Nix, Bazel RE, Wasmtime, **CRDTs** (convergent state) | carded |
| 10 infrastructure bypass | content addressing (IPLD/IPFS), build-graph shortcutting | partial |

Node investigation CLOSED by `research/DR-001.md` (external pass): all ten
nodes classified, verdict **Stopping Condition C/D** — no new mathematics
required, the single residual gap is a **general cross-type mechanism-selection
layer** (the dial, generalized). Next action is the P0 benchmark (`O-crossover`),
not more taxonomy.

## Disposition (§10), honest first cut

- `K(X|K_B)` as the cross-node judge → **ADOPT** (information theory; nothing to
  build, everything to respect).
- distributed source coding → **RESEARCH then INTEGRATE** — it is the baseline
  and the bound; the project cannot claim novelty without positioning against
  it.
- the dial / recursive decomposition → **the one genuine open synthesis** — but
  only demonstrated to pay in the high-`K(X|K_B)`-gap regime, and only ever
  tested once (v1 sim). Tracked as `O-crossover`.

## Session caution carried forward

This project's recurring failure (documented in HANDOFF) is collapsing the
objective into whatever is easiest to measure. §12's semantic invariant — *do
not collapse the objective into any individual mechanism* — is the formal
statement of that lesson. Eight experiments collapsed it into cost-model
selection. This document exists to prevent the ninth from doing the same.
