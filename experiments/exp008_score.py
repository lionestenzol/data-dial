#!/usr/bin/env python
"""Score experiment 008 against EXP008_PREREGISTRATION.md. Mechanical."""
import json, math

R = json.load(open("experiments/exp008_results.json"))
A, D, S = R["arms"], R["detail"], R["op_cost_sweep"]
BASE = ("direct", "memo", "memo_canon")
NORM = ("memo_sympy", "memo_egglog")
checks = []
def chk(tag, claim, ok, actual, note=""):
    checks.append({"tag":tag,"claim":claim,"verdict":"hit" if ok else "MISS",
                   "actual":actual,"note":note})

def tot(arm, split=None):
    if split is None: return A[arm]["total_ms"]
    return D[arm][f"split:{split}"]["total_ms"]
def p50(arm, split): return D[arm][f"split:{split}"]["p50"]

# Y1 mismatches
mm = {a: A[a].get("mismatches", "n/a") for a in A}
impl = [a for a in A if a != "memo_egglog_persist"]
chk("Y1","zero mismatches across all implemented arms",
    all(A[a]["mismatches"]==0 for a in impl),
    ", ".join(f"{a}:{A[a]['mismatches']}" for a in impl))

# Y2 memo avoids 70-75
h = A["memo"]["hits"]
chk("Y2","arm 2 avoids re-execution on 70-75 requests", 70<=h<=75,
    f"{h} hits of {A['memo']['requests']} requests")

# Y3 canon captures >=50% of equiv_form misses
eq_n = R["meta"]["by_case"]["equiv_form"]
extra = A["memo_canon"]["hits"] - A["memo"]["hits"]
frac = extra/eq_n
chk("Y3","free canonicalisation captures >=50% of the equiv_form misses", frac>=0.50,
    f"{extra} extra hits over arm 2 = {frac*100:.0f}% of the {eq_n} equiv_form requests")

# Y4 headline: no normalising arm gets >=10% total-time improvement over best baseline
best_base_prim = min(tot(a,"primary") for a in BASE)
best_norm_prim = min(tot(a,"primary") for a in NORM)
impr = (best_base_prim - best_norm_prim)/best_base_prim
chk("Y4","NO normalising arm reaches >=10% total-time improvement on primary", impr < 0.10,
    f"best baseline {best_base_prim:.2f}ms vs best normalising {best_norm_prim:.2f}ms "
    f"= {impr*100:+.1f}% (threshold needs >= +10%)")

# Y5 arms 4/5 >10x slower than arm 3
r4 = tot("memo_sympy")/tot("memo_canon"); r5 = tot("memo_egglog")/tot("memo_canon")
chk("Y5","arms 4 and 5 are >10x slower in total time than arm 3", r4>10 and r5>10,
    f"memo_sympy {r4:.1f}x, memo_egglog {r5:.1f}x of memo_canon "
    f"({tot('memo_canon'):.1f}ms)")

# Y6 unrelated split regression >10% median vs arm 2
g4 = (p50("memo_sympy","unrelated")-p50("memo","unrelated"))/p50("memo","unrelated")
g5 = (p50("memo_egglog","unrelated")-p50("memo","unrelated"))/p50("memo","unrelated")
chk("Y6","arms 4/5 regress >10% median on the unrelated split", g4>0.10 and g5>0.10,
    f"memo_sympy {g4*100:+.0f}%, memo_egglog {g5*100:+.0f}% median vs arm 2")

# Y7 break-even op cost
costs = sorted(float(c) for c in S)
be = None
for c in costs:
    bb = min(S[str(c)][a]["accounted_ms"] for a in BASE)
    sy = S[str(c)]["memo_sympy"]["accounted_ms"]
    if sy <= bb: be = c; break
ratios = ", ".join(f"{c:g}us:{S[str(c)]['memo_sympy']['accounted_ms']/min(S[str(c)][a]['accounted_ms'] for a in BASE):.2f}x" for c in costs)
chk("Y7","break-even op cost at which arm 4 beats arm 3 is >=100us/op", be is not None and be>=100,
    f"NO break-even found up to {costs[-1]:g}us/op; ratio plateaus -> {ratios}",
    "stronger negative than predicted: the prediction assumed a break-even EXISTS. "
    "It does not, because SymPy's expanded normal form executes MORE operations "
    f"({A['memo_sympy']['ops_executed']} vs {A['direct']['ops_executed']} for plain "
    "direct evaluation), so making operations costlier hurts the normalising arm faster "
    "than it helps it.")

# Y8 adversarial blowup
adv_growth = A["memo_sympy"]["norm_node_growth"]
egg_skip = A["memo_egglog"]["norm_skipped"]
advn = R["meta"]["by_case"]["adversarial"]
ok8 = adv_growth > 0 or egg_skip > 0 or A["memo_sympy"]["norm_timeouts"]>0
chk("Y8","on adversarial requests an arm times out or node count grows >=10x", ok8,
    f"memo_sympy net node growth {adv_growth:+d} across all requests; "
    f"memo_egglog skipped {egg_skip} requests over its {R['config']['EGG_NODE_CAP']}-node cap; "
    f"timeouts sympy={A['memo_sympy']['norm_timeouts']} egglog={A['memo_egglog']['norm_timeouts']}")

# Y9 canon retains fewer cache entries
c2, c3 = A["memo"]["cache_entries"], A["memo_canon"]["cache_entries"]
chk("Y9","arm 3 retains >=10% fewer cache entries than arm 2", (c2-c3)/c2 >= 0.10,
    f"arm 2 {c2} entries, arm 3 {c3} = {(c2-c3)/c2*100:+.0f}%")

hits = sum(1 for c in checks if c["verdict"]=="hit")
print(f"\nExperiment 008 — {hits} of {len(checks)} pre-registered predictions hit\n")
for c in checks:
    print(f"{c['tag']:>4} {c['verdict']:>6}  {c['claim']}")
    print(f"{'':>12}actual: {c['actual']}")
    if c["note"]: print(f"{'':>12}note:   {c['note']}")

print("\n" + "="*78)
print("VERDICT against NEXT_EXPERIMENT.md's declared thresholds")
print(f"  zero mismatches .................. {'PASS' if all(A[a]['mismatches']==0 for a in impl) else 'FAIL'}")
print(f"  >=10% total-time improvement ..... {'PASS' if impr>=0.10 else 'FAIL'}  ({impr*100:+.1f}% on primary)")
print(f"  <=10% median regression unrelated  {'PASS' if max(g4,g5)<=0.10 else 'FAIL'}  (worst {max(g4,g5)*100:+.0f}%)")
pk = R.get("peak_rss_mb_final",0); cap = R["config"]["MEM_CAP_GB"]*1024
print(f"  within {cap:.0f} MB memory cap ......... {'PASS' if pk<=cap else 'FAIL'}  ({pk:.0f} MB)")
pers = A.get("memo_egglog_persist",{})
print(f"  persistent e-graph completed ..... {'PASS' if pers.get('completed') else 'FAIL'}  "
      f"{pers.get('failure','')[:60]}")
print(f"\n  -> the claimed advantage must be {'KEPT' if impr>=0.10 else 'NARROWED OR STOPPED'}")
json.dump({"hits":hits,"total":len(checks),"checks":checks,
           "improvement_primary":impr,"breakeven_op_cost_us":be,
           "worst_unrelated_regression":max(g4,g5)},
          open("experiments/exp008_scorecard.json","w"), indent=2)
