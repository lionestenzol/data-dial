"""Build step 9 - the Raw Sync toggle: the full-sync baseline.

Every new or changed file, sent whole.  This is the floor the dial has to
beat, and the number the logger's full_sync_bytes column must match.
"""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Dict

from .manifest import iter_files


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def raw_sync(src: str | Path, dst: str | Path, apply: bool = True) -> Dict[str, int]:
    """Copy every file that is new or changed on the far side; count the bytes."""
    src, dst = Path(src), Path(dst)
    dst.mkdir(parents=True, exist_ok=True)
    sent = 0
    files = 0
    for p in iter_files(src):
        rel = p.relative_to(src)
        target = dst / rel
        if target.exists() and target.stat().st_size == p.stat().st_size \
                and _sha(target) == _sha(p):
            continue
        files += 1
        sent += p.stat().st_size
        if apply:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)
    return {"files": files, "bytes": sent}
