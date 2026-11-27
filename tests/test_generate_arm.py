"""The regenerate arm, and - more important - its safety net.

The arm is only allowed to win when it is byte-exact.  These tests prove that
when regeneration would be wrong (generator absent, or nondeterministic), the
engine notices and falls back to raw, so B still ends up byte-identical to A.
"""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import pytest

from dial import generators
from dial.device import Device
from dial.engine import Engine
from dial.generators import GenRecipe
from dial.thumb import ThumbMaker
from dial.wire import Ledger
from photogen import save_photo

SIZE = (800, 600)
Q = 88


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _library(root: Path, n=4):
    prov, truth = {}, {}
    for i in range(n):
        rel = f"p{i}.jpg"
        save_photo(root / rel, seed=i, size=SIZE, quality=Q)
        prov[rel] = GenRecipe("photo:v1",
                              {"seed": i, "width": SIZE[0], "height": SIZE[1],
                               "quality": Q})
        truth[rel] = _sha(root / rel)
    return prov, truth


def _run(tmp, src, keep_recipes=True, b_generators=None, prov=None):
    """A fresh A (copied from the untouched library `src`) and a fresh B, under
    their own subdir, so repeated runs never share accumulated state."""
    a_root, b_root = tmp / "A", tmp / "B"
    shutil.copytree(src, a_root)
    A = Device("A", a_root, thumbs=ThumbMaker(a_root / ".dial" / "thumbs.json"),
               provenance=prov if keep_recipes else {})
    B = Device("B", b_root, generators=b_generators)
    led = Ledger()
    opens = sorted(p.name for p in a_root.glob("*.jpg"))
    res = Engine(A, B, led).sync(open_paths=opens)
    return led, res, b_root


def _exact(b_root, truth):
    return all((b_root / rel).exists() and _sha(b_root / rel) == want
               for rel, want in truth.items())


def test_regenerate_is_byte_exact_and_cheaper(tmp_path):
    src = tmp_path / "lib"
    src.mkdir(parents=True)
    prov, truth = _library(src)
    on_led, on_res, b_root = _run(tmp_path / "on", src, keep_recipes=True, prov=prov)
    # every file identical, and it actually went by the regenerate arm
    assert _exact(b_root, truth)
    assert on_res.regen_count == len(truth)
    assert on_res.fallbacks == 0
    # and far fewer bytes than sending the originals raw
    off_led, off_res, off_b = _run(tmp_path / "off", src, keep_recipes=False, prov=prov)
    assert _exact(off_b, truth)
    assert on_led.dial_bytes < off_led.dial_bytes / 5


def test_missing_generator_falls_back_to_raw(tmp_path):
    """B does not have the generator installed: it cannot regenerate, so the
    engine must fall back to raw and still deliver the exact bytes."""
    src = tmp_path / "lib"
    src.mkdir(parents=True)
    prov, truth = _library(src)
    # B's oven is empty: the router never even marks the want (the engine checks
    # the generator is in B.can_generate), so originals go raw and nothing is
    # regenerated - yet every file still arrives byte-exact.
    led, res, b_root = _run(tmp_path, src, keep_recipes=True, b_generators=set(), prov=prov)
    assert _exact(b_root, truth)
    assert res.regen_count == 0


def test_nondeterministic_generator_is_caught(tmp_path, monkeypatch):
    """The generator runs but returns the wrong bytes (version skew / nondeterminism).
    The hash check must fail and the engine fall back to raw - never keep wrong bytes."""
    src = tmp_path / "lib"
    src.mkdir(parents=True)
    prov, truth = _library(src)

    real = generators.REGISTRY["photo:v1"]

    def corrupt(params):
        return real(params) + b"\x00"    # one byte off: no longer byte-exact

    monkeypatch.setitem(generators.REGISTRY, "photo:v1", corrupt)

    led, res, b_root = _run(tmp_path, src, keep_recipes=True, prov=prov)
    # B ran the generator, got a mismatch, and fell back - files still exact
    assert _exact(b_root, truth)
    assert res.fallbacks == len(truth)
