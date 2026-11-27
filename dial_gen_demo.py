#!/usr/bin/env python3
"""dial_gen_demo - the regenerate arm, actually running.

Two local folders stand in for Device A and Device B; nothing crosses but
counted messages (same engine as dial_sim).  A holds a pile of photos and -
this is the new part - the RECIPE that made each one.  B starts empty.

We run the same day twice on a fresh B:

  ARM OFF  - A discarded the recipes.  Originals cross as raw chunks (what any
             content-addressed sync, rsync included, is limited to).
  ARM ON   - A kept the recipes and B has the generator.  Each original crosses
             as an ~80-byte recipe; B reruns the generator and verifies the
             bytes are identical.

Both reconstruct every file byte-for-byte - that is checked, not assumed.  The
only difference is how much crossed the wire, and how much CPU B spent.

    python3 dial_gen_demo.py [--n 8]
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import tempfile
from pathlib import Path

from dial.device import Device
from dial.engine import Engine
from dial.generators import GenRecipe
from dial.thumb import ThumbMaker
from dial.wire import Ledger
from photogen import save_photo

SIZE = (1600, 1200)
QUALITY = 88


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build_A(root: Path, n: int):
    """A photo library, plus the provenance A chose to keep for each photo."""
    provenance = {}
    truth = {}
    for i in range(n):
        rel = f"pic{i}.jpg"
        save_photo(root / rel, seed=i, size=SIZE, quality=QUALITY)
        provenance[rel] = GenRecipe("photo:v1",
                                    {"seed": i, "width": SIZE[0],
                                     "height": SIZE[1], "quality": QUALITY})
        truth[rel] = sha(root / rel)
    return provenance, truth


def run_once(src: Path, keep_recipes: bool, provenance, b_has_generator=True):
    """One fresh B, pull every original, return (ledger, result, B-root)."""
    work = Path(tempfile.mkdtemp())
    a_root, b_root = work / "A", work / "B"
    shutil.copytree(src, a_root)
    A = Device("A", a_root,
               thumbs=ThumbMaker(a_root / ".dial" / "thumbs.json"),
               provenance=provenance if keep_recipes else {})
    B = Device("B", b_root,
               generators=None if b_has_generator else set())
    led = Ledger()
    opens = sorted(p.name for p in src.glob("*.jpg"))
    res = Engine(A, B, led).sync(open_paths=opens)
    return led, res, b_root


def verify(b_root: Path, truth: dict) -> bool:
    ok = True
    for rel, want in truth.items():
        got = sha(b_root / rel) if (b_root / rel).exists() else "MISSING"
        if got != want:
            print(f"  MISMATCH {rel}: {got[:12]} != {want[:12]}")
            ok = False
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8, help="number of photos")
    args = ap.parse_args()

    src = Path(tempfile.mkdtemp()) / "lib"
    src.mkdir(parents=True)
    provenance, truth = build_A(src, args.n)
    total_orig = sum((src / r).stat().st_size for r in truth)
    recipe_bytes = sum(provenance[r].wire_bytes() for r in truth)

    off_led, off_res, off_b = run_once(src, keep_recipes=False, provenance=provenance)
    on_led, on_res, on_b = run_once(src, keep_recipes=True, provenance=provenance)

    off_ok = verify(off_b, truth)
    on_ok = verify(on_b, truth)

    print(f"\n{args.n} photos, {total_orig/1e6:.2f} MB of originals on A\n")
    print(f"{'':22}{'ARM OFF (raw)':>16}{'ARM ON (regen)':>16}")
    print(f"{'dial bytes on wire':22}{off_led.dial_bytes:>16,}{on_led.dial_bytes:>16,}")
    print(f"{'recipes arrived':22}{0:>16}{on_res.regen_count:>16}")
    print(f"{'B regenerate CPU ms':22}{0.0:>16.0f}{on_res.regen_ms:>16.0f}")
    print(f"{'raw fallbacks':22}{off_res.fallbacks:>16}{on_res.fallbacks:>16}")
    print(f"{'every file byte-exact':22}{str(off_ok):>16}{str(on_ok):>16}")
    if on_led.dial_bytes:
        print(f"\nregenerate arm moved {off_led.dial_bytes / on_led.dial_bytes:.1f}x "
              f"fewer bytes; each {total_orig/args.n/1e3:.0f} KB photo crossed as "
              f"a {recipe_bytes/args.n:.0f}-byte recipe.")
    assert off_ok and on_ok, "byte-exactness failed"


if __name__ == "__main__":
    main()
