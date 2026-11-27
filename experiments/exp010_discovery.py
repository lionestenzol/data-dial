#!/usr/bin/env python
"""Experiment 010 - does discovery eat the 4x? See EXP010_PREREGISTRATION.md.

Reuses 009's per-item mechanism costs. Charges each policy its own discovery:
always-transfer pays nothing; always-delta (rsync) pays block signatures already
inside 009's delta bytes; the selector pays a manifest (content hashes +
capability list). recompute additionally requires A to hold the recipe, modeled
by provenance coverage p. Question: after charging discovery, does the selector
still beat rsync?
"""
from __future__ import annotations
import json, random

HASH_BYTES = 32          # content hash advertised per exact file B holds
CAP_BYTES = 16           # one entry per generator id B advertises
BUDGET_MS = 1000.0       # fixed compute budget (009's headline point)
P_SWEEP = (0.0, 0.25, 0.5, 0.75, 1.0)
SEED = 10010

R = json.load(open("experiments/exp009_results.json"))
items = R["rows"]

# reconstruct B-state facts from 009: which items are cache/recompute/delta eligible
def eligibility(it):
    m = it["mechs"]
    return {"cache": "cache" in m, "recompute": "recompute" in m, "delta": "delta" in m}

def manifest_bytes(items):
    """B advertises: a content hash per exact file it holds, one entry per
    generator it has. The delta-signature bytes are already inside each item's
    delta cost, so they are not double-counted here."""
    n_cache = sum(1 for it in items if eligibility(it)["cache"])
    # distinct generators B advertises (here: photogen = 1 capability)
    n_gen = 1 if any(eligibility(it)["recompute"] for it in items) else 0
    return n_cache * HASH_BYTES + n_gen * CAP_BYTES

def realised(items, p, rng):
    """Selector bytes at budget BUDGET_MS with provenance coverage p, plus the
    manifest. recompute only available if B-eligible AND A kept the recipe."""
    man = manifest_bytes(items)
    total = man
    picks = {}
    for it in items:
        m = it["mechs"]
        adm = {}
        for mech, (b, ms) in m.items():
            if ms > BUDGET_MS:
                continue
            if mech == "recompute" and rng.random() >= p:
                continue                      # A did not retain the recipe
            adm[mech] = b
        if not adm:
            adm = {"transfer": m["transfer"][0]}
        mech = min(adm, key=adm.get)
        total += adm[mech]
        picks[mech] = picks.get(mech, 0) + 1
    return total, man, picks

def main():
    always_tx = sum(it["mechs"]["transfer"][0] for it in items)
    always_delta = sum((it["mechs"].get("delta") or it["mechs"]["transfer"])[0] for it in items)
    man = manifest_bytes(items)

    print(f"corpus {len(items)} items | always_transfer={always_tx} "
          f"always_delta(rsync)={always_delta} | manifest={man}B "
          f"({man/always_delta*100:.2f}% of rsync)\n")
    rng = random.Random(SEED)
    out = {"always_transfer": always_tx, "always_delta": always_delta,
           "manifest_bytes": man, "budget_ms": BUDGET_MS, "by_p": {}}
    # average over several provenance draws per p for stability
    print(f"{'p':>5} {'selector':>10} {'manifest':>9} {'sel/rsync':>10} "
          f"{'sel/tx':>8} {'beats rsync':>12}  picks")
    for p in P_SWEEP:
        sels, mans = [], []
        last_picks = None
        for _ in range(21):
            s, mb, picks = realised(items, p, rng)
            sels.append(s); mans.append(mb); last_picks = picks
        sel = sum(sels) / len(sels)
        out["by_p"][str(p)] = {"selector": sel, "manifest": man,
                               "sel_over_rsync": sel / always_delta,
                               "sel_over_tx": sel / always_tx,
                               "beats_rsync_x": always_delta / sel,
                               "picks": last_picks}
        print(f"{p:>5.2f} {sel:>10.0f} {man:>9} {sel/always_delta:>10.3f} "
              f"{sel/always_tx:>8.3f} {always_delta/sel:>11.2f}x  {last_picks}")
    json.dump(out, open("experiments/exp010_results.json", "w"), indent=2)
    print("\nwrote experiments/exp010_results.json")

if __name__ == "__main__":
    main()
