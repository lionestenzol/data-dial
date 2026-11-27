# Prior-art discovery cards

Checked 2026-11-26. All integration assessments and smallest experiments are analyst proposals. Published measurements are author-reported unless explicitly marked locally executed. License entries are an initial source screen, not a transitive dependency or patent audit.

## Unison

- **url:** https://github.com/unisonweb/unison
- **capability:** Content-addressed executable definitions
- **implementation status:** Usable language/toolchain
- **principle:** Hash structured terms and dependency references independently of names
- **dependencies:** UCM/runtime; Haskell/Stack for source build
- **license screen:** MIT; bundled Data.Relation BSD-3-Clause; hosted Cloud terms separate
- **published measurements:** No comparable RIV benchmark established
- **limitations:** Structural identity does not imply semantic equivalence; language adoption and Cloud are separate decisions
- **integration method:** Run UCM as separate backend; exchange typed descriptors
- **custom work eliminated:** Custom content-addressed language/code database
- **remaining gap:** Cross-language identity, resolution policy, environment contracts
- **smallest experiment:** Rename a definition, then change its body; inspect hashes and dependency closure
- **additional sources:** https://www.unison-lang.org/docs/language-reference/hashes/
- **evidence:** Documented; not locally executed

## egg

- **url:** https://github.com/egraphs-good/egg
- **capability:** Equivalent expression storage and extraction
- **implementation status:** Rust library
- **principle:** E-graphs, congruence closure, rebuilding, e-class analysis
- **dependencies:** Rust/Cargo
- **license screen:** MIT
- **published measurements:** POPL 2021 case studies; not reproduced
- **limitations:** Rules supplied by developer; search growth; extracted cost need not predict latency *(the last clause is OUR INFERENCE, not stated by egg — verified absent from the repository and rustdoc at 73975c9; see research/findings/SELECTOR_GAP.md)*
- **integration method:** Embed typed DSL and cost function
- **custom work eliminated:** Custom e-graph and equality-saturation engine
- **remaining gap:** Sound domain rules and measured costs
- **smallest experiment:** Run upstream arithmetic example under node/time limits
- **additional sources:** https://arxiv.org/abs/2004.03082
- **evidence:** Documented; not locally executed

## egglog

- **url:** https://github.com/egraphs-good/egglog
- **capability:** Equality plus inference and incremental matching
- **implementation status:** Rust engine; Python bindings
- **principle:** Datalog-style fixpoints with equality and lattice analyses
- **dependencies:** Rust or Python egglog wheel
- **license screen:** MIT; bindings separately licensed MIT
- **published measurements:** PLDI 2023 math experiment reports 9.27x versus egg at iteration 100; workload-specific
- **limitations:** Incremental rule matching does not establish general deletion/invalidation of merged equalities
- **integration method:** Python bindings or Rust library; typed IR adapter
- **custom work eliminated:** Separate rewrite, logical inference, and matching implementations
- **remaining gap:** Versioned rules; safe updates; persistence and extraction economics
- **smallest experiment:** Normalize expressions and feed existing execution cache
- **additional sources:** https://ztatlock.net/pubs/2023-pldi-egglog/2023-pldi-egglog.pdf
- **evidence:** Documented + locally executed constrained integration smoke test; see experiments/results.json

## redun

- **url:** https://github.com/insitro/redun
- **capability:** Hashed tasks, result reuse, provenance, lazy workflows
- **implementation status:** Python workflow engine
- **principle:** Graph reduction and cached task evaluation
- **dependencies:** Python, SQLAlchemy/database; optional cloud executors
- **license screen:** Apache-2.0
- **published measurements:** No comparable RIV speedup established
- **limitations:** Correctness depends on declaring relevant inputs/code/environment; Python is not a sandbox
- **integration method:** Decorate pure task boundaries; reuse persistent database
- **custom work eliminated:** Custom task scheduler, historical call graph, result cache
- **remaining gap:** Semantic equivalence across tasks; complete environment identity
- **smallest experiment:** Repeat task, change input, restart scheduler and inspect executions
- **additional sources:** https://insitro.github.io/redun/design.html
- **evidence:** Documented + locally executed constrained integration smoke test; see experiments/results.json

## Adapton Rust / nominal Adapton

- **url:** https://github.com/Adapton/adapton.rust
- **capability:** Demand-driven reuse of dependency structure
- **implementation status:** Rust library archived September 2026; historical OCaml artifacts
- **principle:** Named thunks and demanded computation graphs
- **dependencies:** Rust; OCaml for separate paper artifact
- **license screen:** Rust MPL-2.0; other artifacts require their own license check
- **published measurements:** PLDI 2014/OOPSLA 2015 evaluations; not reproduced
- **limitations:** Research artifact maintenance; names require disciplined identity
- **integration method:** Reference algorithm or isolated library trial
- **custom work eliminated:** Dependency recording and demand-driven change propagation
- **remaining gap:** Persistence and cross-device identity
- **smallest experiment:** Change one tree leaf and count forced thunks
- **additional sources:** https://adapton.org/
- **evidence:** Documented; not locally executed

## Fumola

- **url:** https://github.com/Adapton/fumola
- **capability:** Language with inspectable reusable computation graph
- **implementation status:** Current experimental Adapton implementation
- **principle:** Named graph repair with graphical/simple execution modes
- **dependencies:** Nightly Rust; wasm-bindgen for browser
- **license screen:** Apache-2.0
- **published measurements:** Examples and CI tests; no independent performance result established
- **limitations:** Experimental language; nightly toolchain; current does not imply mature
- **integration method:** Separate process or published Wasm/JavaScript interface
- **custom work eliminated:** New experimental incremental interpreter
- **remaining gap:** Fit to RIV representation and persistent interchange
- **smallest experiment:** Run same named thunk before/after cell edit; compare execution modes
- **additional sources:** 
- **evidence:** Documented; not locally executed

## Salsa

- **url:** https://github.com/salsa-rs/salsa
- **capability:** On-demand selective recomputation
- **implementation status:** Rust framework
- **principle:** Memoized queries with dependency validation across revisions
- **dependencies:** Rust; pin compatible toolchain/API
- **license screen:** Apache-2.0 OR MIT
- **published measurements:** No cross-project numerical baseline established
- **limitations:** Pure query boundary; not a distributed persistent computation store
- **integration method:** Embed tracked queries around planner computations
- **custom work eliminated:** Query memoization and dependency invalidation
- **remaining gap:** Cross-session persistence and distributed identity
- **smallest experiment:** Update one input; verify unrelated queries remain memoized
- **additional sources:** https://salsa-rs.github.io/salsa/
- **evidence:** Documented; not locally executed

## Differential Dataflow

- **url:** https://github.com/TimelyDataflow/differential-dataflow
- **capability:** Incremental recursive relational computation
- **implementation status:** Rust framework over Timely Dataflow
- **principle:** Weighted collections and partially ordered timestamps
- **dependencies:** Rust, Timely Dataflow
- **license screen:** MIT
- **published measurements:** Papers and examples supplied; no RIV result reproduced
- **limitations:** Requires dataflow reformulation; retained state and update fan-out can be costly
- **integration method:** Use for changing relation/graph workloads
- **custom work eliminated:** Custom delta propagation for recursive collections
- **remaining gap:** Mapping arbitrary procedures into collection operators
- **smallest experiment:** Insert/delete edge in reachability query; compare full rebuild
- **additional sources:** https://timelydataflow.github.io/differential-dataflow/
- **evidence:** Documented; not locally executed

## Nix

- **url:** https://github.com/NixOS/nix
- **capability:** Dependency closure and reproducible environment description
- **implementation status:** Established package/build system
- **principle:** Derivations, immutable store, substitution
- **dependencies:** Nix daemon/store and platform tooling
- **license screen:** LGPL-2.1; packaged software licenses separate
- **published measurements:** Official reproducibility project measures builds; no universal guarantee
- **limitations:** Input-addressed store paths common; deterministic dependency references do not force deterministic outputs
- **integration method:** Pin experiment environment and artifact closure
- **custom work eliminated:** Custom package/dependency resolver and environment builder
- **remaining gap:** Runtime semantic equivalence and adaptation
- **smallest experiment:** Rebuild derivation in check mode and compare outputs
- **additional sources:** https://nix.dev/manual/nix/2.29/command-ref/nix-build.html
- **evidence:** Documented; not locally executed

## Buildbarn

- **url:** https://github.com/buildbarn/bb-storage
- **capability:** Remote content storage, action cache, build execution
- **implementation status:** Multiple production-oriented services
- **principle:** Remote Execution API; digest-addressed blobs/actions
- **dependencies:** Go/Bazel; storage plus scheduler/workers for execution
- **license screen:** Apache-2.0 repository licenses; dependency review pending
- **published measurements:** No comparable end-to-end RIV benchmark established
- **limitations:** bb-storage alone does not execute; action identity assumes complete declared inputs
- **integration method:** Remote Execution API client; use bb-remote-execution when needed
- **custom work eliminated:** Custom remote build cache and worker protocol
- **remaining gap:** Non-build execution semantics and adaptive placement
- **smallest experiment:** Cache one action; repeat on another worker; change input
- **additional sources:** https://github.com/buildbarn/bb-remote-execution
- **evidence:** Documented; not locally executed

## Wasmtime

- **url:** https://github.com/bytecodealliance/wasmtime
- **capability:** Portable bounded execution
- **implementation status:** Maintained Wasm runtime
- **principle:** Validated Wasm, sandbox boundary, fuel metering
- **dependencies:** Runtime/bindings; source build Rust
- **license screen:** Apache-2.0 WITH LLVM-exception; Python binding license separately checked on adoption
- **published measurements:** No RIV speedup measured
- **limitations:** Determinism needs controlled imports, NaNs, relaxed SIMD, allocation/growth; fuel is not wall time or energy
- **integration method:** Embed small Wasm modules with explicit host interface
- **custom work eliminated:** Custom VM/interpreter and instruction fuel mechanism
- **remaining gap:** Application ABI, host determinism, resource cost model
- **smallest experiment:** Same integer module and fuel on two architectures
- **additional sources:** https://docs.wasmtime.dev/examples-deterministic-wasm-execution.html
- **evidence:** Documented + locally executed constrained integration smoke test; see experiments/results.json

## Wasmi

- **url:** https://github.com/wasmi-labs/wasmi
- **capability:** Lightweight interpreter for constrained hosts
- **implementation status:** Rust interpreter; no_std support
- **principle:** Portable interpretation with fuel
- **dependencies:** Rust; optional WASI integration
- **license screen:** MIT OR Apache-2.0
- **published measurements:** Upstream claims spec-test compliance and links benchmarks; not reproduced
- **limitations:** Lower footprint does not imply faster execution; imports still matter
- **integration method:** Alternative backend behind same restricted Wasm ABI
- **custom work eliminated:** Embedded VM development
- **remaining gap:** Hardware fit and runtime-specific feature parity
- **smallest experiment:** Run identical module in Wasmi/Wasmtime; compare memory/startup/time
- **additional sources:** 
- **evidence:** Documented; not locally executed

## Succinct

- **url:** https://github.com/amplab/succinct
- **capability:** Search/count/access compressed data
- **implementation status:** Research implementation; compatibility needs evaluation
- **principle:** Compressed self-index with query support
- **dependencies:** Java/Maven; Scala/Spark for distributed integration
- **license screen:** Apache-2.0
- **published measurements:** NSDI 2015 reports order-of-magnitude memory reduction on selected datasets
- **limitations:** Specific query operations, not general program execution; construction/update costs
- **integration method:** Separate searchable representation backend
- **custom work eliminated:** Custom compressed text search engine
- **remaining gap:** Mapping desired queries and current workload suitability
- **smallest experiment:** Compare substring count/extract with raw scan and modern compressed index
- **additional sources:** https://www.cs.cornell.edu/~ragarwal/pubs/succinct.pdf
- **evidence:** Documented; not locally executed

## Grammar-compressed computation

- **url:** https://arxiv.org/abs/2307.08833
- **capability:** Operations without full expansion
- **implementation status:** Research family; no universal runtime identified
- **principle:** Straight-line grammars and compressed-domain algorithms
- **dependencies:** Algorithm-specific grammar representation and indexes
- **license screen:** Paper access rights distinct from implementation license
- **published measurements:** Model-specific upper/lower bounds; not a benchmark
- **limitations:** Complexity depends on compressed and expanded sizes; some operations stay expensive
- **integration method:** Add only algorithms matching required operators
- **custom work eliminated:** Re-deriving supported compressed-domain algorithms
- **remaining gap:** Usable implementation for exact workload
- **smallest experiment:** Random access/count on repeated and incompressible inputs
- **additional sources:** https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.FSTTCS.2016.36
- **evidence:** Documented; not locally executed

## SDSL-lite

- **url:** https://github.com/simongog/sdsl-lite
- **capability:** Succinct bitvectors, rank/select and indexes
- **implementation status:** C++ library; fork choice matters
- **principle:** Near-information-bound structures with efficient primitives
- **dependencies:** C++11/CMake and bundled dependencies
- **license screen:** Original simongog repository GPLv3; do not assume forks share license
- **published measurements:** Repository provides construction/query benchmarks; not reproduced
- **limitations:** Operation-specific structures; distribution fit and license differ by fork
- **integration method:** Native extension or service for indexed data
- **custom work eliminated:** Custom succinct primitive implementations
- **remaining gap:** Mutable graph integration and serialization contract
- **smallest experiment:** Benchmark rank/select and indexed search on target corpus
- **additional sources:** 
- **evidence:** Documented; not locally executed

## IREE

- **url:** https://github.com/iree-org/iree
- **capability:** Compilation and execution across hardware targets
- **implementation status:** Compiler/runtime toolkit
- **principle:** MLIR lowering and hardware abstraction
- **dependencies:** Compiler tools, runtime; device driver/backend as selected
- **license screen:** Apache-2.0 WITH LLVM-exception
- **published measurements:** Project benchmark infrastructure exists; no RIV result established
- **limitations:** Targets supported ML/numerical programs; portable does not mean bitwise-identical floats
- **integration method:** Optional numerical backend once workloads justify it
- **custom work eliminated:** Custom ML compiler and accelerator runtime
- **remaining gap:** RIV IR lowering and numerical semantics
- **smallest experiment:** Compile one small tensor kernel to CPU and one GPU
- **additional sources:** https://iree.dev/
- **evidence:** Documented; not locally executed

## MLIR

- **url:** https://mlir.llvm.org/
- **capability:** Reusable multi-level compiler representations
- **implementation status:** LLVM compiler framework
- **principle:** Dialects, verification, transformations and lowering
- **dependencies:** LLVM/MLIR C++ build; optional Python bindings
- **license screen:** Apache-2.0 WITH LLVM-exception
- **published measurements:** Infrastructure; no single relevant speedup claim
- **limitations:** Framework does not supply semantics or universal optimizer for a new dialect
- **integration method:** Reuse existing dialects; create dialect only if necessary
- **custom work eliminated:** Compiler IR/pass infrastructure
- **remaining gap:** Domain operations, validity and lowering
- **smallest experiment:** Represent small typed program; verify and lower existing operations
- **additional sources:** 
- **evidence:** Documented; not locally executed

## IPLD / IPFS content addressing

- **url:** https://ipld.io/
- **capability:** Hash-linked references and portable block representation
- **implementation status:** Specifications and multiple implementations
- **principle:** CIDs, codecs, multihash, Merkle DAG
- **dependencies:** Select codec/library; IPFS node only if network retrieval needed
- **license screen:** Per-implementation license; specifications are not a package license
- **published measurements:** No RIV performance evidence established
- **limitations:** Digest identifies content, not availability or execution; immutable DAGs need separate mutable/versioned index
- **integration method:** Use canonical blocks/descriptors; resolve through local storage first
- **custom work eliminated:** Inventing identifier/codec/link format
- **remaining gap:** Execution semantics, cycle representation, availability
- **smallest experiment:** Transfer root plus missing blocks; verify hash and decode
- **additional sources:** https://docs.ipfs.tech/concepts/content-addressing/
- **evidence:** Documented; not locally executed

## libp2p

- **url:** https://github.com/libp2p/go-libp2p
- **capability:** Peer discovery and authenticated transport
- **implementation status:** Modular networking stack
- **principle:** Composable peer protocols/transports
- **dependencies:** Go; alternative language implementations separate
- **license screen:** Go repository MIT
- **published measurements:** No workload-specific network benchmark run
- **limitations:** Peer discovery is not result correctness or guaranteed availability
- **integration method:** Add only after local resolver semantics stabilize
- **custom work eliminated:** Custom transport, peer identity and connection stack
- **remaining gap:** Replication policy and result trust
- **smallest experiment:** Two local peers exchange verified descriptor and missing block
- **additional sources:** 
- **evidence:** Documented; not locally executed

## Algorithmic information theory

- **url:** https://www.trustworthy.systems/publications/abstracts/Catt_Norrish_21.abstract
- **capability:** Reason about program descriptions and shared knowledge
- **implementation status:** Theory; formal proofs exist
- **principle:** Conditional Kolmogorov complexity and invariance
- **dependencies:** Chosen machine/model; HOL4 if reproducing formal proof
- **license screen:** Theory is not a library; proof artifact rights separate
- **published measurements:** Formal uncomputability result; not a performance result
- **limitations:** Exact shortest-program objective is uncomputable in general
- **integration method:** Use bounded candidate programs and explicit shared state
- **custom work eliminated:** Pursuing an impossible exact universal minimizer
- **remaining gap:** Practical resource-bounded objective
- **smallest experiment:** Account for recipe, parameters, missing dependencies and execution cost
- **additional sources:** 
- **evidence:** Documented; not locally executed

## Minimum description length

- **url:** https://arxiv.org/abs/math/0406077
- **capability:** Penalize representation/library complexity
- **implementation status:** Theory with many domain-specific applications
- **principle:** Two-part description of model and data given model
- **dependencies:** Chosen code/model class and optimizer
- **license screen:** No implementation license implied by tutorial
- **published measurements:** No RIV benchmark; theory supplies objective
- **limitations:** Bit count alone omits latency, energy and training costs
- **integration method:** One term in library admission objective
- **custom work eliminated:** Ad hoc unpenalized model-growth metric
- **remaining gap:** Weights, horizon and resource accounting
- **smallest experiment:** Compare total library plus corpus description on held-out tasks
- **additional sources:** 
- **evidence:** Documented; not locally executed

## DreamCoder

- **url:** https://github.com/ellisk42/ec
- **capability:** Capability growth plus guided synthesis
- **implementation status:** Research system
- **principle:** Wake-sleep library learning and neural-guided program search
- **dependencies:** Python/ML dependencies, OCaml solver, submodules; some Rust tooling
- **license screen:** Main repository MIT; submodules/data separately screened
- **published measurements:** Evaluated across eight domains; not reproduced
- **limitations:** DSL/task definitions required; example fit does not prove universal equivalence
- **integration method:** Offline research reference; avoid full dependency stack initially
- **custom work eliminated:** Inventing entire library-learning/search loop
- **remaining gap:** Integration, held-out transfer and deployment economics
- **smallest experiment:** Small list-processing domain: compare fixed versus learned primitives
- **additional sources:** https://arxiv.org/pdf/2006.08381
- **evidence:** Documented; not locally executed

## Stitch

- **url:** https://github.com/mlb2251/stitch
- **capability:** Learn reusable program abstractions
- **implementation status:** Rust library and Python package
- **principle:** Corpus-guided top-down abstraction synthesis
- **dependencies:** Rust or stitch-core wheel
- **license screen:** MIT; dataset licenses separate
- **published measurements:** POPL 2023: 3–4 orders faster and 2 orders less memory than tested DreamCoder deductive learner
- **limitations:** Optimizes DSL corpus structure; shorter programs need not execute faster *(the last clause is OUR INFERENCE, not stated by Stitch — verified absent from the repository at 350804b)*
- **integration method:** Offline abstraction learner feeding versioned primitive library
- **custom work eliminated:** Custom structural abstraction miner
- **remaining gap:** Semantic validation and held-out net utility
- **smallest experiment:** Run upstream repeated-subterm example, then evaluate unseen programs
- **additional sources:** https://arxiv.org/pdf/2211.16605
- **evidence:** Documented + upstream two-program toy example reproduced; see experiments/stitch_results.json

## Ruler

- **url:** https://github.com/uwplse/ruler
- **capability:** Discover domain rewrite rules
- **implementation status:** Research Rust artifact
- **principle:** Enumerate candidates, cluster behavior, validate rules
- **dependencies:** Rust; solver/domain-specific tools; full artifact recommends substantial RAM
- **license screen:** MIT
- **published measurements:** OOPSLA 2021 artifact includes reproducible claims and Boolean toy test
- **limitations:** Validation may use fuzzing or solver depending domain; testing is not proof
- **integration method:** Offline rule proposal then trusted domain validation
- **custom work eliminated:** Hand-authoring every candidate rewrite
- **remaining gap:** Proof obligations, conditions and scalable search
- **smallest experiment:** Infer Boolean rules and exhaustively validate truth tables
- **additional sources:** https://github.com/uwplse/ruler/blob/main/OOPSLA21.md
- **evidence:** Documented; not locally executed

## Souper

- **url:** https://github.com/google/souper
- **capability:** Instruction-level replacement synthesis
- **implementation status:** LLVM superoptimizer; archived October 2025
- **principle:** SMT-backed refinement of LLVM IR fragments
- **dependencies:** Compatible LLVM/Clang, Z3, C++ build
- **license screen:** Apache-2.0 repository license; LLVM and solver dependencies separate
- **published measurements:** Published evaluations linked by repository; not reproduced
- **limitations:** Archived stack and LLVM poison/undefined-behavior semantics
- **integration method:** Offline comparison/reference for restricted bitvector DSL
- **custom work eliminated:** Custom bitvector peephole search
- **remaining gap:** Current toolchain and domain semantics
- **smallest experiment:** Find one missing integer optimization and validate with solver
- **additional sources:** 
- **evidence:** Documented; not locally executed

## Partial evaluation

- **url:** https://api.call-cc.org/5/doc/scheme0-pe
- **capability:** Reusable specialized computations
- **implementation status:** Established theory and diverse tools
- **principle:** Specialize program with known inputs; execute residual program later
- **dependencies:** Language-specific specializer/compiler; Scheme0 reference available
- **license screen:** Scheme0 implementation GPL-2.0-or-later; other tools separately licensed
- **published measurements:** No domain-independent speedup promised
- **limitations:** Code growth and specialization cost; dynamic inputs remain
- **integration method:** Use existing compiler specialization or JIT first
- **custom work eliminated:** Writing special-case execution engine for each parameter setting
- **remaining gap:** Choose when specialization amortizes
- **smallest experiment:** Fix one parameter in repeated workload; include specialization cost
- **additional sources:** 
- **evidence:** Documented; not locally executed

## Supercompilation / CHSC

- **url:** https://github.com/batterseapower/chsc
- **capability:** Transform recursive computations
- **implementation status:** Historical Haskell research prototype
- **principle:** Drive, fold and generalize program states
- **dependencies:** Compatible GHC and historical build stack
- **license screen:** BSD-3-Clause repository classification
- **published measurements:** Repository tests report compilation/runtime/allocation ratios
- **limitations:** Code explosion and termination issues explicitly documented
- **integration method:** Offline research branch only
- **custom work eliminated:** Reinventing recursive specialization techniques
- **remaining gap:** Safe bounded transformation on target DSL
- **smallest experiment:** Run smallest MapMapFusion example with strict time limit
- **additional sources:** 
- **evidence:** Documented; not locally executed

## CompressAI

- **url:** https://github.com/InterDigitalInc/CompressAI
- **capability:** Neural representations and learned compression
- **implementation status:** PyTorch research/evaluation library
- **principle:** Learned transforms and entropy coding
- **dependencies:** Python, PyTorch, native extensions; model artifacts
- **license screen:** BSD-3-Clause-Clear explicitly gives no patent license; weights separate
- **published measurements:** Repository evaluation tools; no RIV result
- **limitations:** Many use cases lossy; exact reconstruction requires suitable codec/model contract
- **integration method:** Separate optional media representation backend
- **custom work eliminated:** Custom neural codec training/evaluation infrastructure
- **remaining gap:** Exactness, model distribution and total resource economics
- **smallest experiment:** Compare rate/distortion plus encoder/decoder/model footprint
- **additional sources:** https://github.com/InterDigitalInc/CompressAI/blob/master/LICENSE
- **evidence:** Documented; not locally executed

## OpenTuner

- **url:** https://github.com/jansel/opentuner
- **capability:** Adaptive multi-objective mechanism tuning
- **implementation status:** Python research framework
- **principle:** Ensemble search with adaptive allocation of tuning budget
- **dependencies:** Python/database and experiment runner; compatibility screen pending
- **license screen:** MIT
- **published measurements:** Published program-tuning evaluations; not reproduced
- **limitations:** Needs controlled search space and reliable measurements
- **integration method:** Wrap candidate resolution policies in measurement interface
- **custom work eliminated:** Custom portfolio tuner and search budget allocator
- **remaining gap:** Online drift and application-specific cost objective
- **smallest experiment:** Tune among three fixed strategies against static policy
- **additional sources:** https://opentuner.org/
- **evidence:** Documented; not locally executed

## Halide autoscheduling

- **url:** https://halide-lang.org/papers/autoscheduler2019.html
- **capability:** Choose execution/reuse schedule by cost
- **implementation status:** Implemented compiler schedulers
- **principle:** Tree search and symbolic/learned performance model
- **dependencies:** Halide toolchain, autoscheduler plugin and hardware
- **license screen:** Inspect exact Halide release/dependencies before adoption
- **published measurements:** 2019 paper reports 75% average improvement over prior production scheduler without tuning
- **limitations:** Halide pipeline domain; benchmark gains do not transfer automatically
- **integration method:** Use as numerical backend or cost-model reference
- **custom work eliminated:** Original invention of every scheduling heuristic
- **remaining gap:** Cross-domain features and inference overhead
- **smallest experiment:** Compare generated and hand schedule including tuning cost
- **additional sources:** https://halide-lang.org/papers/halide_autoscheduler_2019.pdf
- **evidence:** Documented; not locally executed

## Build Systems à la Carte

- **url:** https://www.microsoft.com/en-us/research/publication/build-systems-la-carte/
- **capability:** Classify scheduler and reuse semantics
- **implementation status:** Research framework with executable Haskell code
- **principle:** Separate task scheduling from rebuilding/traces
- **dependencies:** Haskell for reference implementation
- **license screen:** Inspect linked code license before copying
- **published measurements:** Executable comparison framework; no universal speedup
- **limitations:** Build-oriented assumptions require adapting to runtime state
- **integration method:** Use taxonomy to define resolver/cache contract
- **custom work eliminated:** Inventing an ungrounded scheduler/reuse taxonomy
- **remaining gap:** Semantic equivalence and adaptive resource policy
- **smallest experiment:** Classify proposed resolver and simulate dependency edits
- **additional sources:** 
- **evidence:** Documented; not locally executed

## SymPy

- **url:** https://github.com/sympy/sympy
- **capability:** Symbolic mathematics and strong algebra baseline
- **implementation status:** Established Python computer algebra library
- **principle:** Symbolic simplification, algebra and common-subexpression elimination
- **dependencies:** Python and mpmath
- **license screen:** BSD repository license; verify exact distribution
- **published measurements:** No RIV benchmark run
- **limitations:** Mathematical assumptions and arithmetic semantics must match target DSL
- **integration method:** Use for mathematical operations and benchmark comparison
- **custom work eliminated:** Custom symbolic algebra implementation
- **remaining gap:** Non-algebraic domains and machine arithmetic semantics
- **smallest experiment:** Compare simplification/CSE with egglog on same valid identities
- **additional sources:** https://www.sympy.org/en/index.html
- **evidence:** Documented; not locally executed

## gg / Stanford Builder

- **url:** https://github.com/StanfordSNR/gg
- **capability:** Recursive content-addressed executable thunks
- **implementation status:** Research system; original and gg-project continuation
- **principle:** Functional containers, thunk dependency closure and recursive resolution
- **dependencies:** C++/Autotools or fork-specific CMake; protobuf, crypto and optional cloud
- **license screen:** Original repository GPL-3.0; fork and bundled dependencies require separate check
- **published measurements:** USENIX ATC 2019: compiler best-case 2–5x versus icecc; not reproduced
- **limitations:** Historical infrastructure; no automatic semantic equivalence or learned library
- **integration method:** Study thunk format; local backend before any cloud deployment
- **custom work eliminated:** Custom recursive executable-descriptor resolver and distributed thunk scheduler
- **remaining gap:** Modern integration and adaptive representation economics
- **smallest experiment:** Resolve small dependent thunk graph locally; change one leaf
- **additional sources:** https://www.usenix.org/conference/atc19/presentation/fouladi
- **evidence:** Documented; not locally executed

