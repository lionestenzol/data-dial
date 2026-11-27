"""Message framing, byte accounting and the fault injector.

Nothing crosses a network here, so the Link is where "as if sent" is made
true: every message that is handed over is charged to the ledger, header and
all, exactly once.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import zstandard

HEADER_BYTES = 64
PACK_LIMIT = 1024 * 1024          # 1 MiB per message

_ZC = zstandard.ZstdCompressor(level=3)
_ZD = zstandard.ZstdDecompressor()


def compress(data: bytes, photo: bool) -> Tuple[bytes, str]:
    """zstd for non-photo chunks; photos are already compressed."""
    if photo:
        return data, "raw"
    out = _ZC.compress(data)
    return (out, "zstd") if len(out) < len(data) else (data, "raw")


def decompress(data: bytes, codec: str) -> bytes:
    return _ZD.decompress(data) if codec == "zstd" else data


class LinkDown(Exception):
    """The link dropped before this message went out."""


@dataclass
class Message:
    direction: str
    form: str                      # manifest|have|chunk_query|key|recipe|generate|thumb|raw_chunk
    path: str = ""
    step: Optional[int] = None
    body: bytes = b""                                  # keys, recipes, manifests
    blobs: List[Tuple[str, bytes, str]] = field(default_factory=list)
    # blobs: (sha256 of the plain chunk, bytes actually sent, codec of those bytes)
    kid: str = ""
    note: str = ""

    @property
    def payload_bytes(self) -> int:
        return len(self.body) + sum(len(b) for _, b, _ in self.blobs)


@dataclass
class Faults:
    """Corrupt named chunks on their first N deliveries; drop the link after N messages."""
    corrupt: Dict[str, int] = field(default_factory=dict)
    drop_after: Optional[int] = None

    def hit(self, h: str) -> bool:
        left = self.corrupt.get(h, 0)
        if left > 0:
            self.corrupt[h] = left - 1
            return True
        return False


class Ledger:
    """Every charged message, in order.  jlog turns these into the log."""

    def __init__(self) -> None:
        self.records: List[dict] = []
        self.t0 = time.perf_counter()

    def now_ms(self) -> float:
        return (time.perf_counter() - self.t0) * 1000.0

    def charge(self, msg: Message, elapsed_ms: float) -> dict:
        rec = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "direction": msg.direction,
            "path": msg.path,
            "form": msg.form,
            "step": msg.step,
            "payload_bytes": msg.payload_bytes,
            "header_bytes": HEADER_BYTES,
            "kid": msg.kid,
            "note": msg.note,
            "checker": "",
            "elapsed_ms": round(elapsed_ms, 3),
            "at_ms": round(self.now_ms(), 3),
        }
        self.records.append(rec)
        return rec

    @property
    def dial_bytes(self) -> int:
        return sum(r["payload_bytes"] + r["header_bytes"] for r in self.records)


class Link:
    def __init__(self, ledger: Ledger, faults: Optional[Faults] = None):
        self.ledger = ledger
        self.faults = faults or Faults()
        self.count = 0

    def deliver(self, msg: Message) -> Tuple[Message, dict]:
        """Charge the message and hand the far side its copy of the bytes."""
        if self.faults.drop_after is not None and self.count >= self.faults.drop_after:
            raise LinkDown(f"link down after {self.count} messages")
        t = time.perf_counter()
        self.count += 1
        blobs = []
        for h, data, codec in msg.blobs:
            if self.faults.hit(h):
                data = (b"\x00" + data[1:]) if data else b"\x00"  # a bit flipped in flight
            blobs.append((h, data, codec))
        got = Message(direction=msg.direction, form=msg.form, path=msg.path,
                      step=msg.step, body=msg.body, blobs=blobs,
                      kid=msg.kid, note=msg.note)
        rec = self.ledger.charge(msg, (time.perf_counter() - t) * 1000.0)
        return got, rec
