# Remaining architectural gaps

These are candidate integration/research problems, not findings of novelty.

1. **Semantic contract.** Define value types, arithmetic (unbounded integers versus wrapping bitvectors versus floating point), effects, errors, recursion and termination. A valid equality in one domain can fail in another.
2. **Identity contract.** Distinguish representation hash, equivalence class, derivation identity, and output hash. Include rule version, runtime/ABI, declared environment, input dependencies and exactness mode where relevant. An e-class ID is not a portable global content ID.
3. **Resolution policy.** Compare local result reuse, partial repair, execution, remote retrieval, compressed-domain query and specialization. Reuse available caches/runtimes; implement their narrow decision interface.
4. **End-to-end economics.** Count lookup, hashing, optimization, compilation, execution, validation, network movement, retained graph/library state and invalidation costs. Keep time, memory, energy and money separately unless an explicit conversion is justified.
5. **Capability admission.** Stitch can propose abstractions and Ruler can propose rules. Define semantic checks, applicability conditions, held-out transfer, admission thresholds, versioning and garbage collection. More retained structure is not automatically useful growth.
6. **Updates.** Mutable input revisions and invalid rule assumptions need safe invalidation. Monotone equality growth and collection deletions are different update problems. Do not assume a union operation can be automatically undone.
7. **Reconstruction contract.** A descriptor is sufficient only relative to an available interpreter, recipe and dependencies. State separately which bytes are preinstalled, fetched, transmitted or generated. This does not require the full output file to preexist on the receiver.
8. **Evidence and novelty.** A literature screen and tiny integration do not establish a new computational model, commercial freedom to operate or general speedup. Write precise differentiating claims and compare them with redun, gg, egglog, library-learning systems and build-system theory.

A practical cost formulation is:

J(method, request, state) = lookup + planning + compilation + materialization/transfer + execution/repair + validation + amortized retained-state cost.

This is a proposed accounting interface. Its terms must be estimated in compatible units or reported as a vector/Pareto comparison. MDL can penalize description growth; it is not a complete runtime-economics objective.
