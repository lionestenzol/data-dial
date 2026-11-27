#!/usr/bin/env python
"""Experiment 007 - does charging compilation undo 006?

See EXP007_PREREGISTRATION.md. 006 charged evaluation time only; on a
compiling backend you cannot time a candidate without first compiling it, and
compilation measures ~685x one evaluation on this machine.

Backend: sympy.ccode scalar body + a hand-written loop, gcc -O2 -shared -fPIC,
loaded with ctypes. Zero new dependencies. Compilation cost is the wall time of
the gcc subprocess, which is the honestly chargeable quantity.

Candidates are REGENERATED, not reloaded from 006's srepr archive: srepr emits
no evaluate=False, so every powexp/ candidate would silently come back as its
base sibling. See the pre-registration.
"""
from __future__ import annotations

import ctypes
import json
import math
import os
import pathlib
import signal
import subprocess
import sys
import time

import numpy as np
import sympy as sp

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import exp004_regret_distribution as E4
from exp004_corpus import load as load_corpus

M_DEPLOY = 16384
PROBE_SIZES = (256, 1024, 4096)
REPEATS = 11
SEED = 7007
BAR = 200
BUILD = os.environ.get(
    "EXP007_BUILD",
    "/tmp/claude-0/-home-user-data-dial/44084ae5-9f89-5472-8890-929f5006120b/scratchpad/exp007/build")
FLAG_ARMS = {"O2": (), "ffast": ("-ffast-math",)}


# ------------------------------------------------------------------ C backend
def emit_c(expr, args):
    """Scalar body from ccode, loop written by hand.

    Arg names are remapped to p0..pN: FPCore permits hyphens and other
    characters C rejects. codegen's IndexedBase path is NOT used - it mistakes
    elementwise work for a tensor contraction and emits wrong O(n^2) code.
    """
    sub = {sp.Symbol(a, real=True): sp.Symbol(f"p{i}") for i, a in enumerate(args)}
    body = sp.ccode(expr.subs(sub, simultaneous=True), standard="C99")
    params = ", ".join(f"double p{i}" for i in range(len(args)))
    ptrs = ", ".join(f"const double *restrict A{i}" for i in range(len(args)))
    call = ", ".join(f"A{i}[i]" for i in range(len(args)))
    return (f"#include <math.h>\n"
            f"static inline double f({params}) {{ return {body}; }}\n"
            f"void kernel(long n, {ptrs}, double *restrict R) {{\n"
            f"    for (long i = 0; i < n; i++) R[i] = f({call});\n"
            f"}}\n")


# Every compiled object needs its OWN path, for a reason that cost a debugging
# session: the first two full runs died with SIGBUS at exactly core 50. The
# build tag was derived from len(rows), which only advances when a decision is
# KEPT, so the first skipped core made the next one reuse the same filenames.
# gcc -o then rewrote a .so that a previously loaded ctypes.CDLL still had
# mmap'd, and touching those pages is a bus error. Unlinking a mapped file is
# safe on Linux; overwriting one in place is not.
_UID = 0


def compile_c(src, tag, extra=()):
    """Returns (so_path, compile_ms). The subprocess wall time IS the charge."""
    global _UID
    _UID += 1
    tag = f"{tag}_{_UID}"
    os.makedirs(BUILD, exist_ok=True)
    c = os.path.join(BUILD, f"{tag}.c")
    so = os.path.join(BUILD, f"{tag}.so")
    with open(c, "w") as fh:
        fh.write(src)
    cmd = ["gcc", "-O2", "-shared", "-fPIC", "-march=native", *extra, c, "-o", so, "-lm"]
    t = time.perf_counter()
    r = subprocess.run(cmd, capture_output=True, text=True)
    ms = (time.perf_counter() - t) * 1000.0
    if r.returncode != 0:
        raise RuntimeError(r.stderr[:300])
    return so, ms


_ND = np.ctypeslib.ndpointer(dtype=np.float64, flags="C_CONTIGUOUS")


def load_kernel(so, nargs):
    lib = ctypes.CDLL(so)
    lib.kernel.argtypes = [ctypes.c_long] + [_ND] * (nargs + 1)
    lib.kernel.restype = None
    return lib.kernel


def time_kernel(fn, arrays, out, n, repeats=REPEATS):
    fn(n, *arrays, out)
    best = math.inf
    for _ in range(repeats):
        t = time.perf_counter()
        fn(n, *arrays, out)
        best = min(best, (time.perf_counter() - t) * 1000.0)
    return best


# ------------------------------------------------------------------ run
def run(limit=None):
    rng = np.random.default_rng(SEED)
    cores, cstats = load_corpus()
    if limit:
        cores = cores[:limit]
    print(f"corpus: {cstats['fpcores']} FPCores, {cstats['ok']} in scope, "
          f"running {len(cores)}", flush=True)

    rows, stats, t0 = [], {}, time.perf_counter()
    for idx, core in enumerate(cores):
        if idx % 50 == 0:
            print(f"  [{idx}/{len(cores)}] {time.perf_counter()-t0:.0f}s "
                  f"decisions={len(rows)}", flush=True)
        try:
            cands = E4.candidates_for(core.expr, stats)
        except Exception:
            continue
        if len(cands) < 2:
            continue

        acols = E4.sample_points(core, rng, E4.N_ADMIT)
        truth = E4.truth_values(core.expr, core.args, acols, stats)
        if truth is None or np.count_nonzero(np.isfinite(truth)) < 8:
            stats["no_truth"] = stats.get("no_truth", 0) + 1
            continue
        finite = np.isfinite(truth)
        aarr = [np.ascontiguousarray(acols[a]) for a in core.args]
        dcols = E4.sample_points(core, rng, M_DEPLOY)
        darr = [np.ascontiguousarray(dcols[a]) for a in core.args]
        parr = {m: [np.ascontiguousarray(E4.sample_points(core, rng, m)[a])
                    for a in core.args] for m in PROBE_SIZES}

        admitted = []
        for ci, (tag, e) in enumerate(cands):
            rec = {"tag": tag, "arms": {}}
            try:
                src = emit_c(e, core.args)
            except Exception:
                stats["ccode_error"] = stats.get("ccode_error", 0) + 1
                continue
            ok_any = False
            for arm, extra in FLAG_ARMS.items():
                try:
                    so, cms = compile_c(src, f"d{len(rows)}_c{ci}_{arm}", extra)
                    fn = load_kernel(so, len(core.args))
                except Exception:
                    stats[f"gcc_error_{arm}"] = stats.get(f"gcc_error_{arm}", 0) + 1
                    continue
                # accuracy admission, re-checked on the C output
                aout = np.empty(E4.N_ADMIT)
                with np.errstate(all="ignore"):
                    fn(E4.N_ADMIT, *aarr, aout)
                err = E4.rel_err(aout, truth)
                m = finite & np.isfinite(aout)
                if np.count_nonzero(m) < 8:
                    stats[f"reject_nonfinite_{arm}"] = stats.get(f"reject_nonfinite_{arm}", 0) + 1
                    continue
                worst = float(np.max(err[m]))
                if worst > E4.REL_TOL:
                    stats[f"reject_tol_{arm}"] = stats.get(f"reject_tol_{arm}", 0) + 1
                    continue
                dout = np.empty(M_DEPLOY)
                ms = time_kernel(fn, darr, dout, M_DEPLOY)
                probes = {}
                for mm in PROBE_SIZES:
                    pout = np.empty(mm)
                    probes[str(mm)] = time_kernel(fn, parr[mm], pout, mm)
                rec["arms"][arm] = {"compile_ms": cms, "ms": ms,
                                    "probe_ms": probes, "worst_rel_err": worst}
                ok_any = True
                for junk in (so, so[:-3] + ".c"):
                    try:
                        os.remove(junk)
                    except OSError:
                        pass
            if not ok_any:
                continue
            tc = E4.tree_op_counts(e)
            rec["cost_ast_size_tree"] = E4.dag_cost(tc, E4.AST_SIZE_WEIGHT)
            rec["tree_nodes"] = sum(tc.values())
            admitted.append(rec)

        kept = [c for c in admitted if "O2" in c["arms"]]
        if len(kept) < 2:
            stats["too_few_admitted"] = stats.get("too_few_admitted", 0) + 1
            continue
        rows.append({"source": core.source, "name": core.name,
                     "args": core.args, "admitted": admitted})

    elapsed = time.perf_counter() - t0
    print(f"\ncollected {len(rows)} decisions in {elapsed:.0f}s", flush=True)
    out = {"rows": rows, "stats": stats,
           "config": {"M_DEPLOY": M_DEPLOY, "PROBE_SIZES": list(PROBE_SIZES),
                      "REPEATS": REPEATS, "SEED": SEED, "BAR": BAR,
                      "REL_TOL": E4.REL_TOL, "flag_arms": list(FLAG_ARMS)},
           "elapsed_s": elapsed}
    with open("experiments/exp007_results.json", "w") as fh:
        json.dump(out, fh)
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    signal.signal(signal.SIGALRM, E4._alarm)
    run(limit=a.limit)
