#!/usr/bin/env python
"""Why did plain node counting beat measured per-operator cost?

T5 and T10 missed in the same direction: ast_size has a SMALLER tail than
either the textbook static table or per-operator measured costs. That was not
predicted and needs an explanation that is tested, not asserted.

Hypothesis H: in vectorised NumPy over L2-resident arrays the cost driver is
the number of intermediate arrays - memory passes - not per-element ALU
latency. Node count is accidentally a good proxy for memory passes, while
weighting a sin at 30x an add over-penalises it relative to its marginal cost
in a traffic-bound regime.

Test: across every admitted candidate, see which cost model best predicts
measured runtime. No new timing; this reads the run's own JSON.
"""
import json
import math
import statistics

R = json.load(open("experiments/exp004_results.json"))
rows = R["rows"]

cands = [c for r in rows for c in r["admitted"]]
print(f"{len(cands)} admitted candidates across {len(rows)} cores\n")

MODELS = [("ast_size (DAG)", "cost_ast_size"), ("static (DAG)", "cost_static"),
          ("measured (DAG)", "cost_measured"), ("ast_size (tree)", "cost_ast_size_tree"),
          ("static (tree)", "cost_static_tree"), ("measured (tree)", "cost_measured_tree")]


def pearson(xs, ys):
    n = len(xs)
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return float("nan")
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def spearman(xs, ys):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        for pos, i in enumerate(order):
            r[i] = pos
        return r
    return pearson(rank(xs), rank(ys))


ms = [c["ms"] for c in cands]
print("How well does each cost model predict measured runtime?")
print(f"{'model':>18} {'pearson r':>10} {'spearman':>10} {'log-log r':>10}")
for label, key in MODELS:
    xs = [c[key] for c in cands]
    pairs = [(x, m) for x, m in zip(xs, ms) if x > 0 and m > 0]
    lr = pearson([math.log(x) for x, _ in pairs], [math.log(m) for _, m in pairs])
    print(f"{label:>18} {pearson(xs, ms):>10.4f} {spearman(xs, ms):>10.4f} {lr:>10.4f}")

# NOTE, recorded rather than quietly deleted: this "test" of H is TAUTOLOGICAL.
# ast_size weights are 1.0 for every operator and 0.0 for var/const, so
# ast_size IS the interior-node count. The numbers below are identical to the
# ast_size row by construction and test nothing. H needed a model that
# separates memory passes from operator identity, which this does not.
# Kept visible because deleting a failed test is how a result stops being
# checkable.
print("\nH (TAUTOLOGICAL - identical to ast_size by construction, tests nothing)")
for label, ck in (("DAG interior", "counts"),):
    xs = []
    for c in cands:
        interior = sum(n for op, n in c[ck].items() if op not in ("var", "const"))
        xs.append(interior)
    pairs = [(x, m) for x, m in zip(xs, ms) if x > 0 and m > 0]
    lr = pearson([math.log(x) for x, _ in pairs], [math.log(m) for _, m in pairs])
    print(f"{label:>18} {pearson(xs, ms):>10.4f} {spearman(xs, ms):>10.4f} {lr:>10.4f}")

# Where the heavy-operator weights actively mislead
print("\nDecisions where static/measured lose to ast_size, by what they traded")
loses = 0
examples = []
for r in rows:
    adm = r["admitted"]
    if len(adm) < 2:
        continue
    oracle = min(c["ms"] for c in adm)
    pa = min(adm, key=lambda c: (c["cost_ast_size"], c["nodes"], c["tag"]))
    pm = min(adm, key=lambda c: (c["cost_measured"], c["nodes"], c["tag"]))
    ra, rm = pa["ms"] / oracle, pm["ms"] / oracle
    if rm > ra * 1.05:
        loses += 1
        if len(examples) < 6:
            examples.append((r["name"][:46], pa["tag"], ra, pm["tag"], rm))
print(f"  measured loses to ast_size on {loses} of "
      f"{sum(1 for r in rows if len(r['admitted'])>=2)} decisions")
for nm, ta, ra, tm, rm in examples:
    print(f"    {nm:<48} ast_size->{ta:<18} {ra:.2f}x | measured->{tm:<18} {rm:.2f}x")

# the extreme tail: what is the 48x case?
print("\nWorst regret cases for ast_size (DAG)")
worst = []
for r in rows:
    adm = r["admitted"]
    if len(adm) < 2:
        continue
    oracle = min(c["ms"] for c in adm)
    pa = min(adm, key=lambda c: (c["cost_ast_size"], c["nodes"], c["tag"]))
    worst.append((pa["ms"] / oracle, r["name"][:44], pa["tag"],
                  min(adm, key=lambda c: c["ms"])["tag"], pa["ms"], oracle))
worst.sort(reverse=True)
for reg, nm, picked, best, pms, oms in worst[:6]:
    print(f"  {reg:>7.2f}x  {nm:<46} picked {picked:<16} ({pms:.3f} ms) "
          f"best {best:<16} ({oms:.3f} ms)")

# noise honesty: how much of the p90-p95 band is distinguishable from noise?
nz = [r["noise_ratio"] for r in rows
      if isinstance(r.get("noise_ratio"), (int, float)) and math.isfinite(r["noise_ratio"])]
nz.sort()
print(f"\nNoise floor over {len(nz)} re-timings: p50 {statistics.median(nz):.4f}x "
      f"p95 {nz[int(.95*len(nz))-1]:.4f}x p99 {nz[int(.99*len(nz))-1]:.4f}x max {nz[-1]:.4f}x")
for thr in (1.05, 1.1, 1.2, 1.3, 1.5):
    frac = sum(1 for x in nz if x >= thr) / len(nz)
    print(f"  re-timings of the SAME candidate reaching {thr:>4}x: {frac*100:.1f}%")
