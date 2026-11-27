#!/usr/bin/env python
"""Experiment 005 - can the regret tail be flagged without paying the oracle?

See EXP005_PREREGISTRATION.md. Reads 004's results file; adds no new timing,
so its risk is overfitting rather than measurement error, and that is what the
grouped cross-validation is for.

Policy under test: ast_size with tree counting - 004's best cheap arm.
Target: decisions where that policy's regret >= 1.2 (secondary: >= 1.5).
Criterion: break-even requests per expression, not precision.
"""
from __future__ import annotations

import json
import math
import pathlib
import statistics
from collections import defaultdict

import numpy as np

REPEATS = 11                 # 004's best-of count; oracle pays this per candidate
POLICY = "cost_ast_size_tree"
TARGETS = (1.2, 1.5)
FOLDS = 5
FLAG_BUDGET = 0.20           # ship criterion: flag at most 20% of decisions
BREAKEVEN_BAR = 200          # ship criterion: <= 200 requests per expression
SEED = 5005

TREE_KEYS = ("cost_ast_size_tree", "cost_static_tree", "cost_measured_tree")


def pick(adm, key):
    return min(adm, key=lambda c: (c[key], c["nodes"], c["tag"]))


def features(adm):
    """Every feature below is computable from the candidate ASTs alone. No
    timing is read. That is the whole point: the oracle costs 162x running the
    best form, so a flag must be decidable without it."""
    picks = {k: pick(adm, k)["tag"] for k in TREE_KEYS}
    dag_pick = pick(adm, "cost_ast_size")["tag"]
    costs = sorted(c[POLICY] for c in adm)
    c1, c2 = costs[0], costs[1]
    cmin, cmax = costs[0], costs[-1]
    return {
        "disagree_ast_static": float(picks["cost_ast_size_tree"] != picks["cost_static_tree"]),
        "disagree_ast_meas": float(picks["cost_ast_size_tree"] != picks["cost_measured_tree"]),
        "disagree_any": float(len(set(picks.values())) > 1),
        "dag_vs_tree": float(picks["cost_ast_size_tree"] != dag_pick),
        "sq_powexp": float(any(c.get("sq_powexp") for c in adm)),
        "pow_gen": float(any(c["counts"].get("pow_gen", 0) for c in adm)),
        # continuous, thresholded on train folds only
        "_tie": (c2 - c1) / c1 if c1 > 0 else 0.0,
        "_spread": (cmax / cmin) if cmin > 0 else 1.0,
        "_ncand": float(len(adm)),
    }


def load():
    R = json.load(open("experiments/exp004_results.json"))
    recs = []
    for r in R["rows"]:
        adm = r["admitted"]
        if len(adm) < 2:
            continue
        oracle_ms = min(c["ms"] for c in adm)
        chosen = pick(adm, POLICY)
        recs.append({
            "group": pathlib.Path(r["source"]).name,
            "name": r["name"],
            "regret": chosen["ms"] / oracle_ms,
            "waste_ms": chosen["ms"] - oracle_ms,
            # cost of flagging: time every admitted candidate, best-of-REPEATS
            "oracle_ms": sum(c["ms"] for c in adm) * REPEATS,
            "feat": features(adm),
        })
    return recs


# ---------------------------------------------------------------- metrics
def prec_recall(flags, pos):
    tp = sum(1 for f, p in zip(flags, pos) if f and p)
    fp = sum(1 for f, p in zip(flags, pos) if f and not p)
    fn = sum(1 for f, p in zip(flags, pos) if not f and p)
    prec = tp / (tp + fp) if tp + fp else float("nan")
    rec = tp / (tp + fn) if tp + fn else float("nan")
    return prec, rec, sum(flags) / len(flags)


def auc(scores, pos):
    pairs = sorted(zip(scores, pos))
    npos = sum(pos); nneg = len(pos) - npos
    if npos == 0 or nneg == 0:
        return float("nan")
    # rank-sum
    ranks, i = [0.0] * len(pairs), 0
    while i < len(pairs):
        j = i
        while j + 1 < len(pairs) and pairs[j + 1][0] == pairs[i][0]:
            j += 1
        r = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[k] = r
        i = j + 1
    s = sum(r for r, (_, p) in zip(ranks, pairs) if p)
    return (s - npos * (npos + 1) / 2) / (npos * nneg)


def logistic_fit(X, y, iters=4000, lr=0.3, l2=1e-3):
    X = np.asarray(X, float); y = np.asarray(y, float)
    mu, sd = X.mean(0), X.std(0) + 1e-9
    Z = (X - mu) / sd
    Z = np.hstack([Z, np.ones((len(Z), 1))])
    w = np.zeros(Z.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-Z @ w))
        g = Z.T @ (p - y) / len(y) + l2 * np.r_[w[:-1], 0.0]
        w -= lr * g
    return (mu, sd, w)


def logistic_score(model, X):
    mu, sd, w = model
    Z = (np.asarray(X, float) - mu) / sd
    Z = np.hstack([Z, np.ones((len(Z), 1))])
    return 1 / (1 + np.exp(-(Z @ w)))


def make_folds(recs, k=FOLDS):
    """Whole source files to folds, greedily balanced by decision count, so a
    held-out case is never a cosmetic variant of a training one."""
    by_group = defaultdict(list)
    for i, r in enumerate(recs):
        by_group[r["group"]].append(i)
    order = sorted(by_group.items(), key=lambda kv: -len(kv[1]))
    folds = [[] for _ in range(k)]
    for _, idxs in order:
        folds.sort(key=len)
        folds[0].extend(idxs)
    return folds


BINARY = ["disagree_ast_static", "disagree_ast_meas", "disagree_any",
          "dag_vs_tree", "sq_powexp", "pow_gen"]
CONTIN = ["_tie", "_spread", "_ncand"]
# continuous features: direction in which large values should mean "risky"
CONT_DIR = {"_tie": -1.0, "_spread": +1.0, "_ncand": +1.0}


def run():
    recs = load()
    folds = make_folds(recs)
    print(f"{len(recs)} decisions, {len(set(r['group'] for r in recs))} groups, "
          f"{FOLDS} folds of sizes {[len(f) for f in folds]}\n")

    out = {"n_decisions": len(recs), "targets": {}}

    for target in TARGETS:
        pos = [r["regret"] >= target for r in recs]
        npos = sum(pos)
        print("=" * 72)
        print(f"TARGET regret >= {target}   ({npos} positives, "
              f"{npos/len(recs)*100:.1f}%)")
        res = {"n_positives": npos, "single": {}, "combined": {}, "economics": {}}

        # ---- single predicates, grouped CV --------------------------------
        print(f"\n{'predicate':>22} {'held-out prec':>13} {'recall':>8} "
              f"{'flagged':>8} {'train prec':>11} {'AUC':>7}")
        for name in BINARY:
            hp, hr, hf, tp_, aucs = [], [], [], [], []
            for fi, test in enumerate(folds):
                train = [i for f2, f in enumerate(folds) if f2 != fi for i in f]
                fl_te = [recs[i]["feat"][name] > 0.5 for i in test]
                po_te = [pos[i] for i in test]
                fl_tr = [recs[i]["feat"][name] > 0.5 for i in train]
                po_tr = [pos[i] for i in train]
                p, r, f_ = prec_recall(fl_te, po_te)
                pt, _, _ = prec_recall(fl_tr, po_tr)
                if not math.isnan(p): hp.append(p)
                if not math.isnan(r): hr.append(r)
                hf.append(f_)
                if not math.isnan(pt): tp_.append(pt)
                aucs.append(auc([float(x) for x in fl_te], po_te))
            a = [x for x in aucs if not math.isnan(x)]
            row = {"heldout_precision": statistics.fmean(hp) if hp else float("nan"),
                   "recall": statistics.fmean(hr) if hr else float("nan"),
                   "flagged_frac": statistics.fmean(hf),
                   "train_precision": statistics.fmean(tp_) if tp_ else float("nan"),
                   "auc": statistics.fmean(a) if a else float("nan")}
            res["single"][name] = row
            print(f"{name:>22} {row['heldout_precision']:>13.3f} {row['recall']:>8.3f} "
                  f"{row['flagged_frac']*100:>7.1f}% {row['train_precision']:>11.3f} "
                  f"{row['auc']:>7.3f}")

        # continuous predicates with threshold fit on train folds
        for name in CONTIN:
            hp, hr, hf, tp_ = [], [], [], []
            for fi, test in enumerate(folds):
                train = [i for f2, f in enumerate(folds) if f2 != fi for i in f]
                d = CONT_DIR[name]
                vals = sorted({recs[i]["feat"][name] for i in train})
                best, best_thr = -1.0, None
                for thr in vals:
                    fl = [d * recs[i]["feat"][name] >= d * thr for i in train]
                    if sum(fl) / len(fl) > FLAG_BUDGET:
                        continue
                    p, r, _ = prec_recall(fl, [pos[i] for i in train])
                    if not math.isnan(p) and not math.isnan(r) and r > 0:
                        f1 = 2 * p * r / (p + r) if p + r else 0
                        if f1 > best:
                            best, best_thr = f1, thr
                if best_thr is None:
                    continue
                fl_te = [d * recs[i][ "feat"][name] >= d * best_thr for i in test]
                p, r, f_ = prec_recall(fl_te, [pos[i] for i in test])
                fl_tr = [d * recs[i]["feat"][name] >= d * best_thr for i in train]
                pt, _, _ = prec_recall(fl_tr, [pos[i] for i in train])
                if not math.isnan(p): hp.append(p)
                if not math.isnan(r): hr.append(r)
                hf.append(f_)
                if not math.isnan(pt): tp_.append(pt)
            if not hp:
                continue
            row = {"heldout_precision": statistics.fmean(hp), "recall": statistics.fmean(hr),
                   "flagged_frac": statistics.fmean(hf),
                   "train_precision": statistics.fmean(tp_), "auc": float("nan")}
            res["single"][name] = row
            print(f"{name+' (tuned)':>22} {row['heldout_precision']:>13.3f} "
                  f"{row['recall']:>8.3f} {row['flagged_frac']*100:>7.1f}% "
                  f"{row['train_precision']:>11.3f} {'-':>7}")

        # ---- combined, grouped CV ----------------------------------------
        feat_names = BINARY + CONTIN
        oof = np.zeros(len(recs))
        for fi, test in enumerate(folds):
            train = [i for f2, f in enumerate(folds) if f2 != fi for i in f]
            Xtr = [[recs[i]["feat"][n] for n in feat_names] for i in train]
            ytr = [float(pos[i]) for i in train]
            model = logistic_fit(Xtr, ytr)
            Xte = [[recs[i]["feat"][n] for n in feat_names] for i in test]
            for j, i in enumerate(test):
                oof[i] = logistic_score(model, [Xte[j]])[0]
        comb_auc = auc(list(oof), pos)
        print(f"\ncombined logistic, out-of-fold AUC = {comb_auc:.3f}")
        # precision at recall 0.5, and at the 20% flagging budget
        order = np.argsort(-oof)
        need = max(1, int(math.ceil(0.5 * npos)))
        got, kflag = 0, 0
        for k, i in enumerate(order, 1):
            if pos[i]:
                got += 1
            if got >= need:
                kflag = k
                break
        p_at_r50 = sum(1 for i in order[:kflag] if pos[i]) / kflag if kflag else float("nan")
        nbudget = int(FLAG_BUDGET * len(recs))
        p_at_budget = sum(1 for i in order[:nbudget] if pos[i]) / nbudget
        r_at_budget = sum(1 for i in order[:nbudget] if pos[i]) / npos
        print(f"  precision at recall 0.50 : {p_at_r50:.3f}  (flagging {kflag/len(recs)*100:.1f}%)")
        print(f"  at {FLAG_BUDGET*100:.0f}% flagging budget : precision {p_at_budget:.3f}, "
              f"recall {r_at_budget:.3f}")
        res["combined"] = {"oof_auc": comb_auc, "precision_at_recall50": p_at_r50,
                           "flagged_at_recall50": kflag / len(recs),
                           "precision_at_budget": p_at_budget,
                           "recall_at_budget": r_at_budget}

        # ---- economics ----------------------------------------------------
        tot_waste = sum(r["waste_ms"] for r in recs)
        tot_oracle = sum(r["oracle_ms"] for r in recs)
        be_all = tot_oracle / tot_waste
        pw = sum(r["waste_ms"] for r, p in zip(recs, pos) if p)
        po_ = sum(r["oracle_ms"] for r, p in zip(recs, pos) if p)
        be_perfect = po_ / pw
        flagged = list(order[:nbudget])
        fw = sum(recs[i]["waste_ms"] for i in flagged)
        fo = sum(recs[i]["oracle_ms"] for i in flagged)
        be_det = fo / fw if fw > 0 else float("inf")
        print(f"\neconomics - break-even requests per expression")
        print(f"  flag everything           : {be_all:>9.1f}   "
              f"(recovers {tot_waste:.2f} ms for {tot_oracle:.0f} ms)")
        print(f"  perfect detector (>={target})  : {be_perfect:>9.1f}   "
              f"(recovers {pw:.2f} ms = {pw/tot_waste*100:.1f}% of waste)")
        print(f"  logistic at {FLAG_BUDGET*100:.0f}% budget    : {be_det:>9.1f}   "
              f"(recovers {fw:.2f} ms = {fw/tot_waste*100:.1f}% of waste)")
        ship = (be_det <= BREAKEVEN_BAR)
        print(f"  ship criterion (<= {BREAKEVEN_BAR} req, <= {FLAG_BUDGET*100:.0f}% flagged): "
              f"{'PASS' if ship else 'FAIL'}")
        res["economics"] = {
            "breakeven_flag_everything": be_all,
            "breakeven_perfect": be_perfect,
            "breakeven_detector_at_budget": be_det,
            "waste_total_ms": tot_waste, "oracle_total_ms": tot_oracle,
            "waste_recovered_perfect_ms": pw, "waste_recovered_detector_ms": fw,
            "residual_waste_frac_detector": 1 - fw / tot_waste,
            "ship": ship}
        out["targets"][str(target)] = res
        print()

    json.dump(out, open("experiments/exp005_results.json", "w"), indent=2)
    return out


def economics_per_predicate():
    """Break-even for each cheap rule at its own natural operating point.

    The ship criterion names 'the best detector', and the logistic at a 20%
    budget is not necessarily it. The binary predicates have no tuned
    threshold, so their flagging rate is whatever the rule gives and there is
    no operating point to cherry-pick.
    """
    recs = load()
    tot_waste = sum(r["waste_ms"] for r in recs)
    tot_oracle = sum(r["oracle_ms"] for r in recs)
    print("=" * 72)
    print("BREAK-EVEN PER CHEAP RULE (requests per expression; lower is better)")
    print(f"{'rule':>22} {'flagged':>8} {'waste kept':>11} {'oracle ms':>10} "
          f"{'break-even':>11} {'ship?':>6}")
    rows = []
    for name in BINARY:
        fl = [r["feat"][name] > 0.5 for r in recs]
        fw = sum(r["waste_ms"] for r, f in zip(recs, fl) if f)
        fo = sum(r["oracle_ms"] for r, f in zip(recs, fl) if f)
        frac = sum(fl) / len(fl)
        be = fo / fw if fw > 0 else float("inf")
        ok = be <= BREAKEVEN_BAR and frac <= FLAG_BUDGET
        rows.append((name, frac, fw / tot_waste, fo, be, ok))
    # oracle-everything and perfect-detector reference lines
    for target in TARGETS:
        pos = [r["regret"] >= target for r in recs]
        fw = sum(r["waste_ms"] for r, p in zip(recs, pos) if p)
        fo = sum(r["oracle_ms"] for r, p in zip(recs, pos) if p)
        rows.append((f"PERFECT >={target}", sum(pos) / len(pos), fw / tot_waste,
                     fo, fo / fw, (fo / fw) <= BREAKEVEN_BAR and sum(pos)/len(pos) <= FLAG_BUDGET))
    rows.append(("flag everything", 1.0, 1.0, tot_oracle, tot_oracle / tot_waste, False))
    for name, frac, wk, fo, be, ok in sorted(rows, key=lambda t: t[4]):
        print(f"{name:>22} {frac*100:>7.1f}% {wk*100:>10.1f}% {fo:>10.0f} "
              f"{be:>11.1f} {'PASS' if ok else 'fail':>6}")
    best = min((r for r in rows if r[1] <= FLAG_BUDGET and not r[0].startswith("PERFECT")
                and r[0] != "flag everything"), key=lambda t: t[4], default=None)
    if best:
        print(f"\nbest cheap rule within the {FLAG_BUDGET*100:.0f}% budget: "
              f"{best[0]} at {best[4]:.1f} requests "
              f"({'PASS' if best[4] <= BREAKEVEN_BAR else 'FAIL'} "
              f"against the {BREAKEVEN_BAR}-request bar)")
    json.dump([{"rule": r[0], "flagged_frac": r[1], "waste_kept_frac": r[2],
                "oracle_ms": r[3], "breakeven": r[4], "ship": r[5]} for r in rows],
              open("experiments/exp005_breakeven.json", "w"), indent=2)
    return rows


if __name__ == "__main__":
    run()
    economics_per_predicate()
