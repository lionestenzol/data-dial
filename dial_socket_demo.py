#!/usr/bin/env python3
"""dial_socket_demo - rung 1: the engine between two real processes.

Two OS processes, one socket.  A runs the engine; B is spawned as a child
process (`python3 -m dial.serve`) listening on a loopback port.  A folder
of photos is synced over the socket, every file on B is hashed, and the
single-process ledger is diffed against the socket ledger: they must be
byte-identical.

    python3 dial_socket_demo.py [--n 8]

Also prints the real framing overhead the socket added - the ledger does
not count it; the console does, so the cost is visible instead of hidden.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from dial.device import Device
from dial.engine import Engine
from dial.generators import GenRecipe
from dial.peer import SocketPeer
from dial.thumb import ThumbMaker
from dial.wire import Ledger
from photogen import save_photo


SIZE = (1600, 1200)
QUALITY = 88


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build_A(root: Path, n: int):
    provenance, truth = {}, {}
    for i in range(n):
        rel = f"pic{i}.jpg"
        save_photo(root / rel, seed=i, size=SIZE, quality=QUALITY)
        provenance[rel] = GenRecipe("photo:v1",
                                    {"seed": i, "width": SIZE[0],
                                     "height": SIZE[1], "quality": QUALITY})
        truth[rel] = sha(root / rel)
    return provenance, truth


def run_local(src: Path, provenance, opens):
    """Baseline: single-process run (LocalPeer path)."""
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


def run_socket(src: Path, provenance, opens):
    """Rung 1: A in this process, B in a child process over a TCP socket."""
    work = Path(tempfile.mkdtemp())
    a_root, b_root = work / "A", work / "B"
    shutil.copytree(src, a_root)
    b_root.mkdir()

    ready = work / "port.txt"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).parent) + os.pathsep + env.get("PYTHONPATH", "")
    child = subprocess.Popen(
        [sys.executable, "-m", "dial.serve",
         "--root", str(b_root),
         "--host", "127.0.0.1", "--port", "0",
         "--ready-file", str(ready)],
        env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    try:
        # Wait up to 15s for the child to bind and write the port.
        deadline = time.time() + 15.0
        while time.time() < deadline and not ready.exists():
            if child.poll() is not None:
                out = child.stdout.read().decode() if child.stdout else ""
                err = child.stderr.read().decode() if child.stderr else ""
                raise RuntimeError(f"dial.serve died early\nout: {out}\nerr: {err}")
            time.sleep(0.05)
        if not ready.exists():
            child.kill()
            raise RuntimeError("dial.serve never reported a port")
        port = int(ready.read_text())

        # A side: connect, build Device, SocketPeer, Engine.
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("127.0.0.1", port))
        A = Device("A", a_root,
                   thumbs=ThumbMaker(a_root / ".dial" / "thumbs.json"),
                   provenance=provenance)
        led = Ledger()
        peer = SocketPeer(sock, led)
        res = Engine(A, peer, led).sync(open_paths=opens)
        wire_sent = peer.wire_bytes_sent
        wire_recv = peer.wire_bytes_recv
        peer.close()
        child.wait(timeout=5.0)
    finally:
        if child.poll() is None:
            child.terminate()
            try: child.wait(timeout=2.0)
            except Exception: child.kill()
    return led, res, b_root, wire_sent, wire_recv


def diff_ledgers(a, b):
    """Field-by-field diff that ignores wall-clock fields."""
    keep = ("direction", "path", "form", "step",
            "payload_bytes", "header_bytes", "kid", "note", "checker")
    out = []
    if len(a.records) != len(b.records):
        return [f"record count: {len(a.records)} vs {len(b.records)}"]
    for i, (r1, r2) in enumerate(zip(a.records, b.records)):
        for k in keep:
            if r1.get(k) != r2.get(k):
                out.append(f"#{i} {k}: {r1.get(k)!r} vs {r2.get(k)!r}")
    return out


def verify_bytes(b_root: Path, truth: dict):
    missing, bad = [], []
    for rel, want in truth.items():
        p = b_root / rel
        if not p.exists():
            missing.append(rel); continue
        if sha(p) != want:
            bad.append(rel)
    return missing, bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8)
    args = ap.parse_args()

    src = Path(tempfile.mkdtemp()) / "lib"
    src.mkdir(parents=True)
    provenance, truth = build_A(src, args.n)
    total_orig = sum((src / r).stat().st_size for r in truth)
    opens = sorted(truth)

    print(f"{args.n} photos, {total_orig/1e6:.2f} MB on A\n")

    print("single-process run (LocalPeer) ...")
    led_local, res_local, b_local = run_local(src, provenance, opens)
    local_missing, local_bad = verify_bytes(b_local, truth)

    print("two-process run (SocketPeer, loopback) ...")
    led_sock, res_sock, b_sock, wire_sent, wire_recv = run_socket(src, provenance, opens)
    sock_missing, sock_bad = verify_bytes(b_sock, truth)

    diffs = diff_ledgers(led_local, led_sock)

    print()
    print(f"{'':30}{'LOCAL':>14}{'SOCKET':>14}")
    print(f"{'dial bytes (ledger)':30}{led_local.dial_bytes:>14,}{led_sock.dial_bytes:>14,}")
    print(f"{'ledger records':30}{len(led_local.records):>14,}{len(led_sock.records):>14,}")
    print(f"{'recipes arrived':30}{res_local.regen_count:>14}{res_sock.regen_count:>14}")
    print(f"{'raw fallbacks':30}{res_local.fallbacks:>14}{res_sock.fallbacks:>14}")
    print(f"{'files missing on B':30}{len(local_missing):>14}{len(sock_missing):>14}")
    print(f"{'files wrong on B':30}{len(local_bad):>14}{len(sock_bad):>14}")

    print()
    print(f"true socket bytes sent (incl. framing): {wire_sent:,}")
    print(f"true socket bytes recv:                 {wire_recv:,}")
    print(f"framing overhead vs ledger:             "
          f"{(wire_sent + wire_recv) - led_sock.dial_bytes:+,} bytes "
          f"({((wire_sent + wire_recv) / led_sock.dial_bytes - 1) * 100:+.2f}%)")

    ok = (led_local.dial_bytes == led_sock.dial_bytes
          and not diffs
          and not sock_missing and not sock_bad
          and not local_missing and not local_bad)
    print()
    if ok:
        print("PASS: ledgers identical record-for-record; every file on B byte-exact.")
        return 0
    print("FAIL:")
    for d in diffs[:20]:
        print("  ledger diff:", d)
    for r in sock_missing: print("  missing:", r)
    for r in sock_bad:     print("  wrong  :", r)
    return 1


if __name__ == "__main__":
    sys.exit(main())
