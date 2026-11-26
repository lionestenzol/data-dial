# Recursive Information Virtualization: research-first architecture assessment

**Research date: November 26, 2026. Scope: capability mapping, prior-art screening, narrow implementation checks, and experiment selection.**

The research supports reusing existing infrastructure before building the architecture. The strongest change to the supplied proposal is that even its proposed original areas—adaptive selection, economics and capability accumulation—have substantial prior art. Their remaining contribution must be specified and tested at the level of integration, semantics and measurable benefit.

This pass records **33 discovery entries**. All requested initial areas are mapped, with deeper attention to candidates that can eliminate entire component categories. Four installed packages were exercised. This is a targeted screen, not a comprehensive literature review, source/security audit, patent search, or demonstration of architectural novelty.

## 1. Capability-to-prior-art matrix

| Desired capability | What actually needs implementation |
|---|---|
| Information-addressed executable code | Reuse Unison or adopt a narrow descriptor adapter; a new language is optional |
| Equivalent computational representations | Define domain semantics/rules/costs around egg or egglog |
| Logical inference plus equivalence | Configure egglog rather than independently building both engines |
| Reusable computational relationships and result history | Adapt redun; compare gg's executable-thunk model |
| Recompute only affected demand | Integrate Salsa, or evaluate Adapton/Fumola for finer dependency semantics |
| Recursive collection updates | Encode suitable workloads in Differential Dataflow |
| Portable virtual processor | Use Wasmtime; evaluate Wasmi for constrained hosts |
| Dependency closure and repeatable environment | Pin Nix derivations or equivalent existing packaging infrastructure |
| Distributed storage/action execution | Adapt Buildbarn's Remote Execution API; avoid writing a worker protocol |
| References to references | Use established hash-linked blocks/CIDs/Merkle structures |
| Peer networking | Integrate libp2p if peer discovery is an actual requirement |
| Compressed-object queries | Match operators to Succinct, SDSL or grammar-specific algorithms |
| Hardware-targeted compilation | Use IREE/MLIR when numerical workloads justify their complexity |
| Capability accumulation | Evaluate Stitch and DreamCoder before writing an abstraction learner |
| Automatically discovered rewrite rules | Evaluate Ruler; study Souper's constrained synthesis/refinement approach |
| Adaptive selection and cost estimation | Reuse autotuning/search techniques; define RIV-specific measurements |
| Substrate economics | Combine amortized measurement and explicit resource accounting; use MDL only where appropriate |

The expanded matrix in CAPABILITIES.md classifies requirements as already solved, partially solved, multiple solutions, or unresolved within the stated scope. A technology's existence does not make every stronger version of the requirement solved.

## 2. The discoveries that most change the plan

**redun is a stronger starting point for integration than the original list suggests.** Its documented design combines lazy expressions, graph reduction, hashed tasks and inputs, cached intermediate results, code/data change handling, provenance and multiple execution backends. It directly connects several proposed capabilities in one implementation. It does not establish equivalence between arbitrary different functions. [Design](https://insitro.github.io/redun/design.html), [repository](https://github.com/insitro/redun).

**egglog already combines multiple proposed reasoning engines.** It joins equality saturation with Datalog-style inference, composable analyses and incremental matching. This can eliminate separate implementations of those mechanisms. The 2023 paper's incremental matching operates over evolving facts/equalities; it should not be equated with arbitrary mutable-program dependency repair or automatic retraction of old merged equalities. [Paper](https://ztatlock.net/pubs/2023-pldi-egglog/2023-pldi-egglog.pdf), [repository](https://github.com/egraphs-good/egglog).

**Stitch directly addresses learning reusable computational structure.** It takes program corpora and extracts abstractions that can be called by rewritten programs; later abstractions can build on earlier ones. Its optimization criterion concerns program representation, so runtime or economic benefit needs separate measurement. [Paper](https://arxiv.org/pdf/2211.16605), [repository](https://github.com/mlb2251/stitch).

**DreamCoder combines library growth and learned search.** It is important prior art for accumulating reusable capabilities and applying them to later tasks. Adopting its entire research stack is unnecessary for the first experiment; its design is relevant to defining what is actually new. [Paper](https://arxiv.org/pdf/2006.08381), [repository](https://github.com/ellisk42/ec).

**gg is close prior art for recursive executable references.** It packages computations and dependencies as thunks and resolves dependent work over functional containers. The original system and a continuation repository deserve inspection before designing a new recursive computation-descriptor format or distributed evaluator. [USENIX paper](https://www.usenix.org/conference/atc19/presentation/fouladi), [original repository](https://github.com/StanfordSNR/gg), [continuation](https://github.com/gg-project/gg).

**Ruler reaches into automatic relationship discovery.** It infers rewrite rules for a specified domain/interpreter. Validation mechanisms vary: exhaustively checked Boolean identities, solver-backed results and fuzz-tested candidates carry different assurance. It supplies a mechanism to evaluate rather than a general proof oracle. [Artifact](https://github.com/uwplse/ruler/blob/main/OOPSLA21.md).

**Adaptive selection also has reusable machinery.** OpenTuner allocates tuning effort among competing search techniques; Halide uses search and symbolic/learned cost models for schedule selection. Neither is a universal RIV resolver, but they show why the selector should begin with established methods and a well-defined objective. [OpenTuner](https://opentuner.org/), [Halide paper](https://halide-lang.org/papers/halide_autoscheduler_2019.pdf).

## 3. Existing architectures that combine capabilities

| Existing architecture | Already combined | Important remaining boundary |
|---|---|---|
| redun | Expression graphs, task hashing, cached reductions, provenance, distributed executors | No general semantic equivalence discovery or automatic abstraction learning |
| gg | Executable thunks, recursive dependencies, content identities, remote execution | No general economic selector across learned equivalent representations |
| egglog | Equality, inference, incremental matching, extraction | Does not supply the complete persistent execution/storage substrate |
| DreamCoder | Synthesis, learned abstractions, compositional library growth, neural search | Domain-specific research system; deployment economics remain untested here |
| Fumola | Named incremental computation, reusable demanded graph, graph inspection, Wasm interface | Experimental language; no complete RIV capability combination established |
| Nix / build-system research | Dependencies, substitution, rebuild decisions, scheduling and trace reuse | Build semantics do not automatically cover runtime effects and equivalences |

**Finding:** this screen found several substantial partial architectures. It did not establish that one existing system meets the full intended requirement. It also did not establish that combining these mechanisms is novel. The next novelty question needs an exact claim, workload and comparison set.

The most useful conceptual separation comes from *Build Systems à la Carte*: scheduling work and deciding whether work must be rebuilt are separable design choices. Add representation choice as another explicit decision; do not bury all three inside an undefined resolver. [Research and executable framework](https://www.microsoft.com/en-us/research/publication/build-systems-la-carte/).

## 4. Corrections to the preliminary proposal

- **Content identity and semantic equivalence are separate.** Unison hashes structured terms without names. It does not assign every mathematically equivalent implementation the same hash. Likewise an e-class's local ID is not a universal portable identifier. [Unison hash definition](https://www.unison-lang.org/docs/language-reference/hashes/).
- **egg/egglog apply supplied rules and analyses.** They do not automatically discover every valid relationship. Ruler and synthesis tools address parts of rule discovery. Their rules still need valid arithmetic/effect assumptions.
- **Portable execution needs a determinism policy.** Wasmtime documents host imports, NaN canonicalization, relaxed SIMD, memory/table growth and interruption as concerns. Fuel bounds guest execution; it does not measure energy or guarantee identical elapsed time. [Deterministic execution](https://docs.wasmtime.dev/examples-deterministic-wasm-execution.html).
- **Nix describes and isolates dependencies; reproducibility still needs checking.** Ordinary input-addressed derivations and content-addressed outputs are distinct. Nix check mode can report non-reproducible outputs. [Official manual](https://nix.dev/manual/nix/2.29/command-ref/nix-build.html).
- **Compressed-domain operations are operator-specific.** Succinct provides queries over a compressed self-index. Grammar-compressed algorithms can avoid full expansion for particular operations, with model-specific complexity bounds. Neither establishes that arbitrary computation becomes cheap on arbitrary compressed data. [Succinct paper](https://www.cs.cornell.edu/~ragarwal/pubs/succinct.pdf), [lower-bound research](https://arxiv.org/abs/2307.08833).
- **A recipe can reconstruct an object the receiver never stored in full.** Its sufficiency depends on accessible interpreter/recipe/dependencies and parameters. A short code such as 3214 can be a local alias, but its meaning must exist in shared or retrievable state. Account for that state without forcing compression to be the project's objective.
- **Maintenance affects selection.** The Rust Adapton library is archived; the current project site points to experimental Fumola. Souper is also archived. They remain valuable prior art, with a different adoption cost from maintained infrastructure. [Adapton library](https://github.com/Adapton/adapton.rust), [Fumola](https://github.com/Adapton/fumola), [Souper](https://github.com/google/souper).

Algorithmic information theory is useful for stating conditional description length relative to shared knowledge. Exact Kolmogorov complexity is uncomputable in general; it cannot be an exact universal selection algorithm. MDL provides practical model-description objectives but does not by itself account for execution cost. [Formalization](https://www.trustworthy.systems/publications/abstracts/Catt_Norrish_21.abstract), [MDL tutorial](https://arxiv.org/abs/math/0406077).

## 5. Smallest useful integration and what was executed

**Minimum for testing representation-aware reuse: egglog + redun.** Use ordinary existing execution beneath them. **Add Wasmtime only when portable guest execution is part of the test.** This third component was included in the local smoke check to establish that an existing VM can fit the connection.

The adapter contains a restricted expression-to-Wasm lowering for one variable, constants, addition and multiplication. It uses only supplied identity rules under wrapping 64-bit arithmetic. It is an experiment harness, not a new general compiler or full architecture.

| Local check | Observed result |
|---|---|
| Three equivalent expression forms | One extracted term and one identical Wasm module |
| Same input across the three forms | One actual guest task execution, two reused results |
| Changed input | One new execution and correct changed result |
| New scheduler object, same SQLite database | Old result reused with zero additional guest executions |
| Same executor/cache without normalization | Three guest task executions for the three original forms |
| Direct checks outside caching | 300 input/form checks; zero mismatches |
| Stitch upstream toy example | Learned fn_0(#0) = (#0 #0 #0), reused in two rewritten programs |

Versions: Python 3.12.14, egglog 14.0.0, redun 0.51.1, Wasmtime 51.0.0, stitch-core 0.1.29. Exact installed dependencies, source harnesses and logs are included in the research bundle.

The integration prediction was recorded before harness implementation. Its first run failed because the adapter omitted redun's database initialization call; after correction it passed with unchanged predictions. This is integration debugging, not an upstream failure.

**What this establishes:** these existing packages can interoperate on a constrained example, and Stitch's toy abstraction-learning behavior is locally reproducible.

**What it does not establish:** general speedup, profitable reuse after planning overhead, automatic rule discovery, fine-grained dependency repair, network interoperability, cross-device determinism, compressed-domain execution, or novelty. Full upstream suites were not run. The restart test created a new scheduler object, not a separate process or device.

The three-versus-one comparison is a narrow ablation. An optimizing compiler or SymPy can remove these identities too, so it would be misleading to present the count reduction as a competitive computational breakthrough.

## 6. Where custom work should concentrate

| Desired capability | Smallest remaining work |
|---|---|
| Correct cross-component interpretation | Typed semantic contract: arithmetic, effects, errors, exactness, inputs and environment |
| Persistent references to reusable representations | Versioned descriptor adapter; distinguish representation, derivation and result identities |
| Adaptive resolution | Thin candidate interface over execution, reuse, repair, retrieval and specialization |
| Resource-aware selection | Measure end-to-end costs and tune an existing selection method |
| Useful capability accumulation | Validate/admit/prune abstractions from Stitch or another existing learner |
| Demonstrable architectural value | A bounded claim and benchmark against the strongest applicable existing system |

One useful proposed accounting interface is total lookup + planning + compilation + execution/repair + materialization/transfer + validation + amortized retained-state cost. Keep time, bytes, money and energy separately until an explicit conversion is chosen. Hashing and preserving a growing graph can cost more than recomputation on small or unrelated tasks.

For integrity, standard digests verify retrieved bytes against an expected identity. Correct execution requires trusted recomputation, proof, attestation or another separately specified mechanism; a result hash alone does not establish that its computation was correct.

## 7. Next experiment and decision gate

The next experiment should ask whether representation-aware reuse lowers total cost against **optimized execution plus memoization**, not merely whether a cache can hit. Use related workloads, changed-leaf workloads, unrelated workloads and cases that cause rewrite expansion. Compare direct optimized execution, memoization, SymPy/CSE where semantics match, egglog plus the same cache, and optionally a Stitch-extended library.

Measure planning/learning time, cold and warm execution, p50/p95 latency, memory, retained state, transfer and validation. Split expression families between training and held-out evaluation. Commit numerical predictions before implementing that benchmark. The supplied benchmark specification proposes explicit correctness and benefit thresholds; none of those future measurements has been performed.

Add Salsa for a query/dependency-repair hypothesis, or Differential Dataflow for a changing relational hypothesis. Add Stitch after the fixed-library baseline is established. Add distributed execution and compressed-query backends only when their particular claims are being tested. This preserves the full capability goal while keeping each experiment interpretable.

## 8. License and commercial-use screen

The registry records initial license evidence, with unresolved entries explicitly marked. MIT/BSD/Apache components offer permissive starting points subject to their terms. Nix's LGPL, the older Adapton library's MPL, original gg's GPL and original SDSL-lite's GPL require different integration/distribution analysis. Forks, dependencies, data and hosted services must be checked separately.

CompressAI uses BSD-3-Clause-Clear and explicitly grants no patent rights; it should not be treated as an ordinary BSD entry with patent clearance. This pass does not establish commercial freedom to operate. [License](https://github.com/InterDigitalInc/CompressAI/blob/master/LICENSE).

## 9. Handoff and research registry

The accompanying ZIP contains the capability matrix; 33 structured discovery cards in Markdown, JSON and CSV; architectural gaps; proposed benchmark and token-reading budgets; rejected assumptions; executed harnesses, package versions, results and logs. Each discovery records its source, capability, implementation status, principle, dependencies, license screen, measurements, limitations, integration route, eliminated custom work, remaining gap and smallest test.

Start with RESEARCH_INDEX.md. Reuse the findings rather than rereading entire repositories. Before adoption, pin a release/commit, resolve any outstanding license/dependency questions, and run the relevant upstream checks. The current recommendation is a minimal research integration around egglog and redun, with Wasmtime as the tested optional execution backend and Stitch as the next capability-growth candidate.
