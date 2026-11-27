#!/usr/bin/env python
"""The persistent accumulating e-graph, run in its own process.

This arm is isolated because it has twice exhausted memory hard enough that
the Rust side aborts the interpreter rather than raising a catchable Python
error — once on six two-term expressions at 4 saturation iterations. Run in
process, it takes the whole experiment down with it. Here it gets its own
RLIMIT_AS, and a death is recorded as a result rather than losing the run.

It is the architecture's own design: one e-graph that accumulates structure
across requests, asked whether each new request is already equal to something
it holds. A fresh e-graph per request cannot serve as a cache-key normaliser,
because egglog proves a*b == b*a yet extracts different representatives from
two separate e-graphs.
"""
from __future__ import annotations

import json
import resource
import signal
import sys
import time

MEM_CAP_MB = int(sys.argv[2]) if len(sys.argv) > 2 else 2048
resource.setrlimit(resource.RLIMIT_AS, (MEM_CAP_MB * 1024 * 1024,) * 2)

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import exp008_arms as A                                      # noqa: E402
from exp008_workload import build, evaluate                  # noqa: E402

ITERS = int(sys.argv[1]) if len(sys.argv) > 1 else 2
OUT = "experiments/exp008_persistent.json"


def main():
    signal.signal(signal.SIGALRM, A._alarm)
    A.EGG_ITERS = ITERS
    requests, _ = build()
    pe = A.PersistentEgraph(iters=ITERS)
    cache = {}
    st = {"arm": "memo_egglog_persist", "iters": ITERS,
          "mem_cap_mb": MEM_CAP_MB, "requests": len(requests),
          "hits": 0, "executed": 0, "ops_executed": 0, "skipped": 0,
          "errors": 0, "norm_ms": 0.0, "exec_ms": 0.0,
          "requests_done": 0, "completed": False, "mismatches": 0}
    t0 = time.perf_counter()
    try:
        for r in requests:
            e = A.tuple_of(r["expr"])
            tn = time.perf_counter()
            try:
                label = pe.canonical_for(e)
            except A._Skipped:
                st["skipped"] += 1
                label = None
            except Exception:
                st["errors"] += 1
                label = None
            st["norm_ms"] += (time.perf_counter() - tn) * 1000.0
            key = (label, A.env_key(e, r["env"])) if label else None
            if key is not None and key in cache:
                st["hits"] += 1
                val = cache[key]
            else:
                c = [0]
                te = time.perf_counter()
                val = evaluate(e, r["env"], c)
                st["exec_ms"] += (time.perf_counter() - te) * 1000.0
                st["ops_executed"] += c[0]
                st["executed"] += 1
                if key is not None:
                    cache[key] = val
            if val != evaluate(e, r["env"]):
                st["mismatches"] += 1
            st["requests_done"] += 1
            if st["requests_done"] % 25 == 0:
                print(f"    {st['requests_done']}/{len(requests)} "
                      f"classes={len(pe.roots)} hits={st['hits']} "
                      f"rss={resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024:.0f}MB",
                      flush=True)
        st["completed"] = True
    except MemoryError as ex:
        st["failure"] = f"MemoryError at request {st['requests_done']}: {ex}"
    except Exception as ex:
        st["failure"] = f"{type(ex).__name__} at request {st['requests_done']}: {str(ex)[:150]}"
    st["wall_s"] = time.perf_counter() - t0
    st["classes"] = len(pe.roots)
    st["saturations"] = pe.saturations
    st["peak_rss_mb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    with open(OUT, "w") as fh:
        json.dump(st, fh, indent=2)
    print(f"  persistent: done={st['completed']} "
          f"{st['requests_done']}/{len(requests)} classes={st['classes']} "
          f"hits={st['hits']} rss={st['peak_rss_mb']:.0f}MB "
          f"{st.get('failure','')}")


if __name__ == "__main__":
    main()
