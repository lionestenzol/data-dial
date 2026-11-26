#!/usr/bin/env python
"""Analyse experiment 006: what is the cheapest sufficient oracle?

Simulates best-of-R oracles from the disjoint simulation pool and scores every
pick against the disjoint truth pool, then turns pick quality into the only
number that decides deployment: break-even requests per expression.
"""
from __future__ import annotations

import json
import math
import pathlib
import statistics

R_GRID = (1, 2, 3, 4, 6, 8, 12, 24)
RP_GRID = (1, 2, 3, 6, 12)
POLICY = "cost_ast_size_tree"
BAR = 200
BUDGET = 0.20
TARGET = 1.2


def pick_by(adm, key):
    return min(range(len(adm)), key=lambda i: (adm[i][key], adm[i]["nodes"], adm[i]["tag"]))


def load():
    D = json.load(open("experiments/exp006_timings.json"))
    rows = []
    for r in D["rows"]:
        adm = r["admitted"]
        if len(adm) < 2:
            continue
        truth = [min(c["truth"]) for c in adm]
        rows.append({"group": pathlib.Path(r["source"]).name, "name": r["name"],
                     "adm": adm, "truth": truth,
                     "best_i": min(range(len(adm)), key=lambda i: truth[i]),
                     "policy_i": pick_by(adm, POLICY)})
    return rows, D["config"]


def oracle_pick(adm, R, probe=None):
    """What an oracle that spends R repeats would choose, and what it costs.

    Cost is evaluation time only - R passes over every admitted candidate -
    charged the same way 004 and 005 charged it so the numbers compare.
    """
    if probe is None:
        samples = [c["sim"][:R] for c in adm]
        cost = sum(sum(c["sim"][:R]) for c in adm)
    else:
        # probe samples are used only to RANK candidates, never as truth
        # (truth always comes from the deployed-size truth pool), so there is
        # no pool to split and all 12 samples are available.
        samples = [c["probe"][str(probe)][:R] for c in adm]
        cost = sum(sum(c["probe"][str(probe)][:R]) for c in adm)
    mins = [min(s) for s in samples]
    return min(range(len(adm)), key=lambda i: mins[i]), cost


def economics(rows, flagged, R, probe=None):
    """break-even = oracle ms spent / ms of waste actually recovered.

    Recovered waste is measured against TRUTH, so an oracle that mis-picks
    recovers less than the full waste - that is how pick quality enters the
    price, rather than through a mis-pick rate that costs nothing.
    """
    spent = recovered = 0.0
    mispicks = 0
    for r, fl in zip(rows, flagged):
        if not fl:
            continue
        i, cost = oracle_pick(r["adm"], R, probe)
        spent += cost
        policy_ms = r["truth"][r["policy_i"]]
        recovered += policy_ms - r["truth"][i]
        if i != r["best_i"]:
            mispicks += 1
    be = spent / recovered if recovered > 0 else math.inf
    return {"spent_ms": spent, "recovered_ms": recovered, "breakeven": be,
            "mispicks": mispicks, "n_flagged": sum(flagged)}


def main():
    rows, cfg = load()
    n = len(rows)
    print(f"{n} decisions, {len(set(r['group'] for r in rows))} groups\n")

    total_waste = sum(r["truth"][r["policy_i"]] - r["truth"][r["best_i"]] for r in rows)
    print(f"total recoverable waste under the policy: {total_waste:.3f} ms")

    all_flag = [True] * n
    perfect = [(r["truth"][r["policy_i"]] / r["truth"][r["best_i"]]) >= TARGET
               if r["truth"][r["best_i"]] > 0 else False for r in rows]
    # 005's best cheap rule: ast_size picks differently under DAG than tree
    cheap = [pick_by(r["adm"], "cost_ast_size") != r["policy_i"] for r in rows]
    print(f"perfect targeting flags {sum(perfect)} ({sum(perfect)/n*100:.1f}%), "
          f"dag_vs_tree flags {sum(cheap)} ({sum(cheap)/n*100:.1f}%)\n")

    out = {"n_decisions": n, "total_waste_ms": total_waste, "by_R": {}, "by_probe": {}}

    print("=" * 78)
    print("REPEAT REDUCTION at the deployed array size")
    print(f"{'R':>3} {'oracle ms':>10} {'recovered':>10} {'% of R=24':>10} "
          f"{'mispick%':>9} | {'BE all':>8} {'BE cheap':>9} {'BE perfect':>11}")
    rec24 = economics(rows, all_flag, 24)["recovered_ms"]
    for R in R_GRID:
        e_all = economics(rows, all_flag, R)
        e_ch = economics(rows, cheap, R)
        e_pf = economics(rows, perfect, R)
        out["by_R"][str(R)] = {"all": e_all, "cheap": e_ch, "perfect": e_pf}
        print(f"{R:>3} {e_all['spent_ms']:>10.0f} {e_all['recovered_ms']:>10.3f} "
              f"{e_all['recovered_ms']/rec24*100:>9.1f}% "
              f"{e_all['mispicks']/n*100:>8.1f}% | {e_all['breakeven']:>8.1f} "
              f"{e_ch['breakeven']:>9.1f} {e_pf['breakeven']:>11.1f}")

    print("\n" + "=" * 78)
    print("SIZE REDUCTION - rank on a small probe, run at the deployed size")
    print(f"{'probe':>7} {'R':>3} {'oracle ms':>10} {'recovered':>10} "
          f"{'% of full R=12':>15} {'mispick%':>9} | {'BE all':>8}")
    rec_full12 = economics(rows, all_flag, 12)["recovered_ms"]
    for m in cfg["PROBE_SIZES"]:
        for R in RP_GRID:
            e = economics(rows, all_flag, R, probe=m)
            out["by_probe"].setdefault(str(m), {})[str(R)] = e
            print(f"{m:>7} {R:>3} {e['spent_ms']:>10.1f} {e['recovered_ms']:>10.3f} "
                  f"{e['recovered_ms']/rec_full12*100:>14.1f}% "
                  f"{e['mispicks']/n*100:>8.1f}% | {e['breakeven']:>8.1f}")

    # cheapest configuration that clears the bar
    print("\n" + "=" * 78)
    cands = []
    for R in R_GRID:
        for lbl, fl in (("flag everything", all_flag), ("dag_vs_tree", cheap)):
            e = economics(rows, fl, R)
            if e["breakeven"] <= BAR and sum(fl) / n <= (1.0 if lbl == "flag everything" else BUDGET):
                cands.append((e["spent_ms"], f"R={R}, {lbl}", e["breakeven"], sum(fl) / n))
    for m in cfg["PROBE_SIZES"]:
        for R in RP_GRID:
            e = economics(rows, all_flag, R, probe=m)
            if e["breakeven"] <= BAR:
                cands.append((e["spent_ms"], f"probe={m}, R={R}, flag everything",
                              e["breakeven"], 1.0))
    if cands:
        cands.sort()
        print(f"configurations clearing the {BAR}-request bar, cheapest first:")
        for spent, lbl, be, fr in cands[:8]:
            print(f"  {lbl:<44} break-even {be:>7.1f} req, "
                  f"oracle {spent:>8.0f} ms, flags {fr*100:.0f}%")
        print(f"\nCHEAPEST PASSING CONFIG: {cands[0][1]} at {cands[0][2]:.1f} requests")
    else:
        print(f"NO configuration clears the {BAR}-request bar.")
    out["passing"] = [{"config": c[1], "breakeven": c[2], "oracle_ms": c[0],
                       "flagged_frac": c[3]} for c in cands]
    json.dump(out, open("experiments/exp006_results.json", "w"), indent=2)


if __name__ == "__main__":
    main()
