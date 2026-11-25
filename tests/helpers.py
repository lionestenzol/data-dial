"""Small fixtures: two devices and a handful of photos and documents."""
from __future__ import annotations

import hashlib
import random
from pathlib import Path

from dial.device import Device
from dial.thumb import ThumbMaker
from photogen import save_photo


def devices(tmp: Path):
    a = Device("A", tmp / "A", thumbs=ThumbMaker(tmp / "A" / ".dial" / "thumbs.json"))
    b = Device("B", tmp / "B")
    return a, b


def photo(path: Path, seed: int = 0, size=(1600, 1200)) -> Path:
    """A plausible photo (see photogen): smooth scene, edges, grain, JPEG q88."""
    return save_photo(path, seed=seed, size=size)


def document(path: Path, lines: int = 4000, seed: int = 0) -> Path:
    rnd = random.Random(seed)
    words = ["sync", "chunk", "recipe", "thumbnail", "device", "manifest",
             "folder", "photo", "document", "byte", "hash", "key"]
    body = "\n".join(" ".join(rnd.choice(words) for _ in range(12))
                     for _ in range(lines))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body + "\n")
    return path


def edit_document(path: Path, where: float = 0.5, text: str = None) -> Path:
    """Insert a paragraph in the middle - the everyday document edit."""
    lines = path.read_text().splitlines()
    at = int(len(lines) * where)
    para = text or ("NEW PARAGRAPH inserted by the daily task. " * 6)
    path.write_text("\n".join(lines[:at] + [para] + lines[at:]) + "\n")
    return path


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def same(a: Path, b: Path) -> bool:
    return sha(a) == sha(b)


def payload_for(records, path: str, form: str = None) -> int:
    return sum(r["payload_bytes"] for r in records
               if r["path"] == path and (form is None or r["form"] == form))


def forms_for(records, path: str):
    return [r["form"] for r in records if r["path"] == path]
