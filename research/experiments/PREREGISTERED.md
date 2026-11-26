# Integration smoke test — registered before implementation
Date: 2026-11-26
Claim: egglog extraction can feed an existing redun result cache and a Wasmtime integer evaluator without a new VM, equivalence engine, or workflow scheduler.
Domain: one variable, integer constants, add, multiply; wrapping 64-bit arithmetic; only identities x+0=x and x*1=x.
Test: normalize three syntactically different expressions equivalent to x+5; lower extracted terms into Wasm; invoke through redun. Repeat x=7, change x=8, restart scheduler with the same SQLite database.
Prediction: three forms produce one identical extracted term and one Wasm module; x=7 produces 12 with one guest task execution; x=8 produces 13 with one additional execution; restarting scheduler reuses the x=7 result with zero additional executions. Zero mismatches on 100 deterministic integer input samples per form, checked outside caching.
Baseline: same redun/Wasmtime adapter using original expressions, with no egglog normalization. Predict three guest executions on x=7. This isolates syntactic normalization only. A compiler optimizer or a symbolic algebra simplifier is a stronger performance baseline and is required for a future benchmark.
Kill: any output mismatch, stale result after input change, failure of persisted reuse, or inability to connect the public APIs. Passing establishes interoperability only. No speedup, scalability, cross-platform determinism, automatic rule discovery, or architectural novelty claim follows.
