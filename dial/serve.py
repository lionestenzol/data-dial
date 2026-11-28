"""Rung 1: B-side server process.

Listens on a TCP socket, accepts one connection, drives a Device+Receiver
from the other end.  Every frame kind maps 1:1 to something Engine already
did against `self.b.*` / `self.rx.*` in-process.

    python3 -m dial.serve --root /path/to/B --host 127.0.0.1 --port 0
                           [--no-generators]
"""
from __future__ import annotations

import argparse
import json
import socket
import sys
import time
from typing import Iterable, List

from . import frame, view
from .checker import Receiver
from .device import Device, pack_bits
from .keys import Key
from .manifest import Entry, Manifest
from .peer import (
    KIND_BYE, KIND_HELLO_REPLY, KIND_HELLO_REQ, KIND_MSG,
    KIND_VERDICT, KIND_VIEW_REPLY, KIND_VIEW_REQ,
    KIND_HAVE_META_REQ, KIND_HAVE_META_REPLY,
    KIND_CHUNK_META_REQ, KIND_CHUNK_META_REPLY,
    _recv_frame, _send_frame,
)
from .wire import Message


def _send_control(sock: socket.socket, kind: int, obj: dict) -> int:
    payload = json.dumps(obj, separators=(",", ":")).encode("utf-8")
    return _send_frame(sock, kind, payload)


def _verdict_payload(ok: bool, reason: str = "",
                     bad_hashes=None, missing_hashes=None,
                     regen_ms_delta: float = 0.0,
                     regen_count_delta: int = 0) -> bytes:
    return json.dumps({
        "ok": ok, "reason": reason,
        "bad_hashes": list(bad_hashes or ()),
        "missing_hashes": list(missing_hashes or ()),
        "regen_ms_delta": round(regen_ms_delta, 6),
        "regen_count_delta": regen_count_delta,
    }, separators=(",", ":")).encode("utf-8")


def serve_once(sock: socket.socket, dev: Device) -> None:
    """Handle one A connection until it says BYE (or disconnects)."""
    rx = Receiver(dev)
    prev_regen_ms, prev_regen_count = 0.0, 0
    # For raw-fallback: A sends a raw_chunk msg with the file hash in blobs[0].
    # We distinguish "normal raw_chunk" from "raw fallback" by note=="raw fallback"
    # - matches engine._raw_fallback's marker.
    while True:
        try:
            kind, body, _wire = _recv_frame(sock)
        except (ConnectionError, OSError):
            return

        if kind == KIND_BYE:
            return

        if kind == KIND_HELLO_REQ:
            _send_control(sock, KIND_HELLO_REPLY,
                          {"can_generate": sorted(dev.can_generate)})
            continue

        if kind == KIND_VIEW_REQ:
            req = json.loads(body.decode("utf-8"))
            entries = [Entry.from_wire(d) for d in req["entries"]]
            man = Manifest(entries=entries)
            rows = view.library(dev, man)
            _send_control(sock, KIND_VIEW_REPLY, {
                "rows": [{"path": r.path, "shown_as": r.shown_as,
                          "bytes_held": r.bytes_held} for r in rows]
            })
            continue

        if kind == KIND_HAVE_META_REQ:
            req = json.loads(body.decode("utf-8"))
            tuples = req["tuples"]
            held = [dev.store.has_key(t["kid"]) for t in tuples]
            bound = [dev.settled(t["path"], t["kid"], t["file_kid"]) for t in tuples]
            _send_control(sock, KIND_HAVE_META_REPLY,
                          {"held": held, "bound": bound})
            continue

        if kind == KIND_CHUNK_META_REQ:
            req = json.loads(body.decode("utf-8"))
            bits = dev.have_chunks(req["hashes"])
            _send_control(sock, KIND_CHUNK_META_REPLY, {"bits": bits})
            continue

        if kind == KIND_MSG:
            msg = frame.decode_body(body)

            # have_query / chunk_query: answer with a pack_bits Message.
            # Raw fallback: Engine sends raw_chunk with note="raw fallback"
            # and expects accept_raw_file semantics on the far side.
            if msg.form == "raw_chunk" and msg.note == "raw fallback":
                # We need the file Key to call accept_raw_file.  Engine
                # packs the file Key as JSON in msg.body for the fallback
                # path (keeping payload_bytes accounted for on A's ledger
                # by sending the file bytes as the single blob).
                # Workaround for rung 1: parse the file key from msg.note
                # won't work because note is already "raw fallback".
                # Instead: the Engine sends an auxiliary KEY in a sidecar
                # field we smuggle through... actually the cleanest fix is
                # to put the Key json in `path` field?  No - keep `path`
                # as the actual path.  We add a dedicated KEY frame before
                # raw fallback.  Simpler: the Engine passes the file key's
                # hash in the blob's hash field, which we already have.
                # We rebuild a FILE key from (hash, len).
                (h, data, _codec) = msg.blobs[0]
                from .keys import Key, EXACT, FILE, RULE_VERSION
                fk = Key(FILE, EXACT, h, len(data))
                before_ms, before_n = rx.regen_ms, rx.regen_count
                v = rx.accept_raw_file(msg.path, fk, data)
                _send_frame(sock, KIND_VERDICT, _verdict_payload(
                    v.ok, v.reason,
                    regen_ms_delta=rx.regen_ms - before_ms,
                    regen_count_delta=rx.regen_count - before_n))
                continue

            # have_query / chunk_query / have: these are charged on A's
            # ledger but never had a checker verdict - they're metadata.
            # The real answer travels the uncharged META sidecar.
            if msg.form in {"have_query", "chunk_query", "have"}:
                continue

            # All other Message forms: apply the checker.
            before_ms, before_n = rx.regen_ms, rx.regen_count
            v = rx.apply(msg)
            _send_frame(sock, KIND_VERDICT, _verdict_payload(
                v.ok, v.reason,
                bad_hashes=v.bad_hashes, missing_hashes=v.missing_hashes,
                regen_ms_delta=rx.regen_ms - before_ms,
                regen_count_delta=rx.regen_count - before_n))
            continue

        raise RuntimeError(f"unknown frame kind {kind}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="Device B root folder")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=0,
                    help="0 = pick a free port and print it")
    ap.add_argument("--no-generators", action="store_true",
                    help="B lacks every generator (test the fallback path)")
    ap.add_argument("--ready-file",
                    help="write the bound port here once listening")
    args = ap.parse_args()

    gens = set() if args.no_generators else None
    dev = Device("B", args.root, generators=gens)

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((args.host, args.port))
    srv.listen(1)
    port = srv.getsockname()[1]
    if args.ready_file:
        with open(args.ready_file, "w") as fh:
            fh.write(str(port))
    print(f"dial.serve: ready on {args.host}:{port}", flush=True)
    try:
        conn, _ = srv.accept()
        with conn:
            serve_once(conn, dev)
    finally:
        srv.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
