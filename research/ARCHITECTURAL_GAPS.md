# Remaining architectural gaps

These are candidate integration/research problems, not findings of novelty.

Status for each gap is tracked in `research/OBJECTIVES.json` (ids
`O-gap-1-semantic` … `O-gap-8-evidence`); render it with
`.venv-research/bin/python -I experiments/objectives_status.py`. This file
states the gaps; it is not the record of which are still open.

1. **Semantic contract.** Define value types, arithmetic (unbounded integers versus wrapping bitvectors versus floating point), effects, errors, recursion and termination. A valid equality in one domain can fail in another.
2. **Identity contract.** Distinguish representation hash, equivalence class, derivation identity, and output hash. Include rule version, runtime/ABI, declared environment, input dependencies and exactness mode where relevant. An e-class ID is not a portable global content ID.
3. **Resolution policy.** Compare local result reuse, partial repair, execution, remote retrieval, compressed-domain query and specialization. Reuse available caches/runtimes; implement their narrow decision interface.
   *Partly answered by 003–006, for the choose-among-equivalent-forms part only:* selection by measured per-operator cost is **worse** than counting AST nodes on a corpus nobody picked (004); targeting measurement at the error tail does not pay, because cheap predicates track expression size and size drives measurement cost but not error (005); the standing policy is a **cheap oracle on every decision with no detector**, break-even 4.7 requests per expression (006). All three are single-backend results — see `O-007-backend`. Reuse, repair, retrieval, compressed-domain query and specialization are **untouched**.
4. **End-to-end economics.** Count lookup, hashing, optimization, compilation, execution, validation, network movement, retained graph/library state and invalidation costs. Keep time, memory, energy and money separately unless an explicit conversion is justified.
   *Partly answered by 003–006:* break-even request counts are now the programme's unit of account, and measurement is charged rather than assumed free. Two stated requirements are **not met and the shortfall was never recorded until now**: only **latency** is measured, never bytes, memory, energy or money (`O-multi-resource`), and 006 charges evaluation time while **excluding compilation**, which for a JIT backend could dominate the oracle's whole cost (`O-007-backend`).
5. **Capability admission.** Stitch can propose abstractions and Ruler can propose rules. Define semantic checks, applicability conditions, held-out transfer, admission thresholds, versioning and garbage collection. More retained structure is not automatically useful growth.
6. **Updates.** Mutable input revisions and invalid rule assumptions need safe invalidation. Monotone equality growth and collection deletions are different update problems. Do not assume a union operation can be automatically undone.
7. **Reconstruction contract.** A descriptor is sufficient only relative to an available interpreter, recipe and dependencies. State separately which bytes are preinstalled, fetched, transmitted or generated. This does not require the full output file to preexist on the receiver.
8. **Evidence and novelty.** A literature screen and tiny integration do not establish a new computational model, commercial freedom to operate or general speedup. Write precise differentiating claims and compare them with redun, gg, egglog, library-learning systems and build-system theory.

A practical cost formulation is:

J(method, request, state) = lookup + planning + compilation + materialization/transfer + execution/repair + validation + amortized retained-state cost.

This is a proposed accounting interface. Its terms must be estimated in compatible units or reported as a vector/Pareto comparison. MDL can penalize description growth; it is not a complete runtime-economics objective.
