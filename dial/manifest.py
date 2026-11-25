"""Build step 4a - the manifest A sends: one entry per file in SyncSet."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .keys import Key, manifest_key
from .store import ChunkCache, ChunkStore

PHOTO_EXT = {".jpg", ".jpeg", ".png", ".heic", ".webp", ".tif", ".tiff"}
PHOTO, FILE = "photo", "file"


def kind_of(path: Path) -> str:
    return PHOTO if path.suffix.lower() in PHOTO_EXT else FILE


@dataclass
class Entry:
    path: str
    size: int
    kind: str
    file_kid: str
    thumb_kid: Optional[str] = None
    thumb_size: int = 0

    def wire_dict(self) -> dict:
        d = {"path": self.path, "size": self.size, "kind": self.kind,
             "file_kid": self.file_kid}
        if self.thumb_kid:
            d["thumb_kid"] = self.thumb_kid
            d["thumb_size"] = self.thumb_size
        return d


@dataclass
class Manifest:
    entries: List[Entry] = field(default_factory=list)

    @property
    def key(self) -> Key:
        return manifest_key([e.wire_dict() for e in self.entries])

    def wire_bytes(self) -> int:
        return self.key.size

    def by_path(self) -> Dict[str, Entry]:
        return {e.path: e for e in self.entries}


def iter_files(root: Path):
    for p in sorted(root.rglob("*")):
        if p.is_file() and ".dial" not in p.parts:
            yield p


def scan(root: str | Path, store: ChunkStore, cache: ChunkCache,
         thumbs=None) -> Manifest:
    """Chunk every file under root and build the manifest.

    `thumbs`, when given, is the thumb maker from step 5; without it the
    manifest carries originals only.
    """
    root = Path(root)
    entries: List[Entry] = []
    for p in iter_files(root):
        rel = str(p.relative_to(root))
        fk = cache.key_for(store, p)
        kind = kind_of(p)
        e = Entry(path=rel, size=fk.size, kind=kind, file_kid=fk.kid)
        if kind == PHOTO and thumbs is not None:
            tk = thumbs.thumb_for(store, p)
            if tk is not None:
                e.thumb_kid, e.thumb_size = tk.kid, tk.size
        entries.append(e)
    cache.save()
    return Manifest(entries)
