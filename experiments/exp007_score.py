#!/usr/bin/env python
"""Score experiment 007 against EXP007_PREREGISTRATION.md. Mechanical.

The accounting is the experiment, so it is spelled out here rather than
buried: flagging a decision means paying to compile the candidates you did
NOT end up deploying, because one compilation is unavoidable under any policy.
Gross charges k compiles, marginal charges k-1, and marginal is the reading
that decides the question.
"""
from __future__ import annotations

import json
import math
import random
import statistics
import sys

ARM = "O2"
POLICY = "cost_ast_size_tree"
BAR = 200
PROBE_DEFAULT = "256"

R = json.load(open("experiments/exp007_results.json"))
rows = [r for r in R["rows"]
        if sum(1 for c in r["admitted"] if ARM in c["arms"]) >= 2]
cfg = R["config"]


def adm(r, arm=ARM):
    return [c for c in r["admitted"] if arm in c["arms"]]


def pick_policy(cs):
    return min(cs, key=lambda c: (c[POLICY], c["tree_nodes"], c["tag"]))


def decision_terms(r, arm=ARM, probe=None):
    """(policy_ms, best_ms, waste_ms, k, compile_total_ms, eval_oracle_ms)"""
    cs = adm(r, arm)
    best = min(c["arms"][arm]["ms"] for c in cs)
    pol = pick_policy(cs)["arms"][arm]["ms"]
    comp = sum(c["arms"][arm]["compile_ms"] for c in cs)
    if probe:
        ev = sum(c["arms"][arm]["probe_ms"][probe] for c in cs)
    else:
        ev = sum(c["arms"][arm]["ms"] for c in cs)
    return pol, best, pol - best, len(cs), comp, ev


def breakeven(rs, mode, arm=ARM, probe=None, repeats=1):
    """requests per expression = oracle one-off cost / waste saved per request"""
    spent = recovered = 0.0
    for r in rs:
        pol, best, waste, k, comp, ev = decision_terms(r, arm, probe)
        if mode == "gross":
            spent += comp + repeats * ev
        elif mode == "marginal":
            # one compilation happens under any policy, so only k-1 are the
            # oracle's marginal cost; its share of eval scales the same way
            spent += comp * (k - 1) / k + repeats * ev
        elif mode == "eval_only":          # 006's accounting, for comparison
            spent += repeats * ev
        recovered += waste
    return (spent / recovered) if recovered > 0 else math.inf, spent, recovered


def boot(rs, mode, probe=None, B=600, seed=7):
    rnd = random.Random(seed)
    out = []
    n = len(rs)
    for _ in range(B):
        s = [rs[rnd.randrange(n)] for _ in range(n)]
        be, _, rec = breakeven(s, mode, probe=probe)
        if math.isfinite(be):
            out.append(be)
    out.sort()
    return out


checks = []


def chk(tag, claim, ok, actual, note=""):
    checks.append({"tag": tag, "claim": claim,
                   "verdict": "hit" if ok else "MISS",
                   "actual": actual, "note": note})


# ---------------------------------------------------------------- W1
cms = [c["arms"][ARM]["compile_ms"] for r in rows for c in adm(r)]
ems = [c["arms"][ARM]["ms"] for r in rows for c in adm(r)]
ratio = statistics.fmean(cms) / statistics.fmean(ems)
chk("W1", "mean compile time >= 100x mean evaluation time", ratio >= 100,
    f"compile {statistics.fmean(cms):.1f} ms vs eval "
    f"{statistics.fmean(ems)*1000:.1f} us = {ratio:.0f}x")

# ---------------------------------------------------------------- W2 / W3
be_gross, sp_g, rec = breakeven(rows, "gross")
be_marg, sp_m, _ = breakeven(rows, "marginal")
be_eval, sp_e, _ = breakeven(rows, "eval_only")
chk("W2", f"gross accounting: break-even > {BAR} requests", be_gross > BAR,
    f"{be_gross:.0f} requests ({sp_g:.0f} ms oracle, {rec:.3f} ms waste)")

bm = boot(rows, "marginal")
lo, hi = bm[int(.025 * len(bm))], bm[int(.975 * len(bm))]
chk("W3", f"DECISIVE - marginal accounting (k-1 compiles): break-even > {BAR}",
    be_marg > BAR,
    f"{be_marg:.0f} requests, bootstrap 95% [{lo:.0f}, {hi:.0f}]"
    f"   (006-style eval-only on this backend: {be_eval:.1f})")

# ---------------------------------------------------------------- W4
chk("W4", "marginal break-even in [1,000, 50,000] requests",
    1000 <= be_marg <= 50000, f"{be_marg:.0f} requests")

# ---------------------------------------------------------------- W5
tot_waste = sum(decision_terms(r)[2] for r in rows)
tot_run = sum(decision_terms(r)[1] for r in rows)
frac_c = tot_waste / tot_run if tot_run else float("nan")
# NumPy reference, from 006's own results file
try:
    S6 = json.load(open("experiments/exp006_timings.json"))
    w6 = b6 = 0.0
    for r in S6["rows"]:
        a = r["admitted"]
        if len(a) < 2:
            continue
        t = [min(c["truth"]) for c in a]
        p = min(a, key=lambda c: (c["cost_ast_size_tree"], c["nodes"], c["tag"]))
        bi = min(t)
        w6 += min(p["truth"]) - bi
        b6 += bi
    frac_np = w6 / b6
except Exception:
    frac_np = float("nan")
rel = frac_c / frac_np if frac_np and math.isfinite(frac_np) else float("nan")
chk("W5", "waste as a fraction of runtime on C is within 3x of NumPy's",
    math.isfinite(rel) and (1 / 3) <= rel <= 3,
    f"C {frac_c*100:.2f}% of runtime vs NumPy {frac_np*100:.2f}% = {rel:.2f}x")

# ---------------------------------------------------------------- W6
bes = {}
for p in [str(x) for x in cfg["PROBE_SIZES"]]:
    bes[p], _, _ = breakeven(rows, "marginal", probe=p)
bes["deployed"], _, _ = breakeven(rows, "marginal")
spread = max(bes.values()) / min(bes.values())
chk("W6", "break-even varies <1.2x across probe sizes (compilation dominates)",
    spread < 1.2,
    "  ".join(f"{k}:{v:.0f}" for k, v in bes.items()) + f"   spread {spread:.3f}x")

# ---------------------------------------------------------------- report
hits = sum(1 for c in checks if c["verdict"] == "hit")
print(f"\nExperiment 007 — {hits} of {len(checks)} pre-registered predictions hit")
print(f"({len(rows)} decisions, {len(cms)} candidates, "
      f"{R['elapsed_s']:.0f}s collection)\n")
for c in checks:
    print(f"{c['tag']:>4} {c['verdict']:>6}  {c['claim']}")
    print(f"{'':>12}actual: {c['actual']}")
    if c["note"]:
        print(f"{'':>12}note:   {c['note']}")

print(f"\nACCOUNTING SUMMARY (requests per expression; bar = {BAR})")
print(f"  006's accounting, evaluation only       : {be_eval:>10.1f}")
print(f"  marginal, k-1 compiles charged          : {be_marg:>10.0f}   "
      f"bootstrap [{lo:.0f}, {hi:.0f}]")
print(f"  gross, all k compiles charged           : {be_gross:>10.0f}")
print(f"  -> 006's operating point "
      f"{'DOES NOT survive' if be_marg > BAR else 'SURVIVES'} a compiling backend")

# -ffast-math admission, reported rather than suppressed
n_o2 = sum(1 for r in R["rows"] for c in r["admitted"] if "O2" in c["arms"])
n_ff = sum(1 for r in R["rows"] for c in r["admitted"] if "ffast" in c["arms"])
print(f"\naccuracy admission at 1e-6 vs a 30-digit reference:")
print(f"  admitted under -O2          : {n_o2}")
print(f"  admitted under -ffast-math  : {n_ff}  "
      f"({n_o2 - n_ff} that -O2 admits are rejected under -ffast-math)")
for k, v in sorted(R["stats"].items()):
    print(f"  {v:>6}  {k}")

json.dump({"hits": hits, "total": len(checks), "checks": checks,
           "breakeven": {"eval_only": be_eval, "marginal": be_marg,
                         "gross": be_gross, "bootstrap95": [lo, hi],
                         "by_probe": bes},
           "n_decisions": len(rows)},
          open("experiments/exp007_scorecard.json", "w"), indent=2)
