"""The regenerate arm: a named, versioned, deterministic process that turns a
tiny recipe into the exact bytes of an artifact.

This is the dial's one novel move. The other arms reuse bytes B already holds -
a cache key (step 1), a chunk reassembly recipe (step 2), raw chunks (step 4).
Those are what every content-addressed sync (rsync, git, Dropbox) already does.
The regenerate arm is different: instead of shipping the artifact or its chunks,
it ships `{generator, params}` and has the RECEIVER run the generator to
reproduce the bytes. A 355 KB photo crosses as an ~80-byte recipe.

Two preconditions - together these are the "provenance discipline":
  1. the SENDER kept the recipe (it did not throw the generator away), and
  2. the RECEIVER has the same generator installed ("it has the oven").

Determinism is required and CHECKED, never assumed. A regenerated artifact is
kept only if its SHA-256 equals the original's. Wrong generator version,
nondeterministic output, or a missing generator all fail the check and the
engine falls back to sending the raw bytes. The win is never at the cost of
correctness - it is byte-exact or it does not count.
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Callable, Dict

from .keys import canon


@dataclass(frozen=True)
class GenRecipe:
    """What crosses the wire in place of the artifact: which generator, and the
    parameters that make it produce this exact artifact."""
    generator: str            # "name:version", e.g. "photo:v1"
    params: dict

    def as_wire_dict(self) -> dict:
        return {"generator": self.generator, "params": self.params}

    def wire(self) -> bytes:
        return canon(self.as_wire_dict())

    def wire_bytes(self) -> int:
        return len(self.wire())

    @classmethod
    def from_dict(cls, d: dict) -> "GenRecipe":
        return cls(generator=d["generator"], params=dict(d["params"]))


REGISTRY: Dict[str, Callable[[dict], bytes]] = {}


def register(name: str, fn: Callable[[dict], bytes]) -> None:
    REGISTRY[name] = fn


def has(name: str) -> bool:
    return name in REGISTRY


def run(recipe: GenRecipe) -> bytes:
    fn = REGISTRY.get(recipe.generator)
    if fn is None:
        raise KeyError(f"no generator {recipe.generator!r} installed")
    return fn(recipe.params)


# -- the one real generator -------------------------------------------------
# A synthetic photograph, byte-identical to photogen.save_photo on disk. This
# is the same recompute that exp009 only *scored*; here it actually runs on B
# and is verified byte-exact (see tests/test_generate_arm.py).
def _photo_v1(params: dict) -> bytes:
    from photogen import scene
    buf = io.BytesIO()
    scene(int(params["width"]), int(params["height"]), int(params["seed"])).save(
        buf, format="JPEG", quality=int(params["quality"]),
        subsampling=2, optimize=False)
    return buf.getvalue()


register("photo:v1", _photo_v1)
