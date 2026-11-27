# Verification ledger

Executed locally on one Linux x86-64 host, Python 3.12.14:

- egglog 14.0.0 + redun 0.51.1 + Wasmtime 51.0.0 integrated. Three forms of x+5 extracted to the same term and Wasm module. One guest task execution across three equivalent requests at x=7. Changing x to 8 caused one new execution. Creating a new scheduler instance against the same SQLite database reused x=7 with zero new executions.
- Same Wasmtime adapter without egglog normalization executed three distinct tasks. This is a deliberately narrow ablation, not the strongest optimization baseline.
- 300 direct input/form checks included signed 64-bit extremes; zero mismatches under wrapping arithmetic.
- Stitch-core 0.1.29 reproduced the upstream toy abstraction (#0 #0 #0), rewriting two programs to call fn_0. No held-out benefit or speedup measured.

The first integration attempt omitted redun Scheduler.load(), producing an assertion about an uninitialized database session. The adapter was corrected using the installed API/tests. initial_failure.log is retained. Predictions were unchanged.

Not executed: full upstream test suites; other listed projects; real network/distributed workloads; two architectures; ~~floating point~~; synthesis-based rule discovery; incremental dependency-graph repair; compressed-domain queries; learned codecs; end-to-end performance benchmark. Recreating a scheduler object is not an independently launched-process or second-device test.

**Update (experiments 003–006).** Floating point is struck from that list: 003–006 are entirely floating-point work — 913 FPCore expressions from FPBench and Herbie, with candidates admitted on relative error ≤ 1e-6 against a 30-digit reference before any cost comparison. See `experiments/FINDINGS.md` sections 003–006. Everything else on the line above remains not executed. `research/RESEARCH_INDEX.md` step 4 directs readers here before making an independently-verified claim, so this file must not under-report what has been run; status for all objectives is tracked in `research/OBJECTIVES.json`.

See experiments/PREREGISTERED.md, smoke.py, results.json, run.log, stitch_smoke.py, stitch_results.json and requirements.lock.txt. Package wheels were installed; entire upstream repositories were not cloned or audited. This was targeted interface inspection and reproduction.
