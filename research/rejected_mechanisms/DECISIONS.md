# Rejected assumptions and deferred integrations

- Reject structural hash = semantic equivalence; retain hashes for identity and explicit equalities for proven relationships.
- Reject universal automatic equivalence discovery or exact shortest-program selection; use bounded, domain-specific mechanisms.
- Reject “WebAssembly is automatically fully deterministic”; apply the runtime's documented controls.
- Reject “content hash proves the computation was correct”; it verifies bytes against an expected digest.
- Reject using AST-size reduction as a runtime speedup measurement.
- Reject a need to build a language, VM, compiler, scheduler, distributed store and network stack before testing the central hypothesis.
- Defer full Unison adoption, MLIR/IREE, distributed Buildbarn/libp2p deployment, learned codecs and general grammar backends pending a workload that needs them.
- Keep Adapton/Souper historical artifacts as research references; their archived repositories are not default new infrastructure dependencies.
