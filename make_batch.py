#!/usr/bin/env python3
"""Build the test batch: photos and documents in a SyncSet folder.

  make_batch.py day1 --out DIR [--photos 30] [--docs 12]
  make_batch.py day2 --out DIR [--photos 15] [--edits 3]

Day 1 is the starting library.  Day 2 is the spec's daily task: add 10-20
photos, edit 1-3 documents.

The documents are real files taken from this machine (vim's own manuals and
other package documentation under /usr/share) - real prose, real markup, real
line endings.  The photos are made locally by photogen.py; there is no camera
and no network here, so they are synthetic, but they are built to compress
and to chunk the way camera JPEGs do.
"""
from __future__ import annotations

import argparse
import random
import shutil
from pathlib import Path

from photogen import save_photo

DOC_SOURCES = [
    Path("/usr/share/vim/vim91/doc"),
    Path("/usr/share/doc"),
    Path("/usr/share/common-licenses"),
]


def real_documents(n: int, seed: int = 0):
    """Pick n real text documents off this machine, smallest spread first."""
    found = []
    for root in DOC_SOURCES:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if p.is_file() and p.suffix.lower() in (".txt", ".md", ".rst"):
                try:
                    size = p.stat().st_size
                except OSError:
                    continue
                if 20_000 <= size <= 1_500_000:
                    found.append(p)
    found.sort()
    random.Random(seed).shuffle(found)
    return found[:n]


def day1(ns):
    out = Path(ns.out)
    (out / "Photos").mkdir(parents=True, exist_ok=True)
    (out / "Docs").mkdir(parents=True, exist_ok=True)
    for i in range(ns.photos):
        save_photo(out / "Photos" / f"IMG_{i:04d}.jpg", seed=1000 + i,
                   size=(ns.width, ns.height))
    for p in real_documents(ns.docs, seed=ns.seed):
        shutil.copy2(p, out / "Docs" / p.name)
    report(out)


def day2(ns):
    out = Path(ns.out)
    existing = sorted((out / "Photos").glob("IMG_*.jpg"))
    start = 1 + max(int(p.stem.split("_")[1]) for p in existing) if existing else 0
    new = []
    for i in range(ns.photos):
        new.append(save_photo(out / "Photos" / f"IMG_{start + i:04d}.jpg",
                              seed=5000 + start + i, size=(ns.width, ns.height)))
    docs = sorted((out / "Docs").iterdir())
    rnd = random.Random(ns.seed)
    edited = rnd.sample(docs, min(ns.edits, len(docs)))
    for d in edited:
        edit_in_place(d, rnd)
    print("new photos:", " ".join(f"Photos/{p.name}" for p in new))
    print("edited docs:", " ".join(f"Docs/{p.name}" for p in edited))
    report(out)


def edit_in_place(path: Path, rnd: random.Random) -> None:
    """The everyday edit: a paragraph goes in somewhere in the middle."""
    text = path.read_text(errors="replace").splitlines()
    at = rnd.randrange(len(text) // 4, max(2, 3 * len(text) // 4))
    para = ["", "NOTE added " + "on the daily pass. " * 8, ""]
    path.write_text("\n".join(text[:at] + para + text[at:]) + "\n")


def report(out: Path) -> None:
    photos = list((out / "Photos").glob("*"))
    docs = list((out / "Docs").glob("*"))
    pb = sum(p.stat().st_size for p in photos)
    db = sum(p.stat().st_size for p in docs)
    print(f"SyncSet {out}: {len(photos)} photos ({pb/1e6:.1f} MB), "
          f"{len(docs)} documents ({db/1e6:.1f} MB), total {(pb+db)/1e6:.1f} MB")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn, ph in (("day1", day1, 30), ("day2", day2, 15)):
        p = sub.add_parser(name)
        p.add_argument("--out", required=True)
        p.add_argument("--photos", type=int, default=ph)
        p.add_argument("--docs", type=int, default=24)
        p.add_argument("--edits", type=int, default=3)
        p.add_argument("--width", type=int, default=4032)
        p.add_argument("--height", type=int, default=3024)
        p.add_argument("--seed", type=int, default=11)
        p.set_defaults(fn=fn)
    ns = ap.parse_args(argv)
    return ns.fn(ns) or 0


if __name__ == "__main__":
    raise SystemExit(main())
