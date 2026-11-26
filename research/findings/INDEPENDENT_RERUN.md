# Independent re-run of the bundled integration smoke test

Re-executed here rather than relayed, per RESEARCH_INDEX.md step 4.

**Environment differs from the original run.** Original: Python 3.12.14.
Here: Python 3.13.18, Linux 6.18.44 x86-64, same pinned wheels
(egglog 14.0.0, redun 0.51.1, wasmtime 51.0.0, stitch-core 0.1.29).

| Claim | Original | This re-run |
|---|---|---|
| Three forms of x+5 extract to one term | yes | yes — all three `Num.var("x") + Num(5)` |
| Unique Wasm modules | 1 | 1 |
| Guest executions, canonical, x=7 | 1 | 1 |
| Guest executions, baseline without normalisation | 3 | 3 |
| New execution after input changes to 8 | 1 | 1 |
| Additional executions after scheduler restart | 0 | 0 |
| Direct input/form checks, mismatches | 300 / 0 | 300 / 0 |
| Stitch reproduces `fn_0(#0) := (#0 #0 #0)` | yes | yes |

Normalisation took 5.9 ms for the three expressions.

**Status upgrade:** the interoperability claim is now independently
reproduced on a different Python minor version. That is slightly stronger
than the original ledger claimed, and it is still only interoperability.

**Unchanged limitations.** The ablation — the same adapter without egglog
normalisation — isolates removal of redundant syntax and nothing else. Three
syntactic forms of `x+5` would also collapse under any constant-folding
compiler or under SymPy's `cse`. This demonstrates that the plumbing works,
not that equality saturation beats an optimiser. The bundle says so itself
and NEXT_EXPERIMENT.md already specifies the stronger comparison.
