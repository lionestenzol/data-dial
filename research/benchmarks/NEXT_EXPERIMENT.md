# Next experiment — economic benefit beyond an optimized cache

Status: designed, not executed. Thresholds below are proposed decision criteria, not observed results.

Claim: choosing among equivalent executable recipes and dependency reuse yields lower total cost than a strong existing optimized memoization baseline on related workloads.

Use deterministic integer/bitvector workloads with repeated subcomputations. Include exact repeats, changed leaf inputs, algebraically equivalent formulations, unrelated requests and adversarial expansion cases. Split by expression family so held-out cases are not cosmetic variants of training programs.

Compare: (1) direct optimized execution, (2) same executor plus result memoization, (3) SymPy simplification/CSE where semantics match plus memoization, (4) egglog plus same memoization, (5) optional Stitch-extended library. Use an optimizing compiler for compiled workloads. The original smoke-test baseline only isolates removal of redundant syntax and is insufficient here.

Before implementing this benchmark, commit numerical predictions for every arm. Proposed decision thresholds: zero mismatches; at least 10% total-time improvement over the best applicable baseline on the declared primary workload; no more than 10% median regression on the unrelated workload; declare a memory cap before measurement. Otherwise narrow or stop the claimed advantage. These thresholds are engineering choices, not theoretical facts.

Include cold-start installation/model/library footprint separately; then measure cold compilation, warm-cache execution, edits, restart, and changing workload mix. Report p50/p95 latency, peak RSS, retained state, transferred bytes, task/operation counts and optimization/learning time. Avoid treating Wasm fuel as energy. Repeat sufficiently to report variance and all timeouts. Report break-even reuse count and any state growth.

A later two-device trial tests missing-dependency retrieval and byte-identical reconstruction. Compressed-query experiments should compare with current indexed implementations as well as decompress-and-query; use exact matching operators.
