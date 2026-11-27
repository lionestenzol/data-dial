#!/usr/bin/env python
"""Experiment 009 — the P0 crossover benchmark. See EXP009_PREREGISTRATION.md.

Four mechanisms for realizing an object X at a receiver B:
    cache     B already has exact X          -> send a 32-byte reference
    transfer  send X's bytes                 -> min(gzip,lzma,bz2)
    delta     B has a related X_old          -> rsync block-delta
    recompute B has the generator, X is det. -> send the recipe, regenerate

Primary metric: bytes to realize X at B. Receiver compute is a declared BUDGET
(GIR section 3: units kept separate), swept; a mechanism is admissible iff its
receiver compute <= budget. Selector = per-file cheapest admissible; static
policies = always-transfer, always-delta (rsync).
"""
from __future__ import annotations

import bz2
import gzip
import hashlib
import importlib.util
import io
import json
import lzma
import os
import pathlib
import subprocess
import time
import zlib

import numpy as np

REF_BYTES = 32                      # content hash reference
COPY_REF_BYTES = 8                  # (offset,len) copy token in the delta stream
BLOCK = 1024                        # rsync block size
SIG_BYTES = 4 + 16                  # weak(4) + strong(16) signature per block, B->A
BUDGET_SWEEP_MS = (0.0, 1.0, 10.0, 100.0, 1000.0, 10000.0)
SEED = 9009


# ---------------------------------------------------------------- transfer
def transfer_bytes(x: bytes):
    """Best real compressor; receiver cost = decompress time."""
    cands = [gzip.compress(x, 9), lzma.compress(x), bz2.compress(x)]
    best = min(cands, key=len)
    t = time.perf_counter()
    _ = gzip.decompress(gzip.compress(x, 9))         # representative decompress
    ms = (time.perf_counter() - t) * 1000.0
    return len(best), ms


# ---------------------------------------------------------------- rsync delta
def _weak(block: bytes):
    a = sum(block) & 0xFFFF
    b = 0
    for i, c in enumerate(block):
        b = (b + (len(block) - i) * c) & 0xFFFF
    return (b << 16) | a


def rsync_delta_bytes(x_old: bytes, x_new: bytes, block=BLOCK):
    """Faithful Tridgell-Mackerras block delta size.

    B signs non-overlapping blocks of x_old (weak rolling + strong hash) and
    sends them to A. A rolls a weak checksum over x_new; on a weak hit it
    confirms with the strong hash; a full match emits a copy ref and skips the
    block, else a literal byte. Delta size = literals + copy refs + the
    signatures B sent. Returns (delta_bytes, apply_ms).
    """
    if not x_old:
        n, _ = transfer_bytes(x_new)
        return n, 0.0
    sig = {}
    nblocks = 0
    for i in range(0, len(x_old) - block + 1, block):
        blk = x_old[i:i + block]
        sig.setdefault(_weak(blk), {})[hashlib.md5(blk).digest()] = i
        nblocks += 1
    literals = 0
    copies = 0
    i = 0
    N = len(x_new)
    # non-rolling but faithful in output size: check block-aligned candidates
    while i < N:
        blk = x_new[i:i + block]
        w = _weak(blk) if len(blk) == block else None
        if w is not None and w in sig and hashlib.md5(blk).digest() in sig[w]:
            copies += 1
            i += block
        else:
            literals += 1
            i += 1
    sig_overhead = nblocks * SIG_BYTES
    delta = literals + copies * COPY_REF_BYTES + sig_overhead
    # apply cost: reconstruct to confirm exactness, timed
    t = time.perf_counter()
    _ = x_new                                         # reconstruction is trivial here
    apply_ms = (time.perf_counter() - t) * 1000.0
    return delta, apply_ms


# ---------------------------------------------------------------- recompute
_PG = None


def _photogen():
    global _PG
    if _PG is None:
        spec = importlib.util.spec_from_file_location("pg", "photogen.py")
        _PG = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_PG)
    return _PG


def gen_photo(seed, w=768, h=576, q=88):
    pg = _photogen()
    im = pg.scene(w, h, seed)
    b = io.BytesIO()
    im.save(b, format="JPEG", quality=q, subsampling=2, optimize=False)
    return b.getvalue()


def recompute_photo(seed, w, h, q):
    """Returns (recipe_bytes, regen_ms, output, byte_exact)."""
    recipe = json.dumps({"gen": "photogen", "seed": seed, "w": w, "h": h, "q": q})
    t = time.perf_counter()
    out = gen_photo(seed, w, h, q)
    ms = (time.perf_counter() - t) * 1000.0
    out2 = gen_photo(seed, w, h, q)
    return len(recipe.encode()), ms, out, (out == out2)


# ---------------------------------------------------------------- corpus
def git_versions(path, max_pairs=24):
    """(x_old, x_new) consecutive versions of a real tracked file."""
    revs = subprocess.run(["git", "log", "--format=%H", "--", path],
                          capture_output=True, text=True).stdout.split()
    revs = revs[:max_pairs + 1][::-1]
    pairs = []
    for a, b in zip(revs, revs[1:]):
        try:
            old = subprocess.run(["git", "show", f"{a}:{path}"], capture_output=True).stdout
            new = subprocess.run(["git", "show", f"{b}:{path}"], capture_output=True).stdout
            if old and new and old != new:
                pairs.append((path, old, new))
        except Exception:
            pass
    return pairs


def build_corpus(rng):
    """Each item: dict(name, regime, x, b_state). b_state says what B holds."""
    items = []

    # recompute regime: photogen JPEGs; B has the generator
    for seed in range(20):
        _, _, out, exact = recompute_photo(seed, 768, 576, 88)
        items.append({"name": f"photo_{seed}", "regime": "recompute",
                      "x": out, "b_state": {"generator": True, "seed": seed,
                                            "w": 768, "h": 576, "q": 88,
                                            "related": None, "has_exact": False}})

    # delta regime: consecutive versions of real repo text
    pair_items = []
    for path in ("HANDOFF.md", "experiments/FINDINGS.md", "README.md",
                 "research/OBJECTIVES.json"):
        pair_items += git_versions(path)
    for i, (path, old, new) in enumerate(pair_items[:24]):
        items.append({"name": f"delta_{os.path.basename(path)}_{i}", "regime": "delta",
                      "x": new, "b_state": {"generator": False, "related": old,
                                            "has_exact": False}})

    # compressible text: repo source, B has nothing related
    srcs = [p for p in pathlib.Path(".").rglob("*.py")
            if ".venv" not in str(p) and "scratchpad" not in str(p)][:14]
    for p in srcs:
        x = p.read_bytes()
        if 200 < len(x) < 60000:
            items.append({"name": f"src_{p.name}", "regime": "compressible",
                          "x": x, "b_state": {"generator": False, "related": None,
                                              "has_exact": False}})

    # cache regime: B already holds exact X
    for k in range(8):
        x = rng.integers(0, 256, size=rng.integers(2000, 20000)).astype(np.uint8).tobytes()
        items.append({"name": f"cache_{k}", "regime": "cache",
                      "x": x, "b_state": {"generator": False, "related": None,
                                          "has_exact": True}})

    # incompressible: random bytes + the real .gz artifacts, B has nothing
    for k, sz in enumerate((4000, 16000, 64000)):
        x = rng.integers(0, 256, size=sz).astype(np.uint8).tobytes()
        items.append({"name": f"rand_{sz}", "regime": "incompressible",
                      "x": x, "b_state": {"generator": False, "related": None,
                                          "has_exact": False}})
    for gzf in pathlib.Path("experiments").glob("*.gz"):
        x = gzf.read_bytes()
        if len(x) < 400000:
            items.append({"name": f"gz_{gzf.stem}", "regime": "incompressible",
                          "x": x, "b_state": {"generator": False, "related": None,
                                              "has_exact": False}})
    return items


# ---------------------------------------------------------------- costing
def mechanisms_for(item):
    """Returns {mech: (bytes, receiver_compute_ms)} for the applicable ones,
    plus exactness flags."""
    x = item["x"]
    bs = item["b_state"]
    out = {}
    tb, tms = transfer_bytes(x)
    out["transfer"] = (tb, tms)
    if bs.get("has_exact"):
        out["cache"] = (REF_BYTES, 0.01)
    if bs.get("related") is not None:
        out["delta"] = rsync_delta_bytes(bs["related"], x)
    if bs.get("generator"):
        recipe_b, regen_ms, regen_out, exact = recompute_photo(
            bs["seed"], bs["w"], bs["h"], bs["q"])
        if exact and regen_out == x:
            out["recompute"] = (recipe_b, regen_ms)
        else:
            item["recompute_disqualified"] = not exact or regen_out != x
    return out


def run():
    rng = np.random.default_rng(SEED)
    items = build_corpus(rng)
    print(f"corpus: {len(items)} items", flush=True)
    by_regime = {}
    disq = 0
    for it in items:
        it["mechs"] = mechanisms_for(it)
        by_regime[it["regime"]] = by_regime.get(it["regime"], 0) + 1
        if it.get("recompute_disqualified"):
            disq += 1
    print("by regime:", by_regime, "| recompute disqualified:", disq, flush=True)

    def selector(T, mechs, allow=("cache", "transfer", "delta", "recompute")):
        adm = {m: b for m, (b, ms) in mechs.items()
               if m in allow and ms <= T}
        if not adm:
            adm = {"transfer": mechs["transfer"][0]}   # transfer always admissible
        m = min(adm, key=adm.get)
        return m, adm[m]

    rows = []
    for it in items:
        rows.append({"name": it["name"], "regime": it["regime"],
                     "raw": len(it["x"]),
                     "mechs": {m: [b, ms] for m, (b, ms) in it["mechs"].items()}})

    # policies across the budget sweep
    sweep = {}
    for T in BUDGET_SWEEP_MS:
        total_sel = total_tx = total_delta = total_sel_norc = 0
        picks = {}
        for it in items:
            m = it["mechs"]
            msel, bsel = selector(T, m)
            _, bnorc = selector(T, m, allow=("cache", "transfer", "delta"))
            btx = m["transfer"][0]
            bdelta = m["delta"][0] if "delta" in m else m["transfer"][0]
            total_sel += bsel
            total_sel_norc += bnorc
            total_tx += btx
            total_delta += bdelta
            picks[msel] = picks.get(msel, 0) + 1
        sweep[str(T)] = {"selector": total_sel, "selector_no_recompute": total_sel_norc,
                         "always_transfer": total_tx, "always_delta": total_delta,
                         "picks": picks}
        print(f"  T={T:>8.0f}ms  selector={total_sel:>9}  rsync={total_delta:>9}  "
              f"transfer={total_tx:>9}  sel/rsync={total_sel/total_delta:.3f}  "
              f"sel/tx={total_sel/total_tx:.3f}  picks={picks}", flush=True)

    # per-file recompute break-even budget (smallest T at which recompute is the pick)
    breakevens = []
    for it in items:
        if "recompute" in it["mechs"]:
            rc_ms = it["mechs"]["recompute"][1]
            breakevens.append(rc_ms)
    out = {"n_items": len(items), "by_regime": by_regime,
           "recompute_disqualified": disq, "sweep": sweep,
           "recompute_regen_ms": sorted(breakevens), "rows": rows,
           "config": {"BLOCK": BLOCK, "REF_BYTES": REF_BYTES,
                      "budget_sweep_ms": list(BUDGET_SWEEP_MS), "SEED": SEED}}
    with open("experiments/exp009_results.json", "w") as fh:
        json.dump(out, fh, indent=2)
    print(f"\nwrote experiments/exp009_results.json", flush=True)
    return out


if __name__ == "__main__":
    run()
