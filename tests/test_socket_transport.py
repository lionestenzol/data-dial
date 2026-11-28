"""Rung 1 tests: the engine over a real socket between two processes.

Two kinds of check:
  1. Ledger parity - every charged record matches the single-process run
     field for field (everything except wall-clock timing).
  2. Byte-exactness - every file on B's folder, independently hashed from
     this test harness, matches the file on A.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

from dial.device import Device
from dial.engine import Engine
from dial.generators import GenRecipe
from dial.peer import SocketPeer
from dial.thumb import ThumbMaker
from dial.wire import Ledger

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from photogen import save_photo  # noqa: E402


SIZE = (800, 600)
QUALITY = 85
LEDGER_KEEP = ("direction", "path", "form", "step",
               "payload_bytes", "header_bytes", "kid", "note", "checker")


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _build_A(n: int):
    """Returns (src_dir, provenance, truth-hashes)."""
    src = Path(tempfile.mkdtemp()) / "lib"
    src.mkdir(parents=True)
    provenance, truth = {}, {}
    for i in range(n):
        rel = f"pic{i}.jpg"
        save_photo(src / rel, seed=i, size=SIZE, quality=QUALITY)
        provenance[rel] = GenRecipe("photo:v1",
                                    {"seed": i, "width": SIZE[0],
                                     "height": SIZE[1], "quality": QUALITY})
        truth[rel] = _sha(src / rel)
    return src, provenance, truth


def _run_local(src, provenance, opens):
    work = Path(tempfile.mkdtemp())
    a_root, b_root = work / "A", work / "B"
    shutil.copytree(src, a_root)
    A = Device("A", a_root,
               thumbs=ThumbMaker(a_root / ".dial" / "thumbs.json"),
               provenance=provenance)
    B = Device("B", b_root)
    led = Ledger()
    res = Engine(A, B, led).sync(open_paths=opens)
    return led, res, b_root


def _run_socket(src, provenance, opens):
    work = Path(tempfile.mkdtemp())
    a_root, b_root = work / "A", work / "B"
    shutil.copytree(src, a_root)
    b_root.mkdir()
    ready = work / "port.txt"

    repo = Path(__file__).resolve().parent.parent
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo) + os.pathsep + env.get("PYTHONPATH", "")

    child = subprocess.Popen(
        [sys.executable, "-m", "dial.serve",
         "--root", str(b_root),
         "--host", "127.0.0.1", "--port", "0",
         "--ready-file", str(ready)],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    try:
        deadline = time.time() + 15.0
        while time.time() < deadline and not ready.exists():
            if child.poll() is not None:
                err = child.stderr.read().decode() if child.stderr else ""
                raise RuntimeError(f"dial.serve died early: {err}")
            time.sleep(0.05)
        assert ready.exists(), "server never reported port"
        port = int(ready.read_text())

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("127.0.0.1", port))
        A = Device("A", a_root,
                   thumbs=ThumbMaker(a_root / ".dial" / "thumbs.json"),
                   provenance=provenance)
        led = Ledger()
        peer = SocketPeer(sock, led)
        res = Engine(A, peer, led).sync(open_paths=opens)
        wire_total = peer.wire_bytes_sent + peer.wire_bytes_recv
        peer.close()
        child.wait(timeout=5.0)
    finally:
        if child.poll() is None:
            child.terminate()
            try: child.wait(timeout=2.0)
            except Exception: child.kill()
    return led, res, b_root, wire_total


def _ledger_diffs(a, b):
    out = []
    if len(a.records) != len(b.records):
        out.append(f"count: {len(a.records)} vs {len(b.records)}")
    for i, (r1, r2) in enumerate(zip(a.records, b.records)):
        for k in LEDGER_KEEP:
            if r1.get(k) != r2.get(k):
                out.append(f"#{i} {k}: {r1.get(k)!r} vs {r2.get(k)!r}")
    return out


def test_socket_sync_byte_exact_and_ledger_parity():
    """Sync a photo library over a socket; every file on B must be
    byte-exact, and A's socket ledger must match the single-process ledger
    record-for-record."""
    src, prov, truth = _build_A(n=3)
    opens = sorted(truth)

    led_local, _, _ = _run_local(src, prov, opens)
    led_sock, res_sock, b_sock, wire_total = _run_socket(src, prov, opens)

    # 1. Byte-exactness, hashed independently here from B's folder.
    for rel, want in truth.items():
        p = b_sock / rel
        assert p.exists(), f"{rel} missing on B"
        assert _sha(p) == want, f"{rel} wrong on B"

    # 2. Ledger parity.
    diffs = _ledger_diffs(led_local, led_sock)
    assert not diffs, "ledger diverged:\n  " + "\n  ".join(diffs[:10])
    assert led_local.dial_bytes == led_sock.dial_bytes

    # 3. Real socket bytes exceed the ledger (framing is honest overhead).
    assert wire_total >= led_sock.dial_bytes


def test_socket_no_generator_falls_back_to_raw():
    """If B has no generator, the generate arm must fall back to raw and
    files still arrive byte-exact.  Exercises the raw-fallback path over
    the socket."""
    src, prov, truth = _build_A(n=2)
    work = Path(tempfile.mkdtemp())
    a_root, b_root = work / "A", work / "B"
    shutil.copytree(src, a_root)
    b_root.mkdir()
    ready = work / "port.txt"

    repo = Path(__file__).resolve().parent.parent
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo) + os.pathsep + env.get("PYTHONPATH", "")
    child = subprocess.Popen(
        [sys.executable, "-m", "dial.serve",
         "--root", str(b_root), "--host", "127.0.0.1", "--port", "0",
         "--ready-file", str(ready), "--no-generators"],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    try:
        deadline = time.time() + 15.0
        while time.time() < deadline and not ready.exists():
            if child.poll() is not None:
                raise RuntimeError("serve died")
            time.sleep(0.05)
        port = int(ready.read_text())
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("127.0.0.1", port))
        A = Device("A", a_root,
                   thumbs=ThumbMaker(a_root / ".dial" / "thumbs.json"),
                   provenance=prov)
        led = Ledger()
        peer = SocketPeer(sock, led)
        # B has no generator; A's attach_gen checks peer.can_generate.
        assert peer.can_generate == set()
        res = Engine(A, peer, led).sync(open_paths=sorted(truth))
        peer.close()
        child.wait(timeout=5.0)
    finally:
        if child.poll() is None:
            child.terminate()
            try: child.wait(timeout=2.0)
            except Exception: child.kill()

    # With no generator attached by A (because peer.can_generate is empty),
    # the originals cross as raw chunks.  Byte-exactness still holds.
    for rel, want in truth.items():
        assert _sha(b_root / rel) == want
