"""Experiment 002b - is 002's null result an amortisation artefact?

002 found: coverage worked (12.00 -> 4.28 operators per sequence at alpha=1.0)
but MAC speedup was only 1.06x, and the breakeven column read 182-272
sequences against a held-out set of exactly 200. The one-time fusion cost was
eating the entire win because the workload was the same size as the breakeven.

That is a property of the parameters, not of the architecture. The fusion of
an m-long motif costs (m-1)*N^3 once and saves (m-1)*N^2 per use, so a
primitive repays itself after N uses. Breakeven should therefore scale with N
and the advantage should approach the coverage ratio as the workload grows.

PRE-REGISTERED (committed before this run)
    Q1  at alpha=1.0 with 2000 held-out sequences, speedup >= 2.3x,
        approaching the 2.80x coverage ratio seen in 002.
    Q2  breakeven sequence count scales roughly linearly in N.
    Q3  at N=16, the original 200-sequence workload already wins (>1.5x).
    Q4  the asymptotic ceiling is the coverage ratio and nothing beyond it -
        fusion buys fewer operations, never cheaper ones.
"""
from __future__ import annotations

import json

import exp002_discovered_substructure as e2


def run(n_held, n_dim, alpha=1.0, seed=7):
    e2.N, e2.N_HELD = n_dim, n_held
    e2.MAC_MATVEC, e2.MAC_MATMUL = n_dim * n_dim, n_dim ** 3
    return e2.trial(alpha, seed)


if __name__ == "__main__":
    out = []
    print("alpha=1.0, operator dimension N=64 - growing the workload")
    print(f"{'held-out':>9} {'steps/seq':>10} {'MAC speedup':>12} {'exec-only':>10} {'exact':>6}")
    for n_held in (200, 500, 1000, 2000, 5000):
        r = run(n_held, 64)
        exec_only = r["seq_macs"] / (r["mech_macs"] - r["fuse_macs"])
        out.append({"sweep": "workload", **r, "exec_only": exec_only})
        print(f"{n_held:>9} {r['covered_steps']/n_held:>10.2f} "
              f"{r['speedup_macs']:>12.2f} {exec_only:>10.2f} {str(r['exact']):>6}")

    print("\nalpha=1.0, held-out fixed at 200 - shrinking the operator")
    print(f"{'N':>9} {'steps/seq':>10} {'MAC speedup':>12} {'breakeven':>10} {'exact':>6}")
    for n_dim in (8, 16, 32, 64, 128):
        r = run(200, n_dim)
        out.append({"sweep": "dimension", **r})
        print(f"{n_dim:>9} {r['covered_steps']/200:>10.2f} {r['speedup_macs']:>12.2f} "
              f"{r['breakeven_seqs']:>10.0f} {str(r['exact']):>6}")

    with open("experiments/exp002b_results.json", "w") as fh:
        json.dump(out, fh, indent=2)
