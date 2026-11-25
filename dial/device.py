"""Build step 4b - a device: a SyncSet folder, a chunk pool, a have-check.

Device A and Device B are two folders on this machine.  Neither can see the
other's files; everything crosses as a message whose bytes are counted.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional, Sequence

from . import manifest as mf
from .keys import Key
from .store import ChunkCache, ChunkStore


def pack_bits(flags: Sequence[bool]) -> bytes:
    """A have-answer: one bit per question, which is what it would cost."""
    out = bytearray((len(flags) + 7) // 8)
    for i, f in enumerate(flags):
        if f:
            out[i >> 3] |= 1 << (i & 7)
    return bytes(out)


class Device:
    def __init__(self, name: str, root: str | Path, thumbs=None):
        self.name = name
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.state = self.root / ".dial"
        self.store = ChunkStore(self.state / "store")
        self.cache = ChunkCache(self.state / "chunkcache.json")
        self.thumbs = thumbs
        self.thumb_dir = self.state / "thumbs"
        self.thumb_dir.mkdir(parents=True, exist_ok=True)

    # -- A side -----------------------------------------------------------
    def scan(self) -> mf.Manifest:
        return mf.scan(self.root, self.store, self.cache, self.thumbs)

    # -- B side: the have-check ------------------------------------------
    def have_keys(self, kids: Iterable[str]) -> List[bool]:
        """Step 4: B reports, one bit per key, which keys it already has."""
        return [self.store.has_key(k) for k in kids]

    def have_chunks(self, hashes: Iterable[str]) -> List[bool]:
        return [self.store.has_chunk(h) for h in hashes]

    # -- B side: what it can show / open ----------------------------------
    def thumb_path(self, rel: str) -> Path:
        p = self.thumb_dir / (rel.replace("/", "__") + ".thumb.jpg")
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def write_file(self, rel: str, data: bytes) -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return p

    def has_original(self, entry: mf.Entry) -> bool:
        return (self.root / entry.path).exists()

    def has_preview(self, entry: mf.Entry) -> bool:
        return self.thumb_path(entry.path).exists()
