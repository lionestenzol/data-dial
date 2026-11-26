#!/usr/bin/env python
"""Experiment 006 - what is the cheapest sufficient oracle?

See EXP006_PREREGISTRATION.md. Collects every repeat time per candidate, which
004 did not, so that best-of-R oracles can be simulated for any R and the
trade-off between oracle price and oracle pick quality becomes a calculation.
"""
from __future__ import annotations

import gzip
import json
import math
import pathlib
import signal
import statistics
import sys
import time

import numpy as np
import sympy as sp

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import exp004_regret_distribution as E4
from exp004_corpus import load as load_corpus

M_DEPLOY = 16384
N_SAMPLES = 48               # alternately split into disjoint sim / truth pools
PROBE_SIZES = (256, 1024, 4096)
N_PROBE = 12
R_GRID = (1, 2, 3, 4, 6, 8, 12, 24)
RP_GRID = (1, 2, 3, 6, 12)
POLICY = "cost_ast_size_tree"
SEED = 6006
BAR = 200                    # 005's ship criterion, carried over


def timed_samples(f, arrays, n):
    """n individual timings. Returns the raw list, not a minimum - the whole
    point is that 004 kept only minima and so could not answer this."""
    with np.errstate(all="ignore"):
        f(*arrays)                                   # warm
        out = []
        for _ in range(n):
            t = time.perf_counter()
            f(*arrays)
            out.append((time.perf_counter() - t) * 1000.0)
    return out


def run():
    rng = np.random.default_rng(SEED)
    cores, cstats = load_corpus()
    print(f"corpus: {cstats['fpcores']} FPCores, {cstats['ok']} in scope", flush=True)
    measured_w, cal_ms = E4.calibrate(rng)

    rows, sreprs, stats = [], {}, {}
    t0 = time.perf_counter()
    for idx, core in enumerate(cores):
        if idx % 100 == 0:
            print(f"  [{idx}/{len(cores)}] {time.perf_counter()-t0:.0f}s "
                  f"decisions={len(rows)}", flush=True)
        try:
            cands = E4.candidates_for(core.expr, stats)
        except Exception:
            continue
        acols = E4.sample_points(core, rng, E4.N_ADMIT)
        truth_vals = E4.truth_values(core.expr, core.args, acols, stats)
        if truth_vals is None or np.count_nonzero(np.isfinite(truth_vals)) < 8:
            continue
        finite = np.isfinite(truth_vals)
        aarrays = [acols[a] for a in core.args]

        dcols = E4.sample_points(core, rng, M_DEPLOY)
        darrays = [dcols[a] for a in core.args]
        parrays = {m: [E4.sample_points(core, rng, m)[a] for a in core.args]
                   for m in PROBE_SIZES}

        admitted = []
        for tag, e in cands:
            try:
                f = E4.compile_fn(core.args, e)
                with np.errstate(all="ignore"):
                    got = np.asarray(f(*aarrays), dtype=float)
                if got.shape != truth_vals.shape:
                    got = np.broadcast_to(got, truth_vals.shape)
            except Exception:
                continue
            err = E4.rel_err(got, truth_vals)
            ok = finite & np.isfinite(got)
            if np.count_nonzero(ok) < 8 or float(np.max(err[ok])) > E4.REL_TOL:
                continue
            try:
                s = timed_samples(f, darrays, N_SAMPLES)
                probes = {m: timed_samples(f, parrays[m], N_PROBE)
                          for m in PROBE_SIZES}
            except Exception:
                continue
            counts = E4.dag_op_counts(e)
            tcounts = E4.tree_op_counts(e)
            admitted.append({
                "tag": tag,
                # disjoint pools, interleaved so neither sees systematic drift
                "sim": s[0::2], "truth": s[1::2],
                "probe": {str(m): v for m, v in probes.items()},
                "cost_ast_size": E4.dag_cost(counts, E4.AST_SIZE_WEIGHT),
                "cost_static": E4.dag_cost(counts, E4.STATIC_WEIGHT),
                "cost_measured": E4.dag_cost(counts, measured_w),
                "cost_ast_size_tree": E4.dag_cost(tcounts, E4.AST_SIZE_WEIGHT),
                "cost_static_tree": E4.dag_cost(tcounts, E4.STATIC_WEIGHT),
                "cost_measured_tree": E4.dag_cost(tcounts, measured_w),
                "nodes": sum(counts.values()),
                "sq_powexp": E4.has_square_powexp(e),
            })
        if len(admitted) < 2:
            continue
        key = f"{len(rows)}"
        sreprs[key] = {c["tag"]: sp.srepr(e) for (tag, e), c
                       in zip([(t, x) for t, x in cands
                               if t in {a['tag'] for a in admitted}], admitted)
                       if True}
        rows.append({"source": core.source, "name": core.name,
                     "args": core.args, "admitted": admitted})

    elapsed = time.perf_counter() - t0
    print(f"\ncollected {len(rows)} decisions in {elapsed:.0f}s", flush=True)
    with open("experiments/exp006_timings.json", "w") as fh:
        json.dump({"rows": rows, "config": {
            "M_DEPLOY": M_DEPLOY, "N_SAMPLES": N_SAMPLES,
            "PROBE_SIZES": list(PROBE_SIZES), "N_PROBE": N_PROBE,
            "SEED": SEED, "calibration_ms": cal_ms}}, fh)
    # candidate expressions, for a future backend re-run (HANDOFF item B)
    with gzip.open("experiments/exp006_candidate_exprs.json.gz", "wt") as fh:
        json.dump(sreprs, fh)
    return rows


if __name__ == "__main__":
    signal.signal(signal.SIGALRM, E4._alarm)
    run()
