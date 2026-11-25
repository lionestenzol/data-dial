"""Build step 5 - thumb-v1: 512 px long edge, JPEG quality 70.

A thumbnail is a visual-preview key.  B checks the SHA-256 of A's exact
thumbnail bytes, so the maker has to be deterministic: same original in, same
bytes out, no timestamps, no EXIF carried over.
"""
from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Dict, Optional

from PIL import Image

from .keys import Key, thumb_key
from .store import ChunkStore

LONG_EDGE = 512
QUALITY = 70
RULE = "thumb-v1"


def render(path: str | Path) -> Optional[bytes]:
    """thumb-v1 bytes for an image, or None if it is not an image we can read."""
    try:
        with Image.open(path) as im:
            im.draft("RGB", (LONG_EDGE, LONG_EDGE))   # fast JPEG downscale
            im = im.convert("RGB")
            w, h = im.size
            scale = LONG_EDGE / float(max(w, h))
            if scale < 1.0:
                im = im.resize((max(1, round(w * scale)), max(1, round(h * scale))),
                               Image.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=QUALITY, optimize=True)
            return buf.getvalue()
    except Exception:
        return None


class ThumbMaker:
    """Makes thumb-v1 blobs and remembers them by (path, size, mtime)."""

    def __init__(self, cache_path: str | Path | None = None):
        self.cache_path = Path(cache_path) if cache_path else None
        self.cache: Dict[str, dict] = {}
        if self.cache_path and self.cache_path.exists():
            self.cache = json.loads(self.cache_path.read_text())

    def thumb_for(self, store: ChunkStore, path: str | Path) -> Optional[Key]:
        path = Path(path)
        st = path.stat()
        tag = f"{path}|{st.st_size}|{st.st_mtime_ns}"
        hit = self.cache.get(tag)
        if hit and store.has_chunk(hit["hash"]):
            k = Key.from_dict(hit)
            store.add_key(k)
            return k
        data = render(path)
        if data is None:
            return None
        store.put_chunk(data)          # the blob lives in the pool
        k = thumb_key(data)
        store.add_key(k)
        self.cache[tag] = k.as_dict()
        self._save()
        return k

    def _save(self) -> None:
        if self.cache_path:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(json.dumps(self.cache))
