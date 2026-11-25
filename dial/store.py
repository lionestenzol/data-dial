"""Build step 3b - the local chunk pool and key index.

Each device has one: chunks addressed by SHA-256, and an index of every key it
holds.  A new chunk is a new word - stored once, reused next time.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from . import chunker
from .keys import Key, chunk_key, file_key, sha256_hex


class ChunkStore:
    def __init__(self, root: str | os.PathLike):
        self.root = Path(root)
        self.objects = self.root / "objects"
        self.objects.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "keys.jsonl"
        self._keys: Dict[str, Key] = {}
        self._load_index()

    # -- chunks -----------------------------------------------------------
    def _path(self, h: str) -> Path:
        return self.objects / h[:2] / h

    def has_chunk(self, h: str) -> bool:
        return self._path(h).exists()

    def put_chunk(self, data: bytes) -> Key:
        k = chunk_key(data)
        p = self._path(k.hash)
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            tmp = p.with_suffix(".tmp")
            tmp.write_bytes(data)
            tmp.replace(p)
        self.add_key(k)
        return k

    def get_chunk(self, h: str) -> bytes:
        return self._path(h).read_bytes()

    # -- key index --------------------------------------------------------
    def _load_index(self) -> None:
        if self.index_path.exists():
            for line in self.index_path.read_text().splitlines():
                if line.strip():
                    k = Key.from_dict(json.loads(line))
                    self._keys[k.kid] = k

    def add_key(self, key: Key) -> None:
        old = self._keys.get(key.kid)
        if old is not None and (old.child_keys or not key.child_keys):
            return
        self._keys[key.kid] = key
        with self.index_path.open("a") as fh:
            fh.write(json.dumps(key.as_dict()) + "\n")

    def has_key(self, kid: str) -> bool:
        return kid in self._keys

    def get_key(self, kid: str) -> Optional[Key]:
        return self._keys.get(kid)

    def kids(self) -> List[str]:
        return list(self._keys)

    def has_all_chunks(self, key: Key) -> bool:
        """True when this device can rebuild `key` from chunks it already has."""
        known = self._keys.get(key.kid)
        children = key.child_keys or (known.child_keys if known else ())
        if not children:
            return False
        return all(self.has_chunk(kid.rsplit(":", 1)[1]) for kid in children)

    def rebuild(self, children: Iterable[str]) -> bytes:
        return b"".join(self.get_chunk(kid.rsplit(":", 1)[1]) for kid in children)


def chunk_bytes(store: ChunkStore, data: bytes) -> Key:
    """Chunk a blob into the store and return its file key."""
    kids: List[str] = []
    for part in chunker.chunks(data):
        kids.append(store.put_chunk(part).kid)
    fk = file_key(sha256_hex(data), len(data), kids)
    store.add_key(fk)
    return fk


class ChunkCache:
    """Remembers (path, size, mtime) -> file key so re-scans are cheap."""

    def __init__(self, path: str | os.PathLike):
        self.path = Path(path)
        self.data: Dict[str, dict] = {}
        if self.path.exists():
            self.data = json.loads(self.path.read_text())

    def key_for(self, store: ChunkStore, path: Path) -> Key:
        st = path.stat()
        tag = f"{path}|{st.st_size}|{st.st_mtime_ns}"
        hit = self.data.get(tag)
        if hit:
            k = Key.from_dict(hit)
            if store.has_all_chunks(k):
                store.add_key(k)
                return k
        k = chunk_bytes(store, path.read_bytes())
        self.data[tag] = k.as_dict()
        return k

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data))
