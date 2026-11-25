"""Preview-first library view on device B.

Every entry in the manifest shows up at once.  Photos show their thumbnail;
the original arrives only when it is opened.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .device import Device
from .manifest import Manifest


@dataclass
class Row:
    path: str
    shown_as: str      # original | preview | missing
    bytes_held: int


def library(dev: Device, man: Manifest) -> List[Row]:
    rows = []
    for e in man.entries:
        if dev.has_original(e):
            rows.append(Row(e.path, "original", (dev.root / e.path).stat().st_size))
        elif dev.has_preview(e):
            rows.append(Row(e.path, "preview", dev.thumb_path(e.path).stat().st_size))
        else:
            rows.append(Row(e.path, "missing", 0))
    return rows


def visible(rows: List[Row]) -> int:
    return sum(1 for r in rows if r.shown_as != "missing")
