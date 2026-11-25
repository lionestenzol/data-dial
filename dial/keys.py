"""Build step 2 - the key model: file, chunk, thumb and manifest keys.

    Key = {points_to, rule_version, exactness, hash, size, child_keys}

A manifest key points to file keys; a file key points to chunk keys.  Keys are
the only thing both devices are ever required to understand, so the wire form
is a single canonical JSON object and its length is what the ledger charges.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Iterable, Sequence

RULE_VERSION = "v1"

FILE, CHUNK, THUMB, MANIFEST = "file", "chunk", "thumb", "manifest"
POINTS_TO = (FILE, CHUNK, THUMB, MANIFEST)

EXACT = "sha256-exact"
PREVIEW = "visual-preview"
EXACTNESS = (EXACT, PREVIEW)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canon(obj) -> bytes:
    """Canonical JSON bytes - the on-the-wire form of anything structured."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


@dataclass(frozen=True)
class Key:
    points_to: str
    exactness: str
    hash: str
    size: int
    child_keys: tuple[str, ...] = ()
    rule_version: str = RULE_VERSION

    def __post_init__(self) -> None:
        if self.points_to not in POINTS_TO:
            raise ValueError(f"points_to={self.points_to!r}")
        if self.exactness not in EXACTNESS:
            raise ValueError(f"exactness={self.exactness!r}")
        if len(self.hash) != 64:
            raise ValueError("hash must be a sha256 hex digest")
        if self.size < 0:
            raise ValueError("size must not be negative")
        if self.points_to in (CHUNK, THUMB) and self.child_keys:
            raise ValueError(f"a {self.points_to} key has no children")

    # -- identity ---------------------------------------------------------
    @property
    def kid(self) -> str:
        """The id both devices use in have-checks."""
        return f"{self.rule_version}:{self.points_to}:{self.exactness}:{self.hash}"

    # -- wire form --------------------------------------------------------
    def as_dict(self, with_children: bool = True) -> dict:
        d = {
            "points_to": self.points_to,
            "rule_version": self.rule_version,
            "exactness": self.exactness,
            "hash": self.hash,
            "size": self.size,
        }
        if with_children and self.child_keys:
            d["child_keys"] = list(self.child_keys)
        return d

    def wire(self, with_children: bool = True) -> bytes:
        return canon(self.as_dict(with_children))

    def wire_bytes(self, with_children: bool = True) -> int:
        """Bytes charged for sending this key (step 1) or its recipe (step 2)."""
        return len(self.wire(with_children))

    # -- the one hard rule ------------------------------------------------
    def satisfies(self, want: "Key") -> bool:
        """Can this key stand in for `want`?  A thumbnail never can."""
        if want.exactness == EXACT and self.exactness != EXACT:
            return False
        return self.kid == want.kid

    @classmethod
    def from_dict(cls, d: dict) -> "Key":
        return cls(
            points_to=d["points_to"],
            exactness=d["exactness"],
            hash=d["hash"],
            size=int(d["size"]),
            child_keys=tuple(d.get("child_keys", ())),
            rule_version=d.get("rule_version", RULE_VERSION),
        )


# -- constructors ---------------------------------------------------------
def chunk_key(data: bytes) -> Key:
    return Key(CHUNK, EXACT, sha256_hex(data), len(data))


def thumb_key(data: bytes) -> Key:
    return Key(THUMB, PREVIEW, sha256_hex(data), len(data))


def file_key(file_hash: str, size: int, children: Iterable[str]) -> Key:
    return Key(FILE, EXACT, file_hash, size, tuple(children))


def manifest_key(entries: Sequence[dict]) -> Key:
    body = canon(entries)
    return Key(MANIFEST, EXACT, sha256_hex(body), len(body))
