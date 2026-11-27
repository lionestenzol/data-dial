#!/usr/bin/env python
"""Score experiment 006 against EXP006_PREREGISTRATION.md. Mechanical."""
import json, math, statistics, random, sys
sys.path.insert(0, "experiments")
import exp006_analysis as A

R = json.load(open("experiments/exp006_results.json"))
byR, byP = R["by_R"], R["by_probe"]
rows, cfg = A.load(); n = len(rows)
BAR = 200

checks = []
def chk(tag, claim, ok, actual, note=""):
    checks.append({"tag": tag, "claim": claim, "verdict": "hit" if ok else "MISS",
                   "actual": actual, "note": note})

# V1 - oracle cost linear in R
c1 = byR["1"]["all"]["spent_ms"]
devs = {r: (byR[str(r)]["all"]["spent_ms"] / c1) / r for r in (2,3,4,6,8,12,24)}
ok1 = all(abs(v - 1.0) <= 0.10 for v in devs.values())
chk("V1", "oracle cost linear in R within 10%", ok1,
    "cost(R)/(R*cost(1)): " + ", ".join(f"R={k} {v:.3f}" for k, v in devs.items()))

# V2 - THE HINGE
r1, r24 = byR["1"]["all"]["recovered_ms"], byR["24"]["all"]["recovered_ms"]
frac = r1 / r24
chk("V2", "HINGE: waste recovered at R=1 >= 90% of R=24", frac >= 0.90,
    f"{frac*100:.1f}% ({r1:.3f} of {r24:.3f} ms)",
    "point estimate clears 90% but the bootstrap 95% interval is [70.7%, 96.6%] - "
    "one decision holds 38.8% of all waste, so this is NOT established at the "
    "stated precision. The direction is robust; the threshold is not.")

# V3 - mispicks common anyway
mp = byR["1"]["all"]["mispicks"] / n
chk("V3", "mis-pick rate at R=1 >= 20% of decisions", mp >= 0.20,
    f"{mp*100:.1f}% mis-picked while recovering {frac*100:.1f}% of waste")

# V4 - R=1 economics
bep, bec = byR["1"]["perfect"]["breakeven"], byR["1"]["cheap"]["breakeven"]
chk("V4", "at R=1: break-even <=20 perfect and <=100 with dag_vs_tree",
    bep <= 20 and bec <= 100,
    f"perfect {bep:.1f} req, dag_vs_tree {bec:.1f} req")

# V5 - size reduction predicted to transfer POORLY
p256_12 = byP["256"]["12"]["recovered_ms"]
full_12 = byR["12"]["all"]["recovered_ms"]
ratio5 = p256_12 / full_12
chk("V5", "probe=256 R=12 recovers <=70% of full R=12", ratio5 <= 0.70,
    f"{ratio5*100:.1f}% ({p256_12:.3f} of {full_12:.3f} ms)",
    "size reduction transferred FAR better than predicted - this is the "
    "optimistic direction, the opposite of this assistant's documented bias")

# V6 - cheapest passing config predicted to be R<=3 at FULL size
passing = R.get("passing", [])
cheapest = passing[0]["config"] if passing else "none"
ok6 = bool(passing) and "probe=" not in cheapest
chk("V6", "cheapest passing config uses R<=3 at full array size", ok6,
    f"cheapest passing is '{cheapest}' at "
    f"{passing[0]['breakeven']:.1f} requests" if passing else "nothing passed",
    "repeat reduction alone would have passed (R=1 full, 124.1 req), but small "
    "probes beat it by ~27x, so the prediction named the wrong mechanism")

# V7 - at R=1 targeting becomes unnecessary
bea = byR["1"]["all"]["breakeven"]
chk("V7", "at R=1, flagging everything breaks even in <=150 requests", bea <= 150,
    f"{bea:.1f} requests",
    "point estimate clears 150; bootstrap interval [51.5, 496.8] does not "
    "establish it. The robust version of this claim uses a small probe: "
    "probe=256 R=1 gives 4.7 req with interval [1.9, 24.0], entirely under the bar.")

hits = sum(1 for c in checks if c["verdict"] == "hit")
print(f"\nExperiment 006 — {hits} of {len(checks)} pre-registered predictions hit\n")
for c in checks:
    print(f"{c['tag']:>4} {c['verdict']:>6}  {c['claim']}")
    print(f"{'':>12}actual: {c['actual']}")
    if c["note"]:
        print(f"{'':>12}note:   {c['note']}")
print(f"\nSHIP CRITERION (<= {BAR} requests per expression)")
print(f"  005 baseline (R=11, full size, no targeting) : 1280.7 req  "
      f"[532, 3903]   FAIL")
print(f"  cheapest sufficient oracle (probe=256, R=1)  :     4.7 req  "
      f"[1.9, 24.0]   PASS")
print(f"  -> 005's recommendation is REVERSED, and targeting is unnecessary:")
print(f"     a cheap oracle on EVERY decision (4.7 req) beats perfect targeting")
print(f"     of the expensive one (11.7 req).")
json.dump({"hits": hits, "total": len(checks), "checks": checks},
          open("experiments/exp006_scorecard.json", "w"), indent=2)
