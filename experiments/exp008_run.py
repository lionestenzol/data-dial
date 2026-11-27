#!/usr/bin/env python
"""Run experiment 008's arms. See EXP008_PREREGISTRATION.md.

Charges every arm for its own normalisation, cross-checks that all arms agree
on every request (the zero-mismatch threshold), and sweeps the simulated
per-operation cost to find the break-even of Y7.
"""
from __future__ import annotations

import json
import resource
import signal
import sys
import time

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import exp008_arms as A
from exp008_workload import build, evaluate

MEM_CAP_GB = 2.0            # declared in the pre-registration
OP_COST_SWEEP_US = (0.0, 1.0, 10.0, 100.0, 1000.0, 10000.0)
EGG_ITERS = 2               # set from the budget probe: 2 canonicalises in
                            # ~11 ms, 3 costs 120 ms, 4 exhausts memory


def peak_rss_mb():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def main(limit=None, with_persistent=True):
    signal.signal(signal.SIGALRM, A._alarm)
    A.EGG_ITERS = EGG_ITERS
    requests, meta = build()
    if limit:
        requests = requests[:limit]
    print(f"workload: {len(requests)} requests, "
          f"{meta['distinct_syntax']} distinct syntax forms", flush=True)

    out = {"meta": meta, "n_requests": len(requests), "arms": {},
           "config": {"EGG_ITERS": EGG_ITERS, "EGG_NODE_CAP": A.EGG_NODE_CAP,
                      "NORM_TIMEOUT_S": A.NORM_TIMEOUT_S,
                      "MEM_CAP_GB": MEM_CAP_GB,
                      "op_cost_sweep_us": list(OP_COST_SWEEP_US)}}

    # ---- reference values: direct evaluation, no cache, no normalisation ----
    ref = [evaluate(A.tuple_of(r["expr"]), r["env"]) for r in requests]

    for arm in A.ARMS:
        t0 = time.perf_counter()
        stats, results = A.run_arm(arm, requests)
        stats["wall_s"] = time.perf_counter() - t0
        stats["peak_rss_mb"] = peak_rss_mb()
        stats["mismatches"] = sum(1 for a, b in zip(results, ref) if a != b)
        del stats["per_request"]            # keep the file small; quantiles below
        _, res2 = None, None
        out["arms"][arm] = stats
        print(f"  {arm:<13} {stats['wall_s']:6.2f}s  exec={stats['executed']:>4} "
              f"hits={stats['hits']:>4} ops={stats['ops_executed']:>7} "
              f"norm={stats['norm_ms']:9.1f}ms mism={stats['mismatches']} "
              f"skip={stats['norm_skipped']} to={stats['norm_timeouts']} "
              f"err={stats['norm_errors']}", flush=True)

    # ---- per-case and per-split detail, re-run cheaply for quantiles -------
    detail = {}
    for arm in A.ARMS:
        stats, _ = A.run_arm(arm, requests)
        per = stats["per_request"]
        detail[arm] = {}
        for grp in ("case", "split"):
            for key in sorted({p[grp] for p in per}):
                xs = sorted(p["ms"] for p in per if p[grp] == key)
                detail[arm][f"{grp}:{key}"] = {
                    "n": len(xs), "total_ms": sum(xs),
                    "p50": xs[len(xs) // 2],
                    "p95": xs[min(int(0.95 * len(xs)), len(xs) - 1)]}
    out["detail"] = detail

    # ---- Y7: where does normalisation start paying? ------------------------
    sweep = {}
    for cost in OP_COST_SWEEP_US:
        sweep[str(cost)] = {}
        for arm in A.ARMS:
            stats, _ = A.run_arm(arm, requests, op_cost_us=cost)
            sweep[str(cost)][arm] = {"accounted_ms": stats["accounted_ms"],
                                     "ops": stats["ops_executed"]}
        best_base = min(sweep[str(cost)][a]["accounted_ms"]
                        for a in ("direct", "memo", "memo_canon"))
        sym = sweep[str(cost)]["memo_sympy"]["accounted_ms"]
        print(f"  op_cost={cost:>8.1f}us  best_baseline={best_base:10.1f}ms  "
              f"memo_sympy={sym:10.1f}ms  ratio={sym/best_base:6.2f}x", flush=True)
    out["op_cost_sweep"] = sweep

    # ---- the persistent e-graph, out of process ---------------------------
    # It has twice exhausted memory hard enough that the Rust side aborts the
    # interpreter instead of raising, which kills the whole run. Isolated.
    if with_persistent:
        import subprocess
        print("\n  persistent e-graph (separate process, own RLIMIT)...", flush=True)
        r = subprocess.run([sys.executable, "-I", "experiments/exp008_persistent.py",
                            str(EGG_ITERS), str(int(MEM_CAP_GB * 1024))],
                           capture_output=True, text=True, timeout=1800)
        print((r.stdout or "")[-600:], flush=True)
        try:
            out["arms"]["memo_egglog_persist"] = json.load(
                open("experiments/exp008_persistent.json"))
        except Exception:
            out["arms"]["memo_egglog_persist"] = {
                "arm": "memo_egglog_persist", "completed": False,
                "failure": "process died before writing results "
                           f"(exit {r.returncode})",
                "stderr_tail": (r.stderr or "")[-400:]}
            print(f"    process died, exit {r.returncode}", flush=True)

    out["peak_rss_mb_final"] = peak_rss_mb()
    with open("experiments/exp008_results.json", "w") as fh:
        json.dump(out, fh, indent=2)
    print(f"\npeak RSS {out['peak_rss_mb_final']:.0f} MB "
          f"(cap {MEM_CAP_GB*1024:.0f} MB)")
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--no-persistent", action="store_true")
    a = ap.parse_args()
    main(limit=a.limit, with_persistent=not a.no_persistent)
