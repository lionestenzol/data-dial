"""Experiment 002 - discovered reusable substructure.

WHAT 001 LEFT OPEN
    001 (matrix precomposition) was *handed* the relationship to reuse: one
    fixed chain, fused by hand. That is a known optimisation and 001 said so.
    The architectural question underneath it is different:

        Can the system DISCOVER which relationships are worth keeping, from a
        training set alone, and does keeping them help on compositions it has
        never seen?

    This is the P/Q/R/S/T case. Caching the finished output of experience
    PQR does nothing for PQS or TQR. The claim under test is that the shared
    SUBSTRUCTURE can be found automatically and reused across experiences
    that never repeat.

WHAT IS ALREADY KNOWN (not claimed as novel)
    Frequent-subsequence mining, common subexpression elimination, and
    operator fusion are all established. Nothing here invents them. What is
    being measured is whether their ECONOMICS survive when discovery cost and
    primitive storage are charged, and when evaluation is on held-out
    compositions rather than the training set.

DESIGN
    Library of K linear operators over GF(p). An "experience" is a sequence of
    L operators applied to ONE novel input vector. Every full sequence is
    unique - no experience ever repeats, so whole-result caching is worthless
    by construction. Sequences are generated with a structure parameter alpha:
    alpha=0 is uniform random (no shared substructure), alpha=1 is composed
    entirely of recurring motifs.

    Discovery sees only the TRAIN sequences. Evaluation is only on HELD-OUT
    sequences generated afterwards from the same process.

    Primary metric is multiply-accumulates (device independent, exact).
    Storage and discovery cost are charged separately and explicitly.

PRE-REGISTERED PREDICTIONS (committed before the first run)
    P1  alpha=0.00: mechanism lands within 5% of sequential - no motif clears
        the keep-threshold, discovery is wasted effort.
    P2  alpha=1.00: mechanism uses at least 2.5x fewer MACs than sequential
        on held-out sequences, including amortised fusion cost.
    P3  crossover (mechanism beats sequential by >10%) sits near alpha ~ 0.5.
    P4  per-sequence full fusion - the 001 technique applied naively at batch
        size 1 - loses to plain sequential execution by more than 100x.
    P5  exactness is 100% in every configuration.
    P6  the keep-threshold that pays for itself is count > N (the matrix
        dimension), falling straight out of the n^3 / n^2 ratio.

HOW THIS CAN FAIL
    If the mechanism cannot beat sequential even at alpha=1.0, discovered
    substructure does not pay at batch size 1 and the approach is dead in this
    form. If it only wins at alpha=1.0, the mechanism needs workloads more
    structured than anything real, which is close to the same verdict.
"""
from __future__ import annotations

import json
import time
from collections import Counter

import numpy as np

P = 65521          # largest prime below 2^16; products stay inside int64
N = 64             # operator dimension
K = 40             # library size
L = 12             # operators per experience
MAX_MOTIF = 5
N_TRAIN = 300
N_HELD = 200
MAC_MATVEC = N * N
MAC_MATMUL = N * N * N


# -- workload ------------------------------------------------------------
def make_library(rng):
    return [rng.integers(0, P, size=(N, N), dtype=np.int64) for _ in range(K)]


def make_motifs(rng, n_motifs=8):
    return [tuple(int(v) for v in rng.integers(0, K, size=int(rng.integers(3, MAX_MOTIF + 1))))
            for _ in range(n_motifs)]


def make_sequences(rng, count, alpha, motifs, seen):
    out = []
    while len(out) < count:
        seq = []
        while len(seq) < L:
            if motifs and rng.random() < alpha:
                seq.extend(motifs[int(rng.integers(len(motifs)))])
            else:
                seq.append(int(rng.integers(K)))
        seq = tuple(seq[:L])
        if seq in seen:          # every experience must be unique
            continue
        seen.add(seq)
        out.append(seq)
    return out


# -- arithmetic ----------------------------------------------------------
def matmul(a, b):
    return (a @ b) % P


def matvec(a, x):
    return (a @ x) % P


def fuse(lib, motif):
    """Fuse left-to-right application order: apply motif[0] first."""
    acc = lib[motif[0]]
    for op in motif[1:]:
        acc = matmul(lib[op], acc)
    return acc


# -- discovery (train only) ----------------------------------------------
def mine(train):
    counts = Counter()
    examined = 0
    for seq in train:
        for m in range(2, MAX_MOTIF + 1):
            for i in range(len(seq) - m + 1):
                counts[seq[i:i + m]] += 1
                examined += 1
    return counts, examined


def select(counts):
    """Keep a motif when fusing it is repaid by its own train occurrences.

    Fusing costs (m-1) matmuls = (m-1)*N^3 MACs, once.
    Each occurrence saves (m-1) matvecs = (m-1)*N^2 MACs.
    So it repays itself after N occurrences - the threshold is the dimension.
    """
    kept = []
    cands = [(mo, c) for mo, c in counts.items() if c > N]
    cands.sort(key=lambda kv: (len(kv[0]) - 1) * kv[1], reverse=True)
    for motif, _ in cands:
        s = "".join(f"<{o}>" for o in motif)
        if any(s in "".join(f"<{o}>" for o in k) for k in kept):
            continue                      # already inside a longer kept motif
        kept.append(motif)
    return kept


def cover(seq, prims):
    plan, i = [], 0
    while i < len(seq):
        hit = None
        for m in range(MAX_MOTIF, 1, -1):
            if seq[i:i + m] in prims:
                hit = seq[i:i + m]
                break
        if hit:
            plan.append(prims[hit])
            i += len(hit)
        else:
            plan.append(seq[i])
            i += 1
    return plan


# -- execution -----------------------------------------------------------
def run_sequential(lib, seq, x):
    for op in seq:
        x = matvec(lib[op], x)
    return x


def run_plan(lib, prims_mat, plan, x):
    for step in plan:
        a = prims_mat[step] if isinstance(step, tuple) else lib[step]
        x = matvec(a, x)
    return x


def trial(alpha, seed):
    rng = np.random.default_rng(seed)
    lib = make_library(rng)
    motifs = make_motifs(rng)
    seen = set()
    train = make_sequences(rng, N_TRAIN, alpha, motifs, seen)
    held = make_sequences(rng, N_HELD, alpha, motifs, seen)
    inputs = [rng.integers(0, P, size=N, dtype=np.int64) for _ in held]

    t0 = time.perf_counter()
    counts, examined = mine(train)
    kept = select(counts)
    discover_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    prims_mat = {mo: fuse(lib, mo) for mo in kept}
    fuse_ms = (time.perf_counter() - t0) * 1000
    fuse_macs = sum((len(mo) - 1) * MAC_MATMUL for mo in kept)
    store_bytes = len(kept) * N * N * 2          # uint16 entries

    prims = {mo: mo for mo in kept}
    plans = [cover(s, prims) for s in held]

    t0 = time.perf_counter()
    seq_out = [run_sequential(lib, s, x) for s, x in zip(held, inputs)]
    seq_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    mech_out = [run_plan(lib, prims_mat, p, x) for p, x in zip(plans, inputs)]
    mech_ms = (time.perf_counter() - t0) * 1000

    exact = all(np.array_equal(a, b) for a, b in zip(seq_out, mech_out))
    steps = sum(len(p) for p in plans)
    hits = sum(1 for p in plans for s in p if isinstance(s, tuple))

    seq_macs = N_HELD * L * MAC_MATVEC
    mech_macs = steps * MAC_MATVEC + fuse_macs
    naive_fuse_macs = N_HELD * ((L - 1) * MAC_MATMUL + MAC_MATVEC)

    return {
        "alpha": alpha, "exact": exact,
        "kept": len(kept), "store_bytes": store_bytes,
        "covered_steps": steps, "primitive_uses": hits,
        "seq_macs": seq_macs, "mech_macs": mech_macs,
        "fuse_macs": fuse_macs, "naive_fuse_macs": naive_fuse_macs,
        "speedup_macs": seq_macs / mech_macs,
        "naive_vs_seq": naive_fuse_macs / seq_macs,
        "breakeven_seqs": (fuse_macs / ((L - steps / N_HELD) * MAC_MATVEC)
                           if steps < N_HELD * L else float("inf")),
        "discover_ms": discover_ms, "fuse_ms": fuse_ms,
        "seq_ms": seq_ms, "mech_ms": mech_ms, "examined": examined,
    }


if __name__ == "__main__":
    rows = [trial(a, 1000 + i) for i, a in enumerate([0.0, 0.25, 0.5, 0.75, 1.0])]
    print(f"{'alpha':>6} {'exact':>6} {'kept':>5} {'store KB':>9} {'steps/seq':>10} "
          f"{'MAC speedup':>12} {'breakeven':>10} {'discover ms':>12}")
    for r in rows:
        print(f"{r['alpha']:>6.2f} {str(r['exact']):>6} {r['kept']:>5} "
              f"{r['store_bytes']/1024:>9.1f} {r['covered_steps']/N_HELD:>10.2f} "
              f"{r['speedup_macs']:>12.2f} {r['breakeven_seqs']:>10.0f} "
              f"{r['discover_ms']:>12.1f}")
    print(f"\nnaive per-sequence fusion (the 001 technique at batch size 1) "
          f"costs {rows[0]['naive_vs_seq']:.0f}x sequential")
    with open("experiments/exp002_results.json", "w") as fh:
        json.dump(rows, fh, indent=2)
