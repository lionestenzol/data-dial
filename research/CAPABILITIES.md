# Capability-to-prior-art matrix

The capability remains authoritative. Classification concerns the requirement as scoped here, not a claim that an entire architecture is solved. Sources and dependency/license/experiment details are in PRIOR_ART.md and RESEARCH_INDEX.json.

| Desired capability | Established terminology / strongest candidates | Classification | What actually needs implementation |
|---|---|---|---|
| References to executable definitions and their dependencies | Content-addressed code; Unison | Partially solved | Descriptor adapter and semantics/environment identity; adopt full language only if justified |
| References to references across devices | Merkle DAG, CID, dependency closure; IPLD/IPFS, gg | Already solved for addressing; partial for executable resolution | Canonical schema and resolver policy |
| Equivalent computational representations | Congruence closure, equality saturation; egg/egglog | Multiple solutions | Domain operations, valid rules, extraction cost |
| Logical inference over representations | Datalog, lattice-based fixpoints; egglog | Already solved within supported logic | Facts and domain rules |
| Reuse after small changes | Demand-driven incremental computation; Salsa/Adapton/Fumola | Multiple solutions | Query boundaries and identity/update contracts |
| Recursive changing relation maintenance | Differential Dataflow | Already solved for suitable collection programs | Encode workload and delta semantics |
| Reuse previous task results and relationships | Graph reduction, constructive traces; redun/gg/build systems | Partially solved | Complete task dependencies and cross-representation adapter |
| Portable virtual processor | WebAssembly runtime; Wasmtime/Wasmi | Multiple solutions | Restricted ABI, explicit arithmetic and host behavior |
| Deterministic reconstruction | Hermetic execution, dependency closure; Wasm plus Nix | Partially solved | Define exact output contract and reproducibility checks |
| Distributed caching/execution | Remote Execution API; Buildbarn | Already solved for declared build actions | Action adapter, deployment policy and trust boundary |
| Peer transport/discovery | libp2p | Already solved for networking | Content protocol, availability and authorization policy |
| Integrity of retrieved bytes | Cryptographic digests/Merkle verification | Already solved | Use libraries; separately define result provenance/verification |
| Query compact objects without full materialization | Succinct/self-indexes, grammar-compressed algorithms, SDSL | Partially solved | Match each operator to representation; measure construction/update costs |
| Multi-level representations/hardware lowering | MLIR/IREE | Partially solved | Domain semantics and lowering; defer compiler framework until justified |
| Accumulate reusable capabilities | Library learning, abstraction learning; Stitch/DreamCoder | Partially solved | Admission/validation and held-out economic utility |
| Discover rules automatically | Rewrite-rule inference, synthesis; Ruler/Souper | Partially solved | Proof/validation conditions and search budget |
| Avoid repeated work with known parameters | Partial evaluation, specialization, supercompilation | Partially solved | Select safe specializations and amortization policy |
| Adaptive mechanism selection | Autotuning, query planning, portfolios; OpenTuner/Halide | Partially solved | Candidate adapters, measured cost features, drift handling |
| Substrate economics | MDL, amortized analysis, resource accounting | Partially solved | Multi-resource objective and empirical evaluation |
| Globally best representation for arbitrary programs | Program equivalence/shortest-program limits | Unresolved as general practical objective | Restrict domain, bounded search, sound rules; no universal guarantee |

“Research exists without a usable implementation” applies to particular compressed-domain operators if their papers fit but artifacts do not. It is not a reason to label all grammar-compressed computation unimplemented.
